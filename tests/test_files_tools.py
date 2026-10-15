# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.tools.files import ListDirTool, ReadFileTool, WriteFileTool
from sleepcode.workspace import Workspace


def test_write_and_read_file(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    read_tool = ReadFileTool(temp_workspace)

    w_res = write_tool.run({"path": "sub/hello.txt", "content": "Line 1\nLine 2\nLine 3"})
    assert w_res.ok
    assert "sub/hello.txt" in w_res.files_changed

    r_res = read_tool.run({"path": "sub/hello.txt"})
    assert r_res.ok
    assert r_res.output == "Line 1\nLine 2\nLine 3"


def test_read_file_line_range(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    read_tool = ReadFileTool(temp_workspace)

    write_tool.run({"path": "lines.txt", "content": "L1\nL2\nL3\nL4\nL5"})
    r_res = read_tool.run({"path": "lines.txt", "start_line": 2, "end_line": 4})
    assert r_res.ok
    assert r_res.output == "L2\nL3\nL4\n"


def test_list_dir(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    list_tool = ListDirTool(temp_workspace)

    write_tool.run({"path": "a.txt", "content": "a"})
    write_tool.run({"path": "folder/b.txt", "content": "b"})

    res = list_tool.run({"path": "."})
    assert res.ok
    assert "a.txt" in res.output
    assert "folder/" in res.output


def test_truncation(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    read_tool = ReadFileTool(temp_workspace)

    large_content = "X" * 30_000
    write_tool.run({"path": "big.txt", "content": large_content})

    res = read_tool.run({"path": "big.txt"})
    assert res.ok
    assert "[truncated: 20480 of 30000 bytes shown]" in res.output
