# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Dict, Optional, Tuple

# Approximate pricing table per 1M tokens: (prompt_price, completion_price)
# Last updated: February 2026
MODEL_PRICES_PER_1M: Dict[str, Tuple[float, float]] = {
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "anthropic/claude-3-5-sonnet-20241022": (3.00, 15.00),
    "groq/llama-3.3-70b-versatile": (0.59, 0.79),
}


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    litellm_cost: Optional[float] = None,
) -> Optional[float]:
    """Calculate cost in USD given model and token counts.

    Uses litellm_cost if provided. Otherwise checks static price table fallback.
    Returns None if cost is unknown.
    """
    if litellm_cost is not None and litellm_cost >= 0:
        return litellm_cost

    # Check fallback table
    if model in MODEL_PRICES_PER_1M:
        prompt_rate, completion_rate = MODEL_PRICES_PER_1M[model]
        cost = (prompt_tokens / 1_000_000.0) * prompt_rate + (
            completion_tokens / 1_000_000.0
        ) * completion_rate
        return cost

    return None
