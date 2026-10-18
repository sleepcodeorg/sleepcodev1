# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os

import httpx
import pytest

from sleepcode.web.cache import WebCache, get_cache_dir
from sleepcode.web.fetch import web_fetch


def test_cache_hit_makes_zero_mock_requests(tmp_path, monkeypatch):
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    cache = WebCache()

    request_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        url_str = str(request.url)
        if "robots.txt" in url_str:
            return httpx.Response(404)
        return httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            html="<html><head><title></title></head><body>Content</body></html>",
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    def fake_dns(host: str):
        return ["93.184.216.34"]

    # First fetch -> calls network
    res1 = web_fetch(
        url="https://example.com/cached",
        allowed_domains=["example.com"],
        dns_resolver=fake_dns,
        client=client,
        cache=cache,
    )
    assert res1.text == "Content"
    initial_count = request_count

    # Second fetch -> served from cache without any mock transport calls
    res2 = web_fetch(
        url="https://example.com/cached",
        allowed_domains=["example.com"],
        dns_resolver=fake_dns,
        client=client,
        cache=cache,
    )
    assert res2.text == "Content"
    assert request_count == initial_count


def test_cache_file_created_with_0600_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    cache = WebCache()

    url = "https://example.com/mode_check"
    cache.set(url, {"url": url, "text": "sample"})

    cache_dir = get_cache_dir()
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1

    mode = os.stat(cache_files[0]).st_mode
    assert (mode & 0o777) == 0o600


def test_policy_failing_url_never_served_from_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    cache = WebCache()

    # Seed cache with data for a forbidden scheme
    forbidden_url = "file:///etc/passwd"
    cache.set(forbidden_url, {"url": forbidden_url, "text": "secret shadow file"})

    # Fetch should refuse at URL policy validation before checking cache
    with pytest.raises(ValueError) as exc_info:
        web_fetch(
            url=forbidden_url,
            allowed_domains=["*"],
            cache=cache,
        )

    assert "Fetch refused by URL policy" in str(exc_info.value)
