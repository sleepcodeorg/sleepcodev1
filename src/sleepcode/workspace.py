# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path


class WorkspaceError(ValueError):
    """Raised when a path safety or workspace boundary check fails."""

    pass


class Workspace:
    """Ensures file system operations remain safely inside a root workspace directory."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise WorkspaceError(f"Workspace root does not exist: {self.root}")
        if not self.root.is_dir():
            raise WorkspaceError(f"Workspace root is not a directory: {self.root}")

    def resolve_path(self, relative_or_abs: Path | str) -> Path:
        """Resolve path relative to root and verify it is strictly within the workspace root."""
        path_obj = Path(relative_or_abs)

        if not path_obj.is_absolute():
            target = self.root / path_obj
        else:
            target = path_obj

        try:
            target_norm = target.resolve(strict=False)
        except Exception as e:
            raise WorkspaceError(f"Invalid path: {relative_or_abs}") from e

        try:
            target_norm.relative_to(self.root)
        except ValueError as e:
            raise WorkspaceError("Access denied: path is outside workspace root.") from e

        current = self.root
        rel_parts = target_norm.relative_to(self.root).parts

        for part in rel_parts:
            current = current / part
            if current.is_symlink():
                resolved_link = current.resolve()
                try:
                    resolved_link.relative_to(self.root)
                except ValueError as e:
                    raise WorkspaceError(
                        "Access denied: symlink points outside workspace root."
                    ) from e

        final_real = target.resolve()
        try:
            final_real.relative_to(self.root)
        except ValueError as e:
            raise WorkspaceError("Access denied: resolved target is outside workspace root.") from e

        return final_real
