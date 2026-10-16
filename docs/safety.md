# SleepCode Safety Model

## Overview
SleepCode Phase 2 introduces shell execution (`run_shell`) and local Git operations to enable autonomous agents to test and repair code changes.

## Honest Safety Boundaries: Shell Execution is NOT a Security Sandbox

> **WARNING:** The `run_shell` allowlist and command validation checks reduce operational risk, but they do **NOT** provide a security isolation boundary or sandbox.

When `--allow-shell` is enabled:
- Running `python script.py` or `python -m pytest` executes arbitrary Python code inside the workspace environment.
- `git_commit` runs `git add -A`, which stages every non-ignored file in the workspace directory.
- Allowlists and command parsing filters reduce human and LLM errors, but they cannot restrict code execution inside permitted language runtimes.

---

## Default Allowlisted Commands Table

| Command | Category | Capabilities & Permissions | Prohibitions & Safety Restrictions |
| --- | --- | --- | --- |
| `git` | Version Control | Runs `status`, `diff`, `add` (stages all files via `git add -A`), `commit`, `branch` (`--show-current`, `--list`), `checkout` (`-b <name>` matching `^sleepcode/[a-z0-9-]+-\d{8}-\d{6}$`), `log`, `rev-parse`. | Global options (`-c`, `--git-dir`, `--no-pager`, etc.), alias expansions, destructive `checkout` (`--`, `-f`), branch deletion (`-d`, `-D`), and subcommands like `push`, `remote`, `reset`, `clean` are rejected. Refuses commit on `main`/`master`. |
| `python` / `python3` | Language Runtime | Runs Python script files inside workspace or approved modules (`-m pytest`, `-m ruff`, `-m mypy`). | `-c` (inline code strings) and `-` (stdin code) are prohibited. Can execute arbitrary Python code inside workspace script files. |
| `pytest` | Test Runner | Runs test suites within workspace root. | Executes test code inside Python interpreter (can execute arbitrary code inside workspace). |
| `ruff` | Linter / Formatter | Lints and formats code inside workspace. | Restricted to workspace filesystem scope. |
| `mypy` | Type Checker | Performs static type checking. | Restricted to workspace filesystem scope. |
| `ls` | Inspection | Lists workspace directory entries. | Path escapes outside workspace are blocked. |
| `cat` | Inspection | Reads workspace file contents. | Path escapes outside workspace are blocked. |
| `grep` | Search | Searches text within workspace files. | Path escapes outside workspace are blocked. |

---

## Opt-in Commands (Configurable via `~/.sleepcode/config.yaml`)

Commands such as `npm`, `node`, `make`, `pip` are **NOT** in the default allowlist. They can be opted into by adding them to `allowed_commands` in `config.yaml`. Note that `npm`, `node`, `make`, and `pip` allow arbitrary code execution or package installation during execution.

---

## Isolation Strategy Roadmap
- **Phase 1 & Phase 2**: Process-level validation (`shlex` token parsing, strict subcommand allowlists, flag guards, operator rejection, deny patterns for `sudo`/`chmod`/`rm -rf`, environment secret scrubbing).
- **Phase 5 (Planned)**: Containerized workspace isolation using Docker containers with restricted network access and isolated filesystems.
