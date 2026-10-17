# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from datetime import datetime, time

from sleepcode.night.window import WindowManager, is_time_in_window, parse_window


def test_parse_window() -> None:
    start, end = parse_window("23:00-07:00")
    assert start == time(23, 0)
    assert end == time(7, 0)


def test_is_time_in_window_same_day() -> None:
    start = time(9, 0)
    end = time(17, 0)

    dt_inside = datetime(2026, 1, 1, 12, 0)
    assert is_time_in_window(dt_inside, start, end) is True

    dt_outside = datetime(2026, 1, 1, 18, 0)
    assert is_time_in_window(dt_outside, start, end) is False


def test_is_time_in_window_midnight_crossing() -> None:
    start = time(23, 0)
    end = time(7, 0)

    dt_2330 = datetime(2026, 1, 1, 23, 30)
    assert is_time_in_window(dt_2330, start, end) is True

    dt_0200 = datetime(2026, 1, 2, 2, 0)
    assert is_time_in_window(dt_0200, start, end) is True

    dt_1200 = datetime(2026, 1, 1, 12, 0)
    assert is_time_in_window(dt_1200, start, end) is False


def test_window_manager_clock_injection() -> None:
    def fake_clock() -> datetime:
        return datetime(2026, 1, 1, 23, 15)

    wm = WindowManager("23:00-07:00", clock=fake_clock)
    assert wm.is_active() is True
