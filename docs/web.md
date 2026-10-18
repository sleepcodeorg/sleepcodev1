# SleepCode Web Search & Permission Tiers Guide

SleepCode allows users to grant controlled internet access to the autonomous agent while enforcing domain allowlists, safety rules, and strict audit logging.

## Permission Tiers

Web access is controlled by four permission tiers:

| Tier | Name | Description |
| --- | --- | --- |
| 0 | `off` | Web access is disabled (default). No web tools are available. |
| 1 | `search` | Agent can perform web searches (`web_search`) and read allowlisted web pages (`web_fetch`). |
| 2 | `read-only browser` | Reserved for future interactive browser capabilities (currently unavailable). |
| 3 | `interactive browser` | Reserved for future full browser automation (currently unavailable). |

### Configuring Tiers via CLI

To check the current tier and allowed domains:
```bash
sleepcode web status
```

To set the global default web permission tier:
```bash
sleepcode web set search
sleepcode web set off
```

To add allowed domains for page fetching:
```bash
sleepcode web allow-domain docs.python.org
sleepcode web allow-domain .python.org  # Subdomain wildcard matching
```

To override the tier per-run:
```bash
sleepcode run "upgrade requests to latest" --repo . --web search
```

Note: A per-run `--web` flag can lower permission tiers or explicitly opt-in to `search` when globally `off`.

### Night Runs
Unattended overnight runs (`sleepcode night start`) default strictly to Tier 0 (`off`). To enable web access for overnight tasks, explicitly pass `--web search`:
```bash
sleepcode night start --web search
```

---

## Security & Untrusted Web Content

Web pages and search results are treated as **untrusted data**, not instructions.

1. **Untrusted Data Wrapper**: All fetched web text and search results are wrapped in fixed `<UNTRUSTED_WEB_CONTENT source="...">` blocks. Any closing tag occurrences inside external page text are automatically sanitized/escaped.
2. **System Rule**: The agent prompt strictly enforces that content inside untrusted blocks cannot authorize tool execution, override safety policies, or issue shell/git instructions.
3. **Network & IP Restrictions**: Page fetching refuses private, loopback, link-local, or cloud metadata IP addresses (`127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`, `::1`), enforces a maximum of 5 redirect hops, checks `robots.txt`, and enforces a 2 MB size cap.

---

## Web Activity Audit Log

Every web search and page fetch is recorded in an in-memory/run audit log. You can inspect recent web activity with:
```bash
sleepcode web log --latest
```
