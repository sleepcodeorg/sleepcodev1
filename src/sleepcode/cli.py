# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

import sleepcode
from sleepcode.agent.loop import AgentLimits, AgentLoop
from sleepcode.agent.repair import run_repair_loop
from sleepcode.config import get_config_path, load_config, set_provider_key
from sleepcode.doctor import run_doctor
from sleepcode.night.cli import night_app
from sleepcode.providers.base import Provider
from sleepcode.providers.litellm_provider import LiteLLMProvider
from sleepcode.queue.cli import queue_app
from sleepcode.report.cli import report_app
from sleepcode.secrets import get_secret
from sleepcode.setup_wizard import run_setup
from sleepcode.tools.files import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from sleepcode.tools.git import GitCommitTool, GitCreateBranchTool, GitDiffTool, GitStatusTool
from sleepcode.tools.registry import ToolRegistry
from sleepcode.tools.search import SearchTool
from sleepcode.tools.shell import RunShellTool
from sleepcode.workspace import Workspace

app = typer.Typer(
    name="sleepcode",
    help="SleepCode: Autonomous coding agent that works while you sleep.",
    add_completion=False,
)
config_app = typer.Typer(help="Manage SleepCode configuration and API keys.")
app.add_typer(config_app, name="config")
app.add_typer(queue_app, name="queue")
app.add_typer(night_app, name="night")
app.add_typer(report_app, name="report")

console = Console()

_test_provider_override: Optional[Provider] = None


def set_test_provider_override(provider: Optional[Provider]) -> None:
    global _test_provider_override
    _test_provider_override = provider


@app.command()
def version() -> None:
    """Print SleepCode version."""
    console.print(f"sleepcode {sleepcode.__version__}")


@app.command()
def setup() -> None:
    """Run interactive setup wizard to configure primary LLM provider and default options."""
    run_setup()


@app.command()
def doctor() -> None:
    """Run SleepCode system diagnostic checks."""
    all_passed = run_doctor()
    if not all_passed:
        raise typer.Exit(code=1)


@config_app.command("set-key")
def config_set_key(
    provider: str = typer.Argument(..., help="Provider name (e.g. openai, anthropic, groq)"),
) -> None:
    """Prompt for and save an API key for a provider."""
    key = typer.prompt(f"Enter API key for provider '{provider}'", hide_input=True)
    if not key or not key.strip():
        console.print("[bold red]Error: Key cannot be empty.[/bold red]")
        raise typer.Exit(code=1)

    set_provider_key(provider, key.strip())
    path_str = str(get_config_path())
    msg = f"[bold green]API key for '{provider}' saved successfully to {path_str}[/bold green]"
    console.print(msg)


@config_app.command("list")
def config_list() -> None:
    """List configured providers without revealing keys."""
    config = load_config()
    providers = ["openai", "anthropic", "groq", "gemini", "openrouter", "mistral"]

    console.print("[bold]Configured Providers:[/bold]")
    for p in providers:
        secret = get_secret(p, config.keys)
        status = "[green]SET[/green]" if secret else "[dim]NOT SET[/dim]"
        console.print(f"  {p}: {status}")


@app.command()
def run(
    task: str = typer.Argument(..., help="Task description for the agent"),
    workspace: Path = typer.Option(..., "--workspace", "-w", help="Workspace directory path"),
    model: str = typer.Option(..., "--model", "-m", help="LLM model identifier"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Run in dry-run mode"),
    allow_shell: bool = typer.Option(
        False, "--allow-shell", help="Allow agent to run safe shell commands and git tools"
    ),
    test_cmd: Optional[str] = typer.Option(
        None, "--test-cmd", help="Optional test command to verify agent work"
    ),
    repair_attempts: int = typer.Option(
        2, "--repair-attempts", help="Number of repair attempts if tests fail (max 5)"
    ),
    max_iterations: int = typer.Option(40, "--max-iterations", help="Maximum agent iterations"),
    max_cost_usd: float = typer.Option(2.00, "--max-cost-usd", help="Maximum cost limit in USD"),
) -> None:
    """Run an autonomous task in a workspace."""
    workspace_path = workspace.expanduser().resolve()
    if not workspace_path.exists() or not workspace_path.is_dir():
        msg = (
            f"[bold red]Error: Workspace path '{workspace}' "
            "does not exist or is not a directory.[/bold red]"
        )
        console.print(msg)
        raise typer.Exit(code=1)

    try:
        ws = Workspace(workspace_path)
    except Exception as e:
        console.print(f"[bold red]Error initializing workspace: {str(e)}[/bold red]")
        raise typer.Exit(code=1) from e

    provider_name = model.split("/")[0] if "/" in model else model

    config = load_config()
    api_key = get_secret(provider_name, config.keys)
    if provider_name.lower() != "ollama" and not api_key and _test_provider_override is None:
        p_upper = provider_name.upper()
        msg = (
            f"[bold red]Error: No API key found for provider '{provider_name}'. "
            f"Run 'sleepcode config set-key {provider_name}' or set {p_upper}_API_KEY.[/bold red]"
        )
        console.print(msg)
        raise typer.Exit(code=1)

    if _test_provider_override is not None:
        provider = _test_provider_override
    else:
        provider = LiteLLMProvider(api_key=api_key)

    registry = ToolRegistry()
    registry.register(ReadFileTool(ws))
    registry.register(WriteFileTool(ws))
    registry.register(EditFileTool(ws))
    registry.register(ListDirTool(ws))
    registry.register(SearchTool(ws))

    if allow_shell:
        registry.register(RunShellTool(ws))
        registry.register(GitStatusTool(ws))
        registry.register(GitDiffTool(ws))
        registry.register(GitCreateBranchTool(ws))
        registry.register(GitCommitTool(ws))

    limits = AgentLimits(
        max_iterations=max_iterations,
        max_cost_usd=max_cost_usd,
    )

    extra_secrets = {api_key} if api_key else set()

    if test_cmd:
        status_msg = "[bold blue]Running SleepCode agent with test-repair loop...[/bold blue]"
        with console.status(status_msg):
            try:
                repair_res = run_repair_loop(
                    task=task,
                    workspace=ws,
                    model=model,
                    provider=provider,
                    tools=registry,
                    test_cmd=test_cmd,
                    repair_attempts=repair_attempts,
                    limits=limits,
                    dry_run=dry_run,
                    extra_secrets=extra_secrets,
                )
            except Exception as e:
                console.print(f"[bold red]Error in test repair loop: {str(e)}[/bold red]")
                raise typer.Exit(code=1) from e

        result = repair_res.agent_result
        status_str = (
            "[bold green]tests_passed[/bold green]"
            if repair_res.status == "tests_passed"
            else "[bold red]tests_failed[/bold red]"
        )
        changed_str = ", ".join(result.files_changed) if result.files_changed else "None"
        summary_text = (
            f"Status: {status_str}\n"
            f"Repair Attempts Used: {repair_res.attempts_used}\n"
            f"Stop Reason: {result.stop_reason}\n"
            f"Run ID: {result.run_id}\n"
            f"Files Changed: {changed_str}\n"
            f"Tokens: {result.total_tokens}\n"
            f"Cost: ${result.total_cost:.4f}\n\n"
            f"Test Output:\n{repair_res.test_output}\n\n"
            f"Final Output:\n{result.final_text}"
        )

        console.print(Panel(summary_text, title="SleepCode Agent Summary", expand=False))

        if repair_res.status == "tests_passed":
            raise typer.Exit(code=0)
        else:
            raise typer.Exit(code=1)

    loop = AgentLoop(
        task=task,
        workspace=ws,
        model=model,
        provider=provider,
        tools=registry,
        limits=limits,
        dry_run=dry_run,
        extra_secrets=extra_secrets,
    )

    with console.status("[bold blue]Running SleepCode agent...[/bold blue]"):
        result = loop.run()

    status_str = (
        "[bold green]Success[/bold green]"
        if result.stop_reason == "completed"
        else "[bold yellow]Stopped[/bold yellow]"
    )
    changed_str = ", ".join(result.files_changed) if result.files_changed else "None"
    summary_text = (
        f"Status: {status_str}\n"
        f"Stop Reason: {result.stop_reason}\n"
        f"Run ID: {result.run_id}\n"
        f"Files Changed: {changed_str}\n"
        f"Tokens: {result.total_tokens}\n"
        f"Cost: ${result.total_cost:.4f}\n\n"
        f"Final Output:\n{result.final_text}"
    )

    console.print(Panel(summary_text, title="SleepCode Agent Summary", expand=False))

    if result.stop_reason == "completed":
        raise typer.Exit(code=0)
    else:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
