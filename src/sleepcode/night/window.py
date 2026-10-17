# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, time
from typing import Callable, Optional


def parse_window(window_str: str) -> tuple[time, time]:
    """Parse a time window string in HH:MM-HH:MM format."""
    parts = window_str.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid window format '{window_str}'. Expected HH:MM-HH:MM.")

    def parse_time(t_str: str) -> time:
        t_parts = t_str.strip().split(":")
        if len(t_parts) != 2:
            raise ValueError(f"Invalid time format '{t_str}'. Expected HH:MM.")
        return time(hour=int(t_parts[0]), minute=int(t_parts[1]))

    return parse_time(parts[0]), parse_time(parts[1])


def is_time_in_window(
    now: datetime,
    start_time: time,
    end_time: time,
) -> bool:
    """Check if the given datetime's local time falls within start_time and end_time.

    Handles overnight windows crossing midnight (e.g. 23:00-07:00).
    """
    current_t = now.time()

    if start_time <= end_time:
        return start_time <= current_t <= end_time
    else:
        return current_t >= start_time or current_t <= end_time


class WindowManager:
    """Manages window parsing and active time checks with explicit clock injection."""

    def __init__(
        self,
        window_str: str = "23:00-07:00",
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.start_time, self.end_time = parse_window(window_str)
        self.window_str = window_str
        self.clock = clock or (lambda: datetime.now().astimezone())

    def is_active(self) -> bool:
        now = self.clock()
        return is_time_in_window(now, self.start_time, self.end_time)
