# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import urllib.parse
from typing import Callable, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from pydantic import BaseModel

from sleepcode.web.audit import record_web_audit_event
from sleepcode.web.cache import WebCache
from sleepcode.web.policy import USER_AGENT, check_robots_allowed, validate_url_policy


class FetchResult(BaseModel):
    url: str
    final_url: str
    status: int
    title: str
    text: str
    truncated: bool


def extract_content_to_text(html_or_text: str, content_type: str) -> Tuple[str, str]:
    """Extract page title and markdown/plain text content from body."""
    main_type = content_type.split(";")[0].strip().lower()

    if main_type in ("text/plain", "text/markdown"):
        return "", html_or_text

    if main_type != "text/html":
        return "", html_or_text

    try:
        soup = BeautifulSoup(html_or_text, "html.parser")
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else ""

        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        cleaned_html = str(soup)
        text_md = md(cleaned_html, heading_style="ATX").strip()
        return title, text_md
    except Exception:
        return "", html_or_text


def web_fetch(
    url: str,
    allowed_domains: List[str],
    dns_resolver: Optional[Callable[[str], List[str]]] = None,
    client: Optional[httpx.Client] = None,
    cache: Optional[WebCache] = None,
    max_redirects: int = 5,
) -> FetchResult:
    """Fetch URL adhering to security policy, redirects, robots.txt, size limits, and cache."""
    ok, reason = validate_url_policy(url, allowed_domains, dns_resolver=dns_resolver)
    if not ok:
        record_web_audit_event("web_fetch", url, f"Policy Refused: {reason}")
        raise ValueError(f"Fetch refused by URL policy: {reason}")

    if cache is not None:
        cached = cache.get(url)
        if cached is not None:
            record_web_audit_event(
                "web_fetch",
                url,
                "200 OK (Cache)",
                bytes_read=len(cached.get("text", "")),
                cache_hit=True,
                truncated=cached.get("truncated", False),
            )
            return FetchResult(**cached)

    if client is None:
        http_client = httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=False,
        )
    else:
        http_client = client

    def fetch_robots(robots_url: str) -> Tuple[Optional[int], Optional[str]]:
        try:
            r = http_client.get(robots_url, follow_redirects=True)
            return r.status_code, r.text
        except Exception:
            return None, None

    robots_ok, robots_reason = check_robots_allowed(url, fetch_robots_fn=fetch_robots)
    if not robots_ok:
        record_web_audit_event("web_fetch", url, f"Robots Refused: {robots_reason}")
        raise ValueError(f"Fetch refused by robots.txt: {robots_reason}")

    current_url = url
    redirect_count = 0
    response: Optional[httpx.Response] = None

    while redirect_count <= max_redirects:
        try:
            response = http_client.get(current_url)
        except Exception as e:
            record_web_audit_event("web_fetch", current_url, f"Network Error: {e}")
            raise RuntimeError(f"Network error fetching '{current_url}': {e}") from None

        if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if not location:
                record_web_audit_event("web_fetch", current_url, "Redirect missing location header")
                raise ValueError("Redirect response missing Location header.")

            next_url = urllib.parse.urljoin(current_url, location)
            redirect_count += 1
            if redirect_count > max_redirects:
                record_web_audit_event("web_fetch", next_url, "Exceeded max redirects (5)")
                raise ValueError("Exceeded maximum redirect limit (5 hops).")

            val_ok, val_reason = validate_url_policy(
                next_url, allowed_domains, dns_resolver=dns_resolver
            )
            if not val_ok:
                record_web_audit_event(
                    "web_fetch", next_url, f"Redirect Policy Refused: {val_reason}"
                )
                raise ValueError(f"Redirect to '{next_url}' refused by URL policy: {val_reason}")

            current_url = next_url
        else:
            break

    assert response is not None
    final_url = current_url
    status_code = response.status_code

    content_type = response.headers.get("content-type", "text/html")
    main_type = content_type.split(";")[0].strip().lower()
    if main_type not in ("text/html", "text/plain", "text/markdown"):
        record_web_audit_event("web_fetch", final_url, f"Disallowed Content-Type: {content_type}")
        raise ValueError(
            f"Disallowed content type '{content_type}'. Only HTML, plain text, and Markdown allowed"
        )

    raw_content = response.content
    is_truncated = False
    if len(raw_content) > 2 * 1024 * 1024:
        raw_content = raw_content[: 2 * 1024 * 1024]
        is_truncated = True

    decoded_text = raw_content.decode("utf-8", errors="replace")
    title, text_content = extract_content_to_text(decoded_text, content_type)

    if len(text_content) > 8000:
        text_content = text_content[:7980] + "\n[content truncated]"
        is_truncated = True

    result = FetchResult(
        url=url,
        final_url=final_url,
        status=status_code,
        title=title,
        text=text_content,
        truncated=is_truncated,
    )

    if cache is not None:
        cache.set(url, result.model_dump())

    record_web_audit_event(
        "web_fetch",
        final_url,
        f"{status_code} OK",
        bytes_read=len(raw_content),
        cache_hit=False,
        truncated=is_truncated,
    )

    return result
