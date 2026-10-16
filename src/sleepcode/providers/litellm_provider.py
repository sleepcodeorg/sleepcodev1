# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import json
import time
from typing import Any, Dict, List, Optional

import litellm

from sleepcode.providers.base import Provider, ProviderResponse, ToolCall
from sleepcode.secrets import redact_secrets

# Transient errors that should be retried with exponential backoff
TRANSIENT_ERRORS = (
    litellm.RateLimitError,  # type: ignore[attr-defined]
    litellm.Timeout,  # type: ignore[attr-defined]
    litellm.APIConnectionError,  # type: ignore[attr-defined]
    litellm.InternalServerError,  # type: ignore[attr-defined]
    litellm.ServiceUnavailableError,  # type: ignore[attr-defined]
    litellm.BadGatewayError,  # type: ignore[attr-defined]
)


class LiteLLMProvider(Provider):
    """LiteLLM-backed provider supporting multiple model backends with retries."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key

    def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        model: str = "",
        max_tokens: int = 4096,
    ) -> ProviderResponse:
        if not model:
            raise ValueError("Model must be specified for LiteLLM completion.")

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        max_attempts = 3
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = litellm.completion(**kwargs)
                return self._parse_response(response, model)
            except Exception as e:
                last_exception = e
                err_str = str(e)
                extra = {self.api_key} if self.api_key else None
                redacted_err = redact_secrets(err_str, extra_secrets=extra)

                if isinstance(e, TRANSIENT_ERRORS) and attempt < max_attempts:
                    time.sleep(2 ** (attempt - 1))
                    continue

                raise RuntimeError(f"LiteLLM completion error: {redacted_err}") from None

        extra_sec = {self.api_key} if self.api_key else None
        redacted_err = redact_secrets(str(last_exception), extra_secrets=extra_sec)
        raise RuntimeError(f"LiteLLM completion failed after retries: {redacted_err}")

    def _parse_response(self, response: Any, model: str) -> ProviderResponse:
        choice = response.choices[0]
        message = choice.message

        text = getattr(message, "content", None)
        raw_tool_calls = getattr(message, "tool_calls", None) or []

        parsed_tool_calls: List[ToolCall] = []
        for tc in raw_tool_calls:
            tc_id = getattr(tc, "id", "")
            func = getattr(tc, "function", None)
            fn_name = getattr(func, "name", "") if func else ""
            fn_args_raw = getattr(func, "arguments", "{}") if func else "{}"

            if isinstance(fn_args_raw, str):
                try:
                    fn_args = json.loads(fn_args_raw)
                except Exception:
                    fn_args = {}
            elif isinstance(fn_args_raw, dict):
                fn_args = fn_args_raw
            else:
                fn_args = {}

            parsed_tool_calls.append(ToolCall(id=tc_id, name=fn_name, arguments=fn_args))

        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
        output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

        cost_usd: Optional[float] = None
        try:
            cost_usd = litellm.completion_cost(completion_response=response)
        except Exception:
            cost_usd = None

        finish_reason = getattr(choice, "finish_reason", None)

        return ProviderResponse(
            text=text,
            tool_calls=parsed_tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            finish_reason=finish_reason,
            cost_usd=cost_usd,
        )
