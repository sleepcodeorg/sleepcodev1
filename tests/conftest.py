# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path

import pytest

from sleepcode.workspace import Workspace


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Workspace:
    ws_dir = tmp_path / "workspace"
    ws_dir.mkdir()
    return Workspace(ws_dir)


@pytest.fixture
def sleepcode_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home_dir = tmp_path / "sleepcode_home"
    home_dir.mkdir()
    monkeypatch.setenv("SLEEPCODE_HOME", str(home_dir))
    return home_dir
