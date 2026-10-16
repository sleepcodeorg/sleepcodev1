# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List

from sleepcode.tools.base import Tool, ToolResult, truncate_output
from sleepcode.workspace import Workspace, WorkspaceError


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read lines from a file. Optionally specify 1-indexed start_line and end_line."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file in workspace"},
            "start_line": {"type": "integer", "description": "1-indexed start line (optional)"},
            "end_line": {"type": "integer", "description": "1-indexed end line (optional)"},
        },
        "required": ["path"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        path_str = arguments.get("path")
        if not path_str:
            return ToolResult(ok=False, output="Error: path parameter is required.")

        try:
            target_path = self.workspace.resolve_path(path_str)
        except WorkspaceError as e:
            return ToolResult(ok=False, output=str(e))

        if not target_path.exists():
            return ToolResult(ok=False, output=f"Error: File '{path_str}' does not exist.")

        if not target_path.is_file():
            return ToolResult(ok=False, output=f"Error: Path '{path_str}' is not a file.")

        try:
            content = target_path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult(ok=False, output=f"Error reading file: {str(e)}")

        lines = content.splitlines(keepends=True)
        start_line = arguments.get("start_line")
        end_line = arguments.get("end_line")

        if start_line is not None or end_line is not None:
            total_lines = len(lines)
            s_idx = max(0, (start_line or 1) - 1)
            e_idx = end_line if end_line is not None else total_lines
            selected_lines = lines[s_idx:e_idx]
            out = "".join(selected_lines)
        else:
            out = content

        return ToolResult(ok=True, output=truncate_output(out), files_changed=[])


class WriteFileTool(Tool):
    name = "write_file"
    description = "Create or overwrite a file with full content."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file in workspace"},
            "content": {"type": "string", "description": "Content to write into file"},
        },
        "required": ["path", "content"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        path_str = arguments.get("path")
        content = arguments.get("content", "")

        if not path_str:
            return ToolResult(ok=False, output="Error: path parameter is required.")

        try:
            target_path = self.workspace.resolve_path(path_str)
        except WorkspaceError as e:
            return ToolResult(ok=False, output=str(e))

        rel_path_str = str(target_path.relative_to(self.workspace.root))

        if dry_run:
            return ToolResult(
                ok=True,
                output=f"[Dry Run] Would write to '{rel_path_str}' ({len(content)} characters).",
                files_changed=[rel_path_str],
            )

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")
            return ToolResult(
                ok=True,
                output=f"Successfully wrote {len(content)} characters to '{rel_path_str}'.",
                files_changed=[rel_path_str],
            )
        except Exception as e:
            return ToolResult(ok=False, output=f"Error writing file: {str(e)}")


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace exactly one occurrence of old_string with new_string in a file."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path to file in workspace"},
            "old_string": {"type": "string", "description": "String to find and replace"},
            "new_string": {"type": "string", "description": "Replacement string"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        path_str = arguments.get("path")
        old_string = arguments.get("old_string")
        new_string = arguments.get("new_string")

        if not path_str:
            return ToolResult(ok=False, output="Error: path parameter is required.")
        if old_string is None or old_string == "":
            return ToolResult(ok=False, output="Error: old_string cannot be empty.")
        if new_string is None:
            return ToolResult(ok=False, output="Error: new_string parameter is required.")

        try:
            target_path = self.workspace.resolve_path(path_str)
        except WorkspaceError as e:
            return ToolResult(ok=False, output=str(e))

        if not target_path.exists() or not target_path.is_file():
            return ToolResult(ok=False, output=f"Error: File '{path_str}' does not exist.")

        try:
            content = target_path.read_text(encoding="utf-8")
        except Exception as e:
            return ToolResult(ok=False, output=f"Error reading file: {str(e)}")

        count = content.count(old_string)
        if count == 0:
            msg = "Error: old_string not found in file (0 occurrences)."
            return ToolResult(ok=False, output=msg)
        if count > 1:
            msg = (
                f"Error: old_string matches {count} occurrences in file. "
                "Must match exactly 1 occurrence."
            )
            return ToolResult(ok=False, output=msg)

        rel_path_str = str(target_path.relative_to(self.workspace.root))

        if dry_run:
            return ToolResult(
                ok=True,
                output=f"[Dry Run] Would edit '{rel_path_str}' (replaced 1 occurrence).",
                files_changed=[rel_path_str],
            )

        new_content = content.replace(old_string, new_string, 1)
        try:
            target_path.write_text(new_content, encoding="utf-8")
            return ToolResult(
                ok=True,
                output=f"Successfully edited '{rel_path_str}'.",
                files_changed=[rel_path_str],
            )
        except Exception as e:
            return ToolResult(ok=False, output=f"Error writing edited file: {str(e)}")


class ListDirTool(Tool):
    name = "list_dir"
    description = "List entries in a directory inside workspace. Directories end with '/'."
    parameters_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative directory path (default '.')"},
        },
    }

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        path_str = arguments.get("path") or "."

        try:
            target_path = self.workspace.resolve_path(path_str)
        except WorkspaceError as e:
            return ToolResult(ok=False, output=str(e))

        if not target_path.exists():
            return ToolResult(ok=False, output=f"Error: Directory '{path_str}' does not exist.")

        if not target_path.is_dir():
            return ToolResult(ok=False, output=f"Error: Path '{path_str}' is not a directory.")

        try:
            entries: List[str] = []
            for item in sorted(target_path.iterdir()):
                if item.is_dir():
                    entries.append(f"{item.name}/")
                else:
                    entries.append(item.name)
            out = "\n".join(entries) if entries else "[empty directory]"
            return ToolResult(ok=True, output=truncate_output(out), files_changed=[])
        except Exception as e:
            return ToolResult(ok=False, output=f"Error listing directory: {str(e)}")
