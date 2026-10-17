# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Optional


class NightTracker:
    """Tracks night run spend and enforces per-task and total night budget rules."""

    def __init__(self, night_budget_usd: float = 5.00) -> None:
        self.night_budget_usd = night_budget_usd
        self.total_spent_usd: float = 0.0

    def get_remaining_budget(self) -> float:
        return max(0.0, self.night_budget_usd - self.total_spent_usd)

    def can_start_next_task(self) -> tuple[bool, str]:
        remaining = self.get_remaining_budget()
        if remaining < 0.10:
            return (
                False,
                f"Remaining night budget (${remaining:.2f}) is less than minimum required $0.10.",
            )
        return True, "Budget sufficient."

    def get_task_effective_budget(self, task_budget_usd: float) -> float:
        remaining = self.get_remaining_budget()
        return min(task_budget_usd, remaining)

    def record_task_cost(
        self, cost_usd: Optional[float], task_budget_usd: float
    ) -> tuple[float, str]:
        if cost_usd is not None:
            self.total_spent_usd += cost_usd
            return cost_usd, f"Task spent ${cost_usd:.4f}."

        fallback_cost = task_budget_usd
        self.total_spent_usd += fallback_cost
        note = (
            f"Task cost could not be determined. Counted conservative estimate "
            f"of task budget (${fallback_cost:.2f}) toward night spend."
        )
        return fallback_cost, note
