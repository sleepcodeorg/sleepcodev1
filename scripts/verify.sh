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

echo "=== Step 6: Phase 2 Safety & Tool Registry Checks ==="
python3 -c "
from pathlib import Path
from sleepcode.cli import app, set_test_provider_override
from sleepcode.providers.fake_provider import FakeProvider
from sleepcode.providers.base import ProviderResponse
from sleepcode.tools.registry import ToolRegistry
from typer.testing import CliRunner

# Check 1: run_shell tool absent when --allow-shell is NOT passed
runner = CliRunner()
fake_resp = ProviderResponse(text='Done', tool_calls=[])
set_test_provider_override(FakeProvider([fake_resp]))

ws_dir = Path('/tmp/sleepcode-verify-test')
ws_dir.mkdir(parents=True, exist_ok=True)

res_no_shell = runner.invoke(app, ['run', 'test task', '--workspace', str(ws_dir), '--model', 'openai/gpt-4o-mini'])
assert res_no_shell.exit_code == 0, f'CLI run failed: {res_no_shell.output}'

# Check tool registry schema directly
reg_default = ToolRegistry()
schemas = [s['function']['name'] for s in reg_default.get_schemas()]
assert 'run_shell' not in schemas, 'run_shell tool present without --allow-shell'
assert 'git_status' not in schemas, 'git_status tool present without --allow-shell'
print('Verified: run_shell and git tools absent without --allow-shell')
"

echo "=== Step 7: Night-git safety checks ==="
pytest tests/test_night_git_safety.py -q

echo "=== Step 8: Prohibit 'git push' in src/ ==="
if grep -rnEI "git push" src/; then
    echo "ERROR: 'git push' string found in src/"
    exit 1
fi
echo "Verified: No 'git push' string in src/"

echo "=== Step 9: Prohibit key prompts without getpass in src/ ==="
python3 -c "
import inspect
import sleepcode.setup_wizard
src_code = inspect.getsource(sleepcode.setup_wizard)
assert 'getpass' in src_code, 'getpass not found in setup_wizard.py'
print('Verified: getpass is used for key prompt in setup_wizard.py')
"

echo "=== Step 10: License, NOTICE, and SPDX headers check ==="
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

echo "=== Step 11: Key pattern leakage check ==="
KEY_LEAKS=$(grep -rnEI --exclude="test_secrets.py" 'sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}' src/ tests/ docs/ || true)
if [ -n "$KEY_LEAKS" ]; then
    echo "ERROR: Potential real API key pattern found outside test_secrets.py:"
    echo "$KEY_LEAKS"
    exit 1
fi

echo "=== Step 12: Phase 3.5 Web Policy & Prompt Injection Checks ==="
pytest tests/test_web_policy.py tests/test_web_injection.py -q

echo "=== Step 13: Prohibit 'shell=True' in src/ ==="
if grep -rnEI "shell=True" src/; then
    echo "ERROR: 'shell=True' found in src/"
    exit 1
fi
echo "Verified: No 'shell=True' found in src/"

echo "=== Step 14: CLI e2e test with fake provider ==="
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
