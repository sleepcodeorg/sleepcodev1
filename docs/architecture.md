# Architecture

## Overview
SleepCode Phase 1 & Phase 2 provides the core foundation for an autonomous coding agent with safe shell execution, git tools, and automated test-repair loops. It runs locally, accepts user tasks, uses LLMs via LiteLLM, executes workspace tools, and enforces strict token, cost, time, and safety limits.

## Core Components
- **CLI (`sleepcode.cli`)**: Typer and Rich-based interface for commands (`version`, `config set-key`, `config list`, `run`). Supports `--allow-shell`, `--test-cmd`, `--repair-attempts`.
- **Workspace (`sleepcode.workspace`)**: Path sandboxing ensuring file operations remain inside the designated root directory, blocking relative traversals and symlink escapes.
- **Safety Module (`sleepcode.safety`)**: Command token parsing (`shlex`), prohibited shell control operator checks, executable allowlist, deny pattern checks, and minimal environment building.
- **Provider Layer (`sleepcode.providers`)**:
  - `Provider` (ABC): Standardized LLM interface.
  - `LiteLLMProvider`: Multi-backend provider supporting OpenAI, Anthropic, Groq, Gemini, OpenRouter, Mistral, and Ollama with retries on transient errors.
  - `FakeProvider`: Deterministic mock provider for offline tests.
- **Tools (`sleepcode.tools`)**:
  - Files: `read_file`, `write_file`, `edit_file`, `list_dir`, `search`.
  - Shell: `run_shell` (enabled with `--allow-shell`).
  - Git: `git_status`, `git_diff`, `git_create_branch`, `git_commit` (enabled with `--allow-shell`).
  - Output truncation at 20 KB.
- **Agent Loop & Repair (`sleepcode.agent.loop`, `sleepcode.agent.repair`)**:
  - Main loop sending conversation history and tool results to LLMs until completion or limit firing (`max_iterations`, `max_total_tokens`, `max_cost_usd`, `max_wall_seconds`).
  - Test-repair loop rerunning test commands and feeding failures back into agent context for up to N repair attempts.
  - Supports `--dry-run` mode.
  - Logs structured JSON events with automatic secret redaction to `~/.sleepcode/runs/<run_id>/events.jsonl`.

## Phase 3 to Phase 5 Extension Points
- **Phase 3 (Night Queue)**: Queue manager will replace direct CLI task invocation.
- **Phase 4 (Dashboard & Web UI)**: Web API will read `events.jsonl` run logs.
- **Phase 5 (Plugins & Docker)**: Dynamic tool loading and containerized workspace adapters.
