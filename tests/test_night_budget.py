# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.night.budget import NightTracker


def test_night_budget_tracking() -> None:
    tracker = NightTracker(night_budget_usd=5.00)
    assert tracker.get_remaining_budget() == 5.00

    can_start, _ = tracker.can_start_next_task()
    assert can_start is True

    tracker.record_task_cost(2.00, 1.00)
    assert tracker.get_remaining_budget() == 3.00

    effective = tracker.get_task_effective_budget(task_budget_usd=4.00)
    assert effective == 3.00

    tracker.record_task_cost(2.95, 1.00)
    assert round(tracker.get_remaining_budget(), 2) == 0.05

    can_start, reason = tracker.can_start_next_task()
    assert can_start is False
    assert "minimum required $0.10" in reason


def test_night_budget_fallback_when_cost_none() -> None:
    tracker = NightTracker(night_budget_usd=5.00)
    recorded, note = tracker.record_task_cost(cost_usd=None, task_budget_usd=1.50)
    assert recorded == 1.50
    assert tracker.get_remaining_budget() == 3.50
    assert "conservative estimate" in note
