# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, Optional

import httpx

from sleepcode.secrets import redact_secrets
from sleepcode.web.search.base import SearchProvider, SearchResult, truncate_search_results

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchProvider(SearchProvider):
    def __init__(self, api_key: str, client: Optional[httpx.Client] = None) -> None:
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=10.0)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        capped_max = min(max(1, max_results), 10)
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params: dict[str, str | int] = {"q": query, "count": capped_max}

        extra_secrets = {self.api_key} if self.api_key else set()

        try:
            response = self.client.get(BRAVE_SEARCH_ENDPOINT, headers=headers, params=params)
            if response.status_code != 200:
                err_text = redact_secrets(response.text, extra_secrets=extra_secrets)
                raise RuntimeError(
                    f"Brave Search failed with status {response.status_code}: {err_text}"
                )
            data: Any = response.json()
        except Exception as e:
            redacted_err = redact_secrets(str(e), extra_secrets=extra_secrets)
            raise RuntimeError(f"Brave Search failed: {redacted_err}") from None

        raw_results: List[SearchResult] = []
        web_items = data.get("web", {}).get("results", [])
        for item in web_items[:capped_max]:
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("description", "")
            raw_results.append(SearchResult(title=title, url=url, snippet=snippet, source="Brave"))

        return truncate_search_results(raw_results)
