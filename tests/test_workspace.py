# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path

import pytest

from sleepcode.workspace import Workspace, WorkspaceError


def test_workspace_valid(tmp_path: Path) -> None:
    ws = Workspace(tmp_path)
    res = ws.resolve_path("file.txt")
    assert res == tmp_path / "file.txt"


def test_workspace_nonexistent_root(tmp_path: Path) -> None:
    bad_root = tmp_path / "nonexistent"
    with pytest.raises(WorkspaceError, match="does not exist"):
        Workspace(bad_root)


def test_workspace_absolute_path_outside(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    ws = Workspace(ws_dir)

    outside = tmp_path / "outside.txt"
    with pytest.raises(WorkspaceError, match="outside workspace root"):
        ws.resolve_path(outside)


def test_workspace_relative_traversal(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    ws = Workspace(ws_dir)

    with pytest.raises(WorkspaceError, match="outside workspace root"):
        ws.resolve_path("../outside.txt")


def test_workspace_nested_traversal(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    ws = Workspace(ws_dir)

    with pytest.raises(WorkspaceError, match="outside workspace root"):
        ws.resolve_path("a/../../b.txt")


def test_workspace_symlink_pointing_outside(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret")

    symlink_path = ws_dir / "link.txt"
    try:
        os.symlink(outside_file, symlink_path)
    except OSError:
        pytest.skip("Symlinks not supported in this environment")

    ws = Workspace(ws_dir)
    with pytest.raises(WorkspaceError, match="outside workspace root"):
        ws.resolve_path("link.txt")


def test_workspace_symlink_inside_allowed(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    ws_dir.mkdir()
    inside_file = ws_dir / "real.txt"
    inside_file.write_text("hello")

    link_path = ws_dir / "link.txt"
    try:
        os.symlink(inside_file, link_path)
    except OSError:
        pytest.skip("Symlinks not supported in this environment")

    ws = Workspace(ws_dir)
    res = ws.resolve_path("link.txt")
    assert res == inside_file.resolve()
