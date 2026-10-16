# SleepCode Safety Model

## Overview
SleepCode Phase 2 introduces shell execution (`run_shell`) and local Git operations to enable autonomous agents to test and repair code changes.

## Honest Safety Boundaries: Shell Execution is NOT a Security Sandbox

> **WARNING:** The `run_shell` allowlist and command validation checks reduce operational risk, but they do **NOT** provide a security isolation boundary or sandbox.

When `--allow-shell` is enabled:
- Executables like `python`, `python3`, `node`, `npm`, and `pytest` are allowed by default.
- Any of these interpreters can execute arbitrary user/LLM-provided Python or JavaScript code inside the host environment and workspace directory.
- `pip` or `npm` can install packages or run install scripts.

### Isolation Strategy Roadmap
- **Phase 1 & Phase 2**: Process-level validation (allowlist, command token parsing via `shlex`, operator rejection, deny patterns for `sudo`/`chmod`/`rm -rf`, environment secret scrubbing).
- **Phase 5 (Planned)**: Full containerized workspace isolation using Docker containers with restricted network access and isolated filesystems.

Do not rely on `--allow-shell` as a security boundary against untrusted or malicious prompts without OS/container-level sandboxing.
