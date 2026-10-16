# Contributing to SleepCode

Thank you for your interest in contributing to SleepCode!

## Developer Certificate of Origin (DCO) Sign-off

Every commit submitted to SleepCode must be signed off under the Developer Certificate of Origin (DCO).
To sign off your commit, use the `-s` flag when committing:

```bash
git commit -s -m "Your descriptive commit message"
```

By adding `Signed-off-by: Your Name <your.email@example.com>`, you certify that you have the right to submit the code under the Apache 2.0 license.

## Testing and Verification

Before opening a pull request, you must run the verification script and ensure it passes cleanly:

```bash
bash scripts/verify.sh
```

All contributions must pass `ruff`, `mypy`, `pytest`, and all security and header checks.
