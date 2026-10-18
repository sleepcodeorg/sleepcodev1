# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, List, Optional

import httpx

from sleepcode.web.search.base import SearchProvider, SearchResult, truncate_search_results


class SearXNGSearchProvider(SearchProvider):
    def __init__(self, base_url: str, client: Optional[httpx.Client] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.Client(timeout=10.0)

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        capped_max = min(max(1, max_results), 10)
        params = {"q": query, "format": "json"}

        url = f"{self.base_url}/search"

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data: Any = response.json()
        except Exception as e:
            raise RuntimeError(f"SearXNG Search failed: {e}") from None

        raw_results: List[SearchResult] = []
        items = data.get("results", [])
        for item in items[:capped_max]:
            title = item.get("title", "")
            item_url = item.get("url", "")
            snippet = item.get("content", "") or item.get("snippet", "")
            raw_results.append(
                SearchResult(title=title, url=item_url, snippet=snippet, source="SearXNG")
            )

        return truncate_search_results(raw_results)
