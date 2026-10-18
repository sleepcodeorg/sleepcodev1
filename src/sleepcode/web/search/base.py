# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source: str


def truncate_search_results(results: List[SearchResult]) -> List[SearchResult]:
    """Truncate result fields: title <= 200 chars, snippet <= 500 chars."""
    truncated_results: List[SearchResult] = []
    for r in results:
        t_title = r.title if len(r.title) <= 200 else r.title[:197] + "..."
        t_snippet = r.snippet if len(r.snippet) <= 500 else r.snippet[:497] + "..."
        truncated_results.append(
            SearchResult(
                title=t_title,
                url=r.url,
                snippet=t_snippet,
                source=r.source,
            )
        )
    return truncated_results


def format_search_results_output(results: List[SearchResult], total_max_chars: int = 4000) -> str:
    """Format list of SearchResult into text, capped at total_max_chars."""
    lines: List[str] = []
    for idx, r in enumerate(results, 1):
        item_text = f"[{idx}] {r.title}\nURL: {r.url}\nSource: {r.source}\nSnippet: {r.snippet}\n"
        lines.append(item_text)

    full_output = "\n".join(lines)
    if len(full_output) <= total_max_chars:
        return full_output

    truncated_output = full_output[: total_max_chars - 20] + "\n[results truncated]"
    return truncated_output


class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform search query and return SearchResult list."""
        pass
