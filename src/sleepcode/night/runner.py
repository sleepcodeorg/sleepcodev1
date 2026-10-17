# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from sleepcode.agent.loop import AgentLimits, AgentLoop
from sleepcode.agent.repair import run_repair_loop
from sleepcode.config import load_config
from sleepcode.night.budget import NightTracker
from sleepcode.night.git_ops import (
    check_working_tree_clean,
    commit_task_changes,
    create_task_branch,
    get_current_branch,
    restore_branch,
)
from sleepcode.night.window import WindowManager
from sleepcode.providers.base import Provider
from sleepcode.providers.litellm_provider import LiteLLMProvider
from sleepcode.queue.db import get_db_connection
from sleepcode.queue.models import Task
from sleepcode.queue.repository import TaskRepository
from sleepcode.report.markdown import generate_morning_report
from sleepcode.report.notifiers import notify_all
from sleepcode.secrets import get_secret
from sleepcode.tools.files import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from sleepcode.tools.git import GitCommitTool, GitCreateBranchTool, GitDiffTool, GitStatusTool
from sleepcode.tools.registry import ToolRegistry
from sleepcode.tools.search import SearchTool
from sleepcode.tools.shell import RunShellTool
from sleepcode.workspace import Workspace

_test_night_provider_override: Optional[Provider] = None


def set_test_night_provider_override(provider: Optional[Provider]) -> None:
    """Set provider override for offline night runner tests."""
    global _test_night_provider_override
    _test_night_provider_override = provider


class NightRunner:
    """Night execution loop runner."""

    def __init__(
        self,
        window_str: str = "23:00-07:00",
        night_budget_usd: float = 5.00,
        allow_shell: bool = False,
        once: bool = False,
        max_tasks: int = 10,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.window_mgr = WindowManager(window_str, clock=clock)
        self.tracker = NightTracker(night_budget_usd)
        self.allow_shell = allow_shell
        self.once = once
        self.max_tasks = max_tasks
        self.window_str = window_str

    def run_night_queue(self) -> List[Task]:
        """Process queued tasks during the night window."""
        if not self.once and not self.window_mgr.is_active():
            return []

        conn = get_db_connection()
        repo_obj = TaskRepository(conn)

        tasks_processed: List[Task] = []

        while len(tasks_processed) < self.max_tasks:
            if not self.once and not self.window_mgr.is_active():
                break

            can_continue, _budget_reason = self.tracker.can_start_next_task()
            if not can_continue:
                break

            task = repo_obj.take_next_queued_task()
            if not task:
                break

            self._process_single_task(task, repo_obj)
            updated_task = repo_obj.get_task(task.id)
            if updated_task:
                tasks_processed.append(updated_task)

        # Generate morning report upon night run completion
        today_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        _report_path, summary_line = generate_morning_report(
            date_str=today_date,
            window_str=self.window_str,
            night_budget_usd=self.tracker.night_budget_usd,
        )
        notify_all(summary_line)

        return tasks_processed

    def _process_single_task(self, task: Task, repo_obj: TaskRepository) -> None:
        repo_path = Path(task.repo_path)
        if not repo_path.exists() or not repo_path.is_dir():
            repo_obj.update_task_status(task.id, "failed")
            repo_obj.add_run(
                task_id=task.id,
                status="failed",
                notes=f"Repository path '{task.repo_path}' does not exist.",
            )
            return

        is_clean, clean_msg = check_working_tree_clean(repo_path)
        if not is_clean:
            repo_obj.update_task_status(task.id, "failed")
            repo_obj.add_run(
                task_id=task.id,
                status="failed",
                notes=f"Refused run: working tree not clean. {clean_msg}",
            )
            return

        original_branch = get_current_branch(repo_path)
        task_branch: Optional[str] = None

        try:
            task_branch = create_task_branch(repo_path, task.task_text)
            repo_obj.update_task_status(task.id, "running", branch_name=task_branch)

            ws = Workspace(repo_path)

            provider_name = task.model.split("/")[0] if "/" in task.model else task.model
            config = load_config()
            api_key = get_secret(provider_name, config.keys)

            if _test_night_provider_override is not None:
                provider = _test_night_provider_override
            else:
                provider = LiteLLMProvider(api_key=api_key)

            registry = ToolRegistry()
            registry.register(ReadFileTool(ws))
            registry.register(WriteFileTool(ws))
            registry.register(EditFileTool(ws))
            registry.register(ListDirTool(ws))
            registry.register(SearchTool(ws))

            if self.allow_shell:
                registry.register(RunShellTool(ws))
                registry.register(GitStatusTool(ws))
                registry.register(GitDiffTool(ws))
                registry.register(GitCreateBranchTool(ws))
                registry.register(GitCommitTool(ws))

            effective_budget = self.tracker.get_task_effective_budget(task.budget_usd)
            limits = AgentLimits(max_cost_usd=effective_budget)
            extra_secrets = {api_key} if api_key else set()

            run_record = repo_obj.add_run(task_id=task.id, status="running")

            if task.test_cmd:
                repair_res = run_repair_loop(
                    task=task.task_text,
                    workspace=ws,
                    model=task.model,
                    provider=provider,
                    tools=registry,
                    test_cmd=task.test_cmd,
                    repair_attempts=2,
                    limits=limits,
                    extra_secrets=extra_secrets,
                )
                agent_res = repair_res.agent_result
                tests_passed = repair_res.status == "tests_passed"

                if tests_passed:
                    final_status = "succeeded"
                else:
                    final_status = "needs_review"

                notes = (
                    f"Test repair status: {repair_res.status}. Stop reason: {agent_res.stop_reason}"
                )
            else:
                loop = AgentLoop(
                    task=task.task_text,
                    workspace=ws,
                    model=task.model,
                    provider=provider,
                    tools=registry,
                    limits=limits,
                    extra_secrets=extra_secrets,
                )
                agent_res = loop.run()
                tests_passed = None
                if agent_res.stop_reason == "completed":
                    final_status = "succeeded"
                    notes = "Agent completed task."
                else:
                    final_status = "failed"
                    notes = f"Agent stopped with reason: {agent_res.stop_reason}"

            actual_cost = agent_res.total_cost
            recorded_cost, cost_note = self.tracker.record_task_cost(actual_cost, task.budget_usd)

            commit_ok = True
            if final_status in ("succeeded", "needs_review"):
                commit_ok, commit_msg = commit_task_changes(repo_path, task.task_text)
                if not commit_ok:
                    final_status = "failed"
                    notes += f" | Commit failed: {commit_msg}"

            repo_obj.update_run(
                run_id=run_record.id,
                status=final_status,
                cost_usd=recorded_cost,
                tokens=agent_res.total_tokens,
                files_changed=agent_res.files_changed,
                tests_passed=tests_passed,
                notes=notes + f" | {cost_note}",
            )
            repo_obj.update_task_status(task.id, final_status, branch_name=task_branch)

        except Exception as e:
            repo_obj.update_task_status(task.id, "failed")
            repo_obj.add_run(
                task_id=task.id,
                status="failed",
                notes=f"Unexpected error during task run: {str(e)}",
            )
        finally:
            restore_branch(repo_path, original_branch)
