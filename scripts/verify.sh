#!/usr/bin/env bash
set -e

echo "=== Step 1: Virtual environment & package installation ==="
VENV_DIR=$(mktemp -d -t sleepcode-venv-XXXXXX)
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -e ".[dev]"

echo "=== Step 2: Ruff check ==="
ruff check .

echo "=== Step 3: Ruff format check ==="
ruff format --check .

echo "=== Step 4: Mypy type check ==="
mypy src

echo "=== Step 5: Pytest ==="
pytest -q

echo "=== Step 6: License, NOTICE, and SPDX headers check ==="
if [ ! -f "LICENSE" ]; then
    echo "ERROR: LICENSE file missing"
    exit 1
fi
if [ ! -f "NOTICE" ]; then
    echo "ERROR: NOTICE file missing"
    exit 1
fi

MISSING_HEADERS=0
for f in $(find src -name "*.py"); do
    if ! head -n 5 "$f" | grep -q "SPDX-License-Identifier: Apache-2.0"; then
        echo "ERROR: Missing SPDX header in $f"
        MISSING_HEADERS=1
    fi
done
if [ "$MISSING_HEADERS" -eq 1 ]; then
    exit 1
fi

echo "=== Step 7: Key pattern leakage check ==="
KEY_LEAKS=$(grep -rnEI --exclude="test_secrets.py" 'sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}' src/ tests/ docs/ || true)
if [ -n "$KEY_LEAKS" ]; then
    echo "ERROR: Potential real API key pattern found outside test_secrets.py:"
    echo "$KEY_LEAKS"
    exit 1
fi

echo "=== Step 8: CLI e2e test with fake provider ==="
TEMP_WS=$(mktemp -d -t sleepcode-ws-XXXXXX)
python3 -c "
from pathlib import Path
from sleepcode.cli import app, set_test_provider_override
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.providers.base import ProviderResponse, ToolCall
from typer.testing import CliRunner

fake_resp1 = ProviderResponse(
    text='Creating file',
    tool_calls=[ToolCall(id='tc1', name='write_file', arguments={'path': 'created_by_e2e.py', 'content': 'print(\"e2e\")'})]
)
fake_resp2 = ProviderResponse(text='Done', tool_calls=[])
set_test_provider_override(FakeProvider([fake_resp1, fake_resp2]))

runner = CliRunner()
res = runner.invoke(app, ['run', 'e2e task', '--workspace', '$TEMP_WS', '--model', 'openai/gpt-4o-mini'])
assert res.exit_code == 0, f'CLI run failed: {res.output}'
assert (Path('$TEMP_WS') / 'created_by_e2e.py').exists(), 'e2e file not created'
"

rm -rf "$VENV_DIR" "$TEMP_WS"

echo "VERIFY PASSED"
