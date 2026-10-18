# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import httpx
import pytest

from sleepcode.web.audit import clear_audit_log, get_latest_audit_log
from sleepcode.web.fetch import web_fetch
from sleepcode.web.search.brave import BraveSearchProvider
from sleepcode.web.search.searxng import SearXNGSearchProvider


def test_brave_search_mock():
    fake_key = "fake-brave-key-for-tests"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == fake_key
        assert "q=python" in str(request.url)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Python Website",
                            "url": "https://www.python.org",
                            "description": "Python language homepage",
                        }
                    ]
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key=fake_key, client=client)

    results = provider.search("python", max_results=5)
    assert len(results) == 1
    assert results[0].title == "Python Website"
    assert results[0].source == "Brave"


def test_brave_search_key_redacted_on_error():
    fake_key = "fake-secret-brave-key-12345"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid token key fake-secret-brave-key-12345"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = BraveSearchProvider(api_key=fake_key, client=client)

    with pytest.raises(RuntimeError) as exc_info:
        provider.search("test")

    err_msg = str(exc_info.value)
    assert fake_key not in err_msg
    assert "[REDACTED]" in err_msg


def test_searxng_search_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "SearXNG Result",
                        "url": "https://searx.space",
                        "content": "SearXNG engine",
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SearXNGSearchProvider(base_url="https://searx.local", client=client)

    results = provider.search("query")
    assert len(results) == 1
    assert results[0].title == "SearXNG Result"
    assert results[0].source == "SearXNG"


def test_web_fetch_basic_and_audit():
    clear_audit_log()

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "robots.txt" in url_str:
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            html="<html><head><title>Test Page</title></head>"
            "<body><h1>Hello World</h1></body></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    res = web_fetch(
        url="https://docs.python.org/3/",
        allowed_domains=["docs.python.org"],
        dns_resolver=lambda h: ["93.184.216.34"],
        client=client,
    )

    assert res.status == 200
    assert res.title == "Test Page"
    assert "Hello World" in res.text

    audit = get_latest_audit_log()
    assert len(audit) > 0
    assert audit[-1]["target"] == "https://docs.python.org/3/"
    assert audit[-1]["status"] == "200 OK"


def test_web_fetch_redirect_to_private_ip_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "robots.txt" in url_str:
            return httpx.Response(404)
        if url_str == "https://docs.python.org/start":
            return httpx.Response(302, headers={"Location": "http://internal.private.net/secret"})
        return httpx.Response(200, text="Secret")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    def mock_dns(host: str):
        if host == "docs.python.org":
            return ["93.184.216.34"]
        elif host == "internal.private.net":
            return ["10.0.0.5"]
        return []

    with pytest.raises(ValueError) as exc_info:
        web_fetch(
            url="https://docs.python.org/start",
            allowed_domains=["docs.python.org", "internal.private.net"],
            dns_resolver=mock_dns,
            client=client,
        )

    assert "refused by URL policy" in str(exc_info.value)


def test_web_fetch_disallowed_content_type():
    def handler(request: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(request.url):
            return httpx.Response(404)
        return httpx.Response(200, headers={"Content-Type": "application/pdf"}, content=b"%PDF-1.4")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError) as exc_info:
        web_fetch(
            url="https://docs.python.org/doc.pdf",
            allowed_domains=["docs.python.org"],
            dns_resolver=lambda h: ["93.184.216.34"],
            client=client,
        )

    assert "Disallowed content type" in str(exc_info.value)
