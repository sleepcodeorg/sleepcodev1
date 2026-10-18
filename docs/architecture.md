# Architecture

## Overview
SleepCode (Phases 1-3) provides an autonomous overnight coding agent with safe shell execution, git tools, an SQLite task queue, overnight window/budget execution, secret redaction, and morning report generation. It runs locally, accepts user tasks, uses LLMs via LiteLLM, executes workspace tools, and enforces strict token, cost, time, and safety limits.

## Core Components
- **CLI (`sleepcode.cli`)**: Typer and Rich-based interface for commands (`version`, `config set-key`, `config list`, `run`, `setup`, `doctor`, `queue`, `night`, `report`, `web`).
- **Setup Wizard & Doctor (`sleepcode.setup_wizard`, `sleepcode.doctor`)**:
  - `setup`: Interactive provider selection, hidden API key prompt via `getpass`, file creation mode `0600` at `~/.sleepcode/config.yaml`, and single minimal test call verification.
  - `doctor`: Environment check (Python 3.11+, git, config permissions 0600, API keys, SQLite DB writable).
- **SQLite Task Queue (`sleepcode.queue`)**:
  - DB stored at `~/.sleepcode/sleepcode.db` with schema versioning (`schema_version` table) and migrations.
  - Tables: `tasks`, `runs`, `events`.
  - All database access uses 100% parameterized queries via `TaskRepository`.
- **Night Runner (`sleepcode.night`)**:
  - `window.py`: Evaluates local execution windows (`HH:MM-HH:MM`, handling midnight crossings).
  - `budget.py`: Tracks task and night-wide spend limits.
  - `runner.py`: Claims queued tasks atomically (`queued` -> `running`), manages test-repair loops, and updates run outcomes (`succeeded`, `needs_review`, `failed`).
  - `git_ops.py`: Branch creation (`sleepcode/<slug>-<timestamp>`), HEAD branch restoration, `main`/`master` commit refusal, and secret file pattern checks (`.env`, `*.pem`, `*.key`, `*secret*`).
- **Morning Report & Notifiers (`sleepcode.report`)**:
  - Markdown report generation at `~/.sleepcode/reports/YYYY-MM-DD.md`.
  - Secret redaction and 500-character excerpt truncation.
  - Desktop notification (`notify-send`) and generic webhook sender.
- **Workspace & Safety (`sleepcode.workspace`, `sleepcode.safety`)**:
  - Workspace path sandboxing blocking traversals and symlinks.
  - Command parsing (`shlex`), prohibited operator rejection, executable allowlists, deny patterns, and sanitized environment execution.
- **Provider Layer (`sleepcode.providers`)**:
  - `LiteLLMProvider`: Multi-backend LLM execution with transient error retries.
  - `FakeProvider`: Deterministic mock provider for offline tests.
- **Tools (`sleepcode.tools`)**:
  - Files: `read_file`, `write_file`, `edit_file`, `list_dir`, `search`.
  - Shell & Git: `run_shell`, `git_status`, `git_diff`, `git_create_branch`, `git_commit` (registered only when `--allow-shell` is explicitly passed).
  - Web: `web_search`, `web_fetch` (registered only when tier is `search` and search provider configured).
- **Web & Security (`sleepcode.web`)**:
  - Permission tiers (`off`, `search`), URL policy engine, private IP blocking, 5-hop redirect limits, robots.txt parsing, SHA-256 disk cache (0600), untrusted data wrapping, and audit event logger.

## Future Extension Points (Phases 4-5)
- **Phase 4 (Dashboard & Web UI)**: Web API reading task queue DB and event logs.
- **Phase 5 (Plugins & Docker)**: Containerized sandbox execution and dynamic plugin loading.
