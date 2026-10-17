# SleepCode Safety Model

## Overview
SleepCode introduces safe shell execution (`run_shell`), local Git operations, an SQLite task queue, and an unattended overnight runner (`sleepcode night start`).

## Honest Safety Boundaries: Shell Execution is NOT a Security Sandbox

> **WARNING:** The `run_shell` allowlist and command validation checks reduce operational risk, but they do **NOT** provide a security isolation boundary or sandbox.

When `--allow-shell` is enabled:
- Running `python script.py` or `python -m pytest` executes arbitrary Python code inside the workspace environment.
- `git_commit` runs `git add -A`, which stages non-ignored files in the workspace directory.
- Allowlists and command parsing filters reduce human and LLM errors, but they cannot restrict code execution inside permitted language runtimes.

---

## Unattended Overnight Runs (`sleepcode night start`)

Unattended runs carry higher risk because no human is actively watching terminal output. SleepCode applies stricter safety defaults for overnight execution:

1. **Explicit Shell Opt-In:** Shell and git tools are **OFF** by default during night runs unless `--allow-shell` is explicitly passed in the `sleepcode night start` command line. There is no configuration file setting that turns them on silently.
2. **Task Branch Isolation:** Commits are strictly isolated to dedicated task branches (`sleepcode/<slug>-<timestamp>`). SleepCode refuses to commit on `main` or `master`.
3. **Zero Remote Push Operations:** SleepCode never runs `git push` or transfers git refs to remote repositories.
4. **Secret Path Guard:** Before staging changes on a task branch, SleepCode scans modified/staged files against secret path patterns (`.env`, `*.pem`, `*.key`, `*secret*`). If a match is found, the commit is refused and the runner logs the filename without revealing its content.
5. **Config Permissions Mode `0600`:** Config files containing API keys (`~/.sleepcode/config.yaml`) are created with permission mode `0600` from initial creation.
6. **Automatic Branch Restoration:** SleepCode records the original Git branch before executing a task and restores it after completion.
7. **Strict Budget Caps:** Overnight runs enforce per-task and total-night spending limits. Night execution terminates when either limit is reached.

---

## Default Allowlisted Commands Table

| Command | Category | Capabilities & Permissions | Prohibitions & Safety Restrictions |
| --- | --- | --- | --- |
| `git` | Version Control | Runs `status`, `diff`, `add`, `commit`, `branch` (`--show-current`, `--list`), `checkout` (`-b <name>`), `log`, `rev-parse`. | Global options (`-c`, `--git-dir`, etc.), alias expansions, destructive `checkout` (`--`, `-f`), branch deletion (`-d`, `-D`), and subcommands like `push`, `remote`, `reset`, `clean` are rejected. Refuses commit on `main`/`master`. |
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
- **Phase 3**: Task queue SQLite repository, night runner window/budget limits, task branch isolation, secret file path checks, morning reports.
- **Phase 5 (Planned)**: Containerized workspace isolation using Docker containers with restricted network access and isolated filesystems.
