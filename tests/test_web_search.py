# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import httpx
import pytest

from sleepcode.web.search.brave import BraveSearchProvider
from sleepcode.web.search.searxng import SearXNGSearchProvider


def test_brave_search_request_format_and_parsing():
    fake_key = "fake-search-key-for-tests"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.scheme == "https"
        assert request.url.host == "api.search.brave.com"
        assert request.url.path == "/res/v1/web/search"
        assert request.headers["X-Subscription-Token"] == fake_key
        assert request.headers["Accept"] == "application/json"
        assert "q=python+async" in str(request.url)
        assert "count=5" in str(request.url)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Async Python",
                            "url": "https://docs.python.org/3/library/asyncio.html",
                            "description": "Asynchronous I/O in Python",
                        }
                    ]
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key=fake_key, client=client)

    results = provider.search("python async", max_results=5)
    assert len(results) == 1
    assert results[0].title == "Async Python"
    assert results[0].url == "https://docs.python.org/3/library/asyncio.html"
    assert results[0].snippet == "Asynchronous I/O in Python"
    assert results[0].source == "Brave"


def test_searxng_search_request_format_and_parsing():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        assert "q=sleepcode" in str(request.url)
        assert "format=json" in str(request.url)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "SleepCode Repo",
                        "url": "https://github.com/sleepcode/sleepcode",
                        "content": "Autonomous coding agent",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SearXNGSearchProvider(base_url="https://searx.local", client=client)

    results = provider.search("sleepcode")
    assert len(results) == 1
    assert results[0].title == "SleepCode Repo"
    assert results[0].snippet == "Autonomous coding agent"
    assert results[0].source == "SearXNG"


def test_search_result_caps_and_defaults():
    def handler(request: httpx.Request) -> httpx.Response:
        count = int(request.url.params.get("count", 5))
        items = [
            {"title": f"Result {i}", "url": f"https://example.com/{i}", "description": f"Desc {i}"}
            for i in range(15)
        ]
        return httpx.Response(200, json={"web": {"results": items[:count]}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key="fake-search-key-for-tests", client=client)

    # Default count is 5
    default_res = provider.search("test")
    assert len(default_res) == 5

    # Cap max_results at 10
    capped_res = provider.search("test", max_results=20)
    assert len(capped_res) == 10


def test_search_field_and_total_output_truncation():
    long_title = "A" * 300
    long_snippet = "B" * 700

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": long_title,
                            "url": "https://example.com/long",
                            "description": long_snippet,
                        }
                    ]
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key="fake-search-key-for-tests", client=client)

    results = provider.search("test")
    assert len(results[0].title) <= 200
    assert results[0].title.endswith("...")
    assert len(results[0].snippet) <= 500
    assert results[0].snippet.endswith("...")


def test_search_malformed_response_handled():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOT VALID JSON")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key="fake-search-key-for-tests", client=client)

    with pytest.raises(RuntimeError):
        provider.search("test")


def test_search_key_redacted_in_logs_and_errors(capsys):
    fake_key = "fake-search-key-for-tests"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401, text="Unauthorized: Invalid API key fake-search-key-for-tests provided"
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key=fake_key, client=client)

    with pytest.raises(RuntimeError) as exc_info:
        provider.search("test")

    err_msg = str(exc_info.value)
    assert fake_key not in err_msg
    assert "[REDACTED]" in err_msg

    captured = capsys.readouterr()
    assert fake_key not in captured.out
    assert fake_key not in captured.err
