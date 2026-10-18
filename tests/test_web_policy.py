# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os

from sleepcode.web.cache import WebCache, get_cache_dir
from sleepcode.web.policy import (
    check_robots_allowed,
    is_domain_allowed,
    is_ip_blocked,
    validate_url_policy,
)


def test_scheme_validation():
    ok, reason = validate_url_policy("file:///etc/passwd", ["example.com"])
    assert not ok
    assert "Disallowed URL scheme" in reason

    ok, _ = validate_url_policy("https://example.com", ["example.com"], lambda h: ["93.184.216.34"])
    assert ok


def test_ip_blocked():
    assert is_ip_blocked("127.0.0.1")
    assert is_ip_blocked("10.0.0.1")
    assert is_ip_blocked("172.16.0.1")
    assert is_ip_blocked("192.168.1.1")
    assert is_ip_blocked("169.254.169.254")
    assert is_ip_blocked("::1")
    assert is_ip_blocked("0.0.0.0")
    assert not is_ip_blocked("93.184.216.34")


def test_dns_resolution_private_ip_rejected():
    ok, reason = validate_url_policy(
        "http://internal.company.local",
        ["internal.company.local"],
        dns_resolver=lambda h: ["10.0.0.5"],
    )
    assert not ok
    assert "resolved to restricted IP" in reason


def test_empty_allowlist_refuses_everything():
    ok, reason = validate_url_policy("https://python.org", [])
    assert not ok
    assert "not in the allowed domains list" in reason


def test_subdomain_matching():
    allowed = [".python.org"]
    assert is_domain_allowed("docs.python.org", allowed)
    assert is_domain_allowed("python.org", allowed)
    assert not is_domain_allowed("evil-python.org", allowed)


def test_robots_txt_checks():
    def mock_fetch_disallowed(url: str):
        return 200, "User-agent: *\nDisallow: /private/"

    ok, _ = check_robots_allowed("https://example.com/public", mock_fetch_disallowed)
    assert ok
    ok, reason = check_robots_allowed("https://example.com/private/data", mock_fetch_disallowed)
    assert not ok
    assert "disallowed by robots.txt" in reason

    ok, _ = check_robots_allowed("https://example.com/page", lambda u: (404, None))
    assert ok

    ok, reason = check_robots_allowed("https://example.com/page", lambda u: (None, None))
    assert not ok
    assert "network error" in reason


def test_web_cache_permissions_and_ttl(tmp_path, monkeypatch):
    monkeypatch.setenv("SLEEPCODE_HOME", str(tmp_path))
    cache = WebCache(ttl_hours=1)

    url = "https://example.com/docs"
    data = {"url": url, "text": "hello cache"}

    cache.set(url, data)

    key_hash = "de106e607d0e711199de3fb7eb98fe5d412ee49ac326eadd3db848ee272ad2cb"
    cache_file = get_cache_dir() / f"{key_hash}.json"
    assert cache_file.exists()

    mode = os.stat(cache_file).st_mode
    assert (mode & 0o777) == 0o600

    cached = cache.get(url)
    assert cached == data
