# Instructions for AI Agents working on SleepCode

- **Verification First**: Never claim tests or checks pass unless you run `scripts/verify.sh` and inspect the output.
- **Do Not Weaken Tests**: Never delete, weaken, or skip tests to make the test suite pass. Fix underlying bugs honestly.
- **SPDX License Headers**: Every Python file under `src/` must begin with:
  ```python
  # Copyright 2026 SleepCode contributors
  # SPDX-License-Identifier: Apache-2.0
  ```
- **Secret Redaction**: Ensure all secrets are redacted using `sleepcode.secrets.redact_secrets` before logging or printing exception/tool outputs.
- **Offline Tests**: All unit tests must run fully offline without requiring network access or real API keys.
