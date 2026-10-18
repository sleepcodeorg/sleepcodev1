# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import ipaddress
import socket
import urllib.parse
import urllib.robotparser
from typing import Callable, List, Optional, Tuple

USER_AGENT = "SleepCode-Agent/0.1.0 (+https://github.com/sleepcode/sleepcode)"

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def default_dns_resolver(hostname: str) -> List[str]:
    """Resolve hostname to list of IP string addresses using socket.getaddrinfo."""
    try:
        infos = socket.getaddrinfo(hostname, None)
        ips = list({str(info[4][0]) for info in infos})
        return ips
    except Exception:
        return []


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP string belongs to private, loopback, link-local, or reserved ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return True

    for net in BLOCKED_IP_NETWORKS:
        if ip in net:
            return True

    return False


def is_domain_allowed(host: str, allowed_domains: List[str]) -> bool:
    """Check host against domain allowlist."""
    if not allowed_domains:
        return False

    host_lower = host.strip().lower()

    for allowed in allowed_domains:
        allowed_lower = allowed.strip().lower()
        if not allowed_lower:
            continue
        if allowed_lower.startswith("."):
            domain_suffix = allowed_lower[1:]
            if host_lower == domain_suffix or host_lower.endswith("." + domain_suffix):
                return True
        else:
            if host_lower == allowed_lower:
                return True

    return False


def validate_url_policy(
    url: str,
    allowed_domains: List[str],
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
) -> Tuple[bool, str]:
    """Validate URL against scheme, allowlist, and IP restrictions."""
    if dns_resolver is None:
        dns_resolver = default_dns_resolver

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are allowed."

    host = parsed.hostname
    if not host:
        return False, "URL missing host component."

    if not is_domain_allowed(host, allowed_domains):
        return False, f"Domain '{host}' is not in the allowed domains list."

    try:
        ipaddress.ip_address(host)
        if is_ip_blocked(host):
            return False, f"Host IP '{host}' is in a private, loopback, or restricted range."
    except ValueError:
        resolved_ips = dns_resolver(host)
        if not resolved_ips:
            return False, f"Failed to resolve host '{host}'."
        for ip in resolved_ips:
            if is_ip_blocked(ip):
                return False, f"Host '{host}' resolved to restricted IP '{ip}'."

    return True, "URL allowed"


def check_robots_allowed(
    url: str,
    fetch_robots_fn: Callable[[str], Tuple[Optional[int], Optional[str]]],
    user_agent: str = USER_AGENT,
) -> Tuple[bool, str]:
    """Check if robots.txt allows fetching url."""
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    status_code, robots_txt = fetch_robots_fn(robots_url)

    if status_code is None:
        return False, f"Failed to fetch robots.txt for {parsed.netloc} due to network error."

    if status_code == 404:
        return True, "robots.txt returned 404 (allowed)"

    if status_code != 200 or robots_txt is None:
        return False, f"robots.txt check returned status {status_code}."

    rfp = urllib.robotparser.RobotFileParser()
    rfp.parse(robots_txt.splitlines())

    if not rfp.can_fetch(user_agent, url) and not rfp.can_fetch("*", url):
        return False, f"URL '{url}' is disallowed by robots.txt."

    return True, "Allowed by robots.txt"
