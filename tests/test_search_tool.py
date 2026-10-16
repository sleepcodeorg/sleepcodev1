# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.tools.files import WriteFileTool
from sleepcode.tools.search import SearchTool
from sleepcode.workspace import Workspace


def test_search_plain_text(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    search_tool = SearchTool(temp_workspace)

    write_tool.run({"path": "a.txt", "content": "hello world\npython programming"})
    write_tool.run({"path": "b.txt", "content": "hello sleepcode"})

    res = search_tool.run({"pattern": "hello"})
    assert res.ok
    assert "a.txt:1:hello world" in res.output
    assert "b.txt:1:hello sleepcode" in res.output


def test_search_regex(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    search_tool = SearchTool(temp_workspace)

    content = "def test_foo():\n    pass\ndef test_bar():\n    pass"
    write_tool.run({"path": "code.py", "content": content})

    res = search_tool.run({"pattern": r"def test_\w+\(\):", "regex": True})
    assert res.ok
    assert "code.py:1:def test_foo():" in res.output
    assert "code.py:3:def test_bar():" in res.output


def test_search_skips_excluded_dirs(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    search_tool = SearchTool(temp_workspace)

    write_tool.run({"path": ".git/config", "content": "secret_key=123"})
    write_tool.run({"path": "node_modules/lib.js", "content": "secret_key=123"})
    write_tool.run({"path": "app.py", "content": "secret_key=123"})

    res = search_tool.run({"pattern": "secret_key"})
    assert res.ok
    assert "app.py:1:secret_key=123" in res.output
    assert ".git" not in res.output
    assert "node_modules" not in res.output


def test_search_match_cap(temp_workspace: Workspace) -> None:
    write_tool = WriteFileTool(temp_workspace)
    search_tool = SearchTool(temp_workspace)

    lines = "\n".join([f"match {i}" for i in range(250)])
    write_tool.run({"path": "many.txt", "content": lines})

    res = search_tool.run({"pattern": "match"})
    assert res.ok
    assert "[capped at 200 matches]" in res.output
