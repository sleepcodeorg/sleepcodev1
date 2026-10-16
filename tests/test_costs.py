# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from sleepcode.costs import calculate_cost


def test_calculate_cost_known_model() -> None:
    cost = calculate_cost(
        "openai/gpt-4o-mini", prompt_tokens=1_000_000, completion_tokens=1_000_000
    )
    assert cost is not None
    assert abs(cost - 0.75) < 1e-4  # 0.15 + 0.60


def test_calculate_cost_litellm_override() -> None:
    cost = calculate_cost(
        "unknown-model", prompt_tokens=100, completion_tokens=100, litellm_cost=0.0042
    )
    assert cost == 0.0042


def test_calculate_cost_unknown_model() -> None:
    cost = calculate_cost("custom-local-model", prompt_tokens=1000, completion_tokens=1000)
    assert cost is None
