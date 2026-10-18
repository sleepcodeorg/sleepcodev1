# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import typer
from rich.console import Console

from sleepcode.config import load_config, save_config
from sleepcode.web.audit import get_latest_audit_log
from sleepcode.web.tiers import parse_web_tier, resolve_effective_web_tier

web_app = typer.Typer(name="web", help="Manage web search and fetch permission tiers.")
console = Console()


@web_app.command("status")
def web_status() -> None:
    """Show current permission tier and allowed domains."""
    config = load_config()
    tier_str = config.web.tier
    allowed = config.web.allowed_domains
    console.print(f"[bold]Current Web Permission Tier:[/bold] {tier_str}")
    if allowed:
        console.print("[bold]Allowed Domains:[/bold]")
        for d in allowed:
            console.print(f"  - {d}")
    else:
        console.print("[bold]Allowed Domains:[/bold] (none)")


@web_app.command("set")
def web_set(tier: str = typer.Argument(..., help="Tier name: 'off' or 'search'")) -> None:
    """Set configured web permission tier ('off' or 'search')."""
    try:
        parsed = parse_web_tier(tier)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from None

    resolve_effective_web_tier(tier, None)

    config = load_config()
    config.web.tier = parsed.name.lower() if hasattr(parsed, "name") else tier.lower()
    save_config(config)
    console.print(f"[bold green]Web permission tier set to '{config.web.tier}'.[/bold green]")


@web_app.command("allow-domain")
def allow_domain(domain: str = typer.Argument(..., help="Domain to add to allowlist")) -> None:
    """Add a domain or subdomain pattern (e.g. docs.python.org or .python.org) to allowlist."""
    config = load_config()
    cleaned = domain.strip().lower()
    if cleaned not in config.web.allowed_domains:
        config.web.allowed_domains.append(cleaned)
        save_config(config)
        console.print(f"[bold green]Added '{cleaned}' to allowed domains.[/bold green]")
    else:
        console.print(f"Domain '{cleaned}' is already in allowed domains.")


@web_app.command("log")
def web_log(
    latest: bool = typer.Option(False, "--latest", help="List URLs/queries accessed in latest run"),
) -> None:
    """Show audit log of web fetches and searches."""
    events = get_latest_audit_log()
    if not events:
        console.print("No web activity recorded.")
        return

    console.print("[bold]Web Access Audit Log:[/bold]")
    for ev in events:
        msg = (
            f"[{ev['timestamp']}] {ev['tool_name']} -> {ev['target']} "
            f"({ev['status']}, {ev['bytes_read']} B, cache_hit={ev['cache_hit']}, "
            f"truncated={ev['truncated']})"
        )
        console.print(msg)
