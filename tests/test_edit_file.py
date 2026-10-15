# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.tools.files import EditFileTool, WriteFileTool
from sleepcode.workspace import Workspace


def test_edit_file_success(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    edit_tool = EditFileTool(temp_workspace)

    write_tool.run({"path": "test.txt", "content": "Hello World\nPython Rulez"})

    res = edit_tool.run({"path": "test.txt", "old_string": "World", "new_string": "SleepCode"})
    assert res.ok
    assert "test.txt" in res.files_changed

    file_content = (temp_workspace.root / "test.txt").read_text()
    assert file_content == "Hello SleepCode\nPython Rulez"


def test_edit_file_zero_matches(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    edit_tool = EditFileTool(temp_workspace)

    write_tool.run({"path": "test.txt", "content": "Hello World"})

    res = edit_tool.run({"path": "test.txt", "old_string": "Nonexistent", "new_string": "X"})
    assert not res.ok
    assert "0 occurrences" in res.output


def test_edit_file_multiple_matches(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    edit_tool = EditFileTool(temp_workspace)

    write_tool.run({"path": "test.txt", "content": "foo bar foo"})

    res = edit_tool.run({"path": "test.txt", "old_string": "foo", "new_string": "baz"})
    assert not res.ok
    assert "matches 2 occurrences" in res.output


def test_edit_file_multiline(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    edit_tool = EditFileTool(temp_workspace)

    write_tool.run({"path": "test.py", "content": "def foo():\n    return 1\n"})

    res = edit_tool.run(
        {
            "path": "test.py",
            "old_string": "def foo():\n    return 1",
            "new_string": "def foo():\n    return 2",
        }
    )
    assert res.ok
    assert (temp_workspace.root / "test.py").read_text() == "def foo():\n    return 2\n"
