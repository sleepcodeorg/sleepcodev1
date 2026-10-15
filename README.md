# SleepCode

SleepCode is an open-source autonomous coding agent that works while you sleep. Users bring their own API keys (BYOK) and choose a model per task.

## Quick Start

### Installation
```bash
pip install -e ".[dev]"
```

### Configure API Key
```bash
sleepcode config set-key openai
```

### Example Task
```bash
sleepcode run "Create a python script hello.py that prints Hello World" \
  --workspace ./sample \
  --model openai/gpt-4o-mini
```

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
