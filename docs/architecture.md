# Architecture

## Overview
SleepCode Phase 1 provides the core foundation for an autonomous coding agent. It is designed to run locally, accept user tasks, use LLMs via LiteLLM, execute workspace tools, and enforce strict token, cost, time, and safety limits.

## Core Components
- **CLI (`sleepcode.cli`)**: Typer and Rich-based interface for commands (`version`, `config set-key`, `config list`, `run`).
- **Workspace (`sleepcode.workspace`)**: Path sandboxing ensuring file operations remain inside the designated root directory, blocking relative traversals and symlink escapes.
- **Provider Layer (`sleepcode.providers`)**:
  - `Provider` (ABC): Standardized LLM interface.
  - `LiteLLMProvider`: Multi-backend provider supporting OpenAI, Anthropic, Groq, Gemini, OpenRouter, Mistral, and Ollama with retries on transient errors.
  - `FakeProvider`: Deterministic mock provider for offline tests.
- **Tools (`sleepcode.tools`)**:
  - `read_file`, `write_file`, `edit_file`, `list_dir`, `search`.
  - Output truncation at 20 KB.
- **Agent Loop (`sleepcode.agent.loop`)**:
  - Main loop sending conversation history and tool results to LLMs until completion or limit firing (`max_iterations`, `max_total_tokens`, `max_cost_usd`, `max_wall_seconds`).
  - Supports `--dry-run` mode.
  - Logs structured JSON events with automatic secret redaction to `~/.sleepcode/runs/<run_id>/events.jsonl`.

## Phase 2 to Phase 5 Extension Points
- **Phase 2 (Shell & Git)**: Execution tools will hook into `ToolRegistry` and `Workspace`.
- **Phase 3 (Night Queue)**: Queue manager will replace direct CLI task invocation.
- **Phase 4 (Dashboard & Web UI)**: Web API will read `events.jsonl` run logs.
- **Phase 5 (Plugins & Docker)**: Dynamic tool loading and containerized workspace adapters.
