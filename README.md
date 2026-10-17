# SleepCode

SleepCode is an open-source autonomous coding agent that works while you sleep. Users bring their own API keys (BYOK) and choose a model per task.

---

## First-time Setup (Non-Technical Guide)

SleepCode is designed to run simple commands without requiring deep command-line expertise:

1. **Run the interactive setup wizard:**
   ```bash
   sleepcode setup
   ```
   Follow the prompts to select your provider (e.g., Groq, OpenAI, Anthropic), paste your API key (hidden as you type), set default model strings, and set daily budgets.

2. **Run doctor diagnostics:**
   ```bash
   sleepcode doctor
   ```
   This verifies your Python version, Git installation, configuration file permissions (`0600`), API key settings, and queue database accessibility.

3. **Queue a coding task:**
   ```bash
   sleepcode queue add "Fix failing tests in user auth module" --repo ~/projects/app
   ```

4. **Start the overnight runner:**
   ```bash
   sleepcode night start --window 23:00-07:00 --budget-usd 5.00
   ```

5. **Review morning report:**
   ```bash
   sleepcode report --latest
   ```

---

## Quick Start (Developer Usage)

### Installation
```bash
pip install -e ".[dev]"
```

### Direct CLI Execution
```bash
sleepcode run "Create a python script hello.py that prints Hello World" \
  --workspace ./sample \
  --model openai/gpt-4o-mini
```

### Safe Shell & Test-Repair Loop
```bash
sleepcode run "Fix failing tests in user auth module" \
  --workspace ./sample \
  --model openai/gpt-4o-mini \
  --allow-shell \
  --test-cmd "pytest -q" \
  --repair-attempts 2
```

## Safety Note
The `--allow-shell` flag enables shell execution (`run_shell`) and local git tools (`git_status`, `git_diff`, `git_create_branch`, `git_commit`). The allowlist and operator rejection filters reduce accidental errors, but **they do NOT constitute a security sandbox**. Runtimes like `python` and `pytest` can execute arbitrary code inside the workspace. During overnight runs (`sleepcode night start`), commits are strictly isolated to task branches, secret files (`.env`, `*.key`) are blocked from commits, and zero push operations are performed. See `docs/safety.md` for full details.

## Running Tests and Verification
```bash
bash scripts/verify.sh
```

### Running Live Tests (Optional)
To run live end-to-end tests against real provider models:
```bash
export OPENAI_API_KEY="your-api-key"
export SLEEPCODE_LIVE_TEST=1
pytest tests/test_live.py
```

## License
SleepCode is licensed under the [Apache License 2.0](LICENSE).
