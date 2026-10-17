# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass
from typing import Optional


@dataclass
class Task:
    id: int
    task_text: str
    repo_path: str
    model: str
    priority: int = 0
    status: str = "queued"
    branch_name: Optional[str] = None
    budget_usd: float = 1.00
    test_cmd: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class Run:
    id: int
    task_id: int
    started_at: str
    finished_at: Optional[str] = None
    status: str = "running"
    cost_usd: Optional[float] = None
    tokens: int = 0
    files_changed: str = "[]"
    tests_passed: Optional[bool] = None
    notes: Optional[str] = None


@dataclass
class Event:
    id: int
    run_id: int
    timestamp: str
    step: int
    role: str
    tool_name: Optional[str] = None
    arguments_json: Optional[str] = None
    result_summary: Optional[str] = None
    tokens: int = 0
    cost_usd: Optional[float] = None
