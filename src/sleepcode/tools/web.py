# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict, List, Optional

import httpx

from sleepcode.tools.base import Tool, ToolResult
from sleepcode.web.audit import record_web_audit_event
from sleepcode.web.cache import WebCache
from sleepcode.web.fetch import web_fetch
from sleepcode.web.search.base import SearchProvider, format_search_results_output
from sleepcode.web.untrusted import wrap_untrusted_content


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web using the configured search provider. "
        "Returns a list of search result snippets."
    )
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5, max 10).",
            },
        },
        "required": ["query"],
    }

    def __init__(self, search_provider: SearchProvider) -> None:
        self.search_provider = search_provider

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        query = str(arguments.get("query", ""))
        max_results = int(arguments.get("max_results", 5))

        try:
            results = self.search_provider.search(query=query, max_results=max_results)
            formatted = format_search_results_output(results)
            wrapped = wrap_untrusted_content(formatted, source=f"web_search:{query}")
            record_web_audit_event(
                tool_name="web_search",
                target=query,
                status="OK",
                bytes_read=len(formatted),
            )
            return ToolResult(ok=True, output=wrapped)
        except Exception as e:
            record_web_audit_event(
                tool_name="web_search",
                target=query,
                status=f"Error: {e}",
            )
            return ToolResult(ok=False, output=f"Web search failed: {e}")


class WebFetchTool(Tool):
    name = "web_fetch"
    description = (
        "Fetch and read the content of a web page URL. Restricted to domains on the allowlist."
    )
    parameters_schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The HTTP or HTTPS URL to fetch.",
            },
        },
        "required": ["url"],
    }

    def __init__(
        self,
        allowed_domains: List[str],
        cache: Optional[WebCache] = None,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self.allowed_domains = allowed_domains
        self.cache = cache or WebCache()
        self.client = client

    def run(self, arguments: Dict[str, Any], dry_run: bool = False) -> ToolResult:
        url = str(arguments.get("url", ""))

        try:
            fetch_res = web_fetch(
                url=url,
                allowed_domains=self.allowed_domains,
                client=self.client,
                cache=self.cache,
            )
            content_block = (
                f"Title: {fetch_res.title}\nFinal URL: {fetch_res.final_url}\n\n{fetch_res.text}"
            )
            wrapped = wrap_untrusted_content(content_block, source=fetch_res.final_url)
            return ToolResult(ok=True, output=wrapped)
        except Exception as e:
            return ToolResult(ok=False, output=f"Web fetch failed: {e}")
