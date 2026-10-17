# Copyright 2026 SleepCode contributors
# SPDX-License-Identifier: Apache-2.0

import os
from pathlib import Path
from typing import Dict, Optional

import typer
from rich.console import Console

from sleepcode.config import SleepCodeConfig, get_config_dir, get_config_path
from sleepcode.providers.base import Provider
from sleepcode.providers.litellm_provider import LiteLLMProvider

console = Console()

_test_wizard_provider_override: Optional[Provider] = None


def set_test_wizard_provider_override(provider: Optional[Provider]) -> None:
    """Set provider override for offline tests of setup wizard."""
    global _test_wizard_provider_override
    _test_wizard_provider_override = provider


PROVIDERS = [
    ("groq", "Groq"),
    ("openai", "OpenAI"),
    ("anthropic", "Anthropic"),
    ("gemini", "Gemini"),
    ("openrouter", "OpenRouter"),
    ("mistral", "Mistral"),
    ("ollama", "Ollama local"),
]

DEFAULT_MODELS: Dict[str, str] = {
    "groq": "groq/llama-3.3-70b-versatile",
    "openai": "openai/gpt-4o-mini",
    "anthropic": "anthropic/claude-3-5-haiku-20241022",
    "gemini": "gemini/gemini-1.5-flash",
    "openrouter": "openrouter/auto",
    "mistral": "mistral/mistral-small-latest",
    "ollama": "ollama/llama3",
}


def create_config_file_securely(config: SleepCodeConfig) -> Path:
    """Create or overwrite ~/.sleepcode/config.yaml with 0600 mode from initial creation."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = get_config_path()

    import yaml

    yaml_bytes = yaml.safe_dump(config.model_dump()).encode("utf-8")

    fd = os.open(config_path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    with open(fd, "wb") as f:
        f.write(yaml_bytes)

    return config_path


def test_key_minimal(provider_name: str, key_or_url: str, model_str: str) -> tuple[bool, str]:
    """Perform ONE minimal LLM test call to verify API key or host reachable."""
    if _test_wizard_provider_override is not None:
        try:
            resp = _test_wizard_provider_override.complete(
                messages=[{"role": "user", "content": "hi"}],
                model=model_str,
                max_tokens=5,
            )
            if resp and resp.text:
                return True, "Key works"
            return False, "Provider unreachable"
        except Exception as e:
            return False, f"Provider error: {str(e)}"

    api_key = key_or_url if provider_name != "ollama" else None

    try:
        provider = LiteLLMProvider(api_key=api_key)
        resp = provider.complete(
            messages=[{"role": "user", "content": "hi"}],
            model=model_str,
            max_tokens=5,
        )
        if resp and resp.text:
            return True, "Key works"
        return False, "Provider returned empty response"
    except Exception as e:
        err_msg = str(e).lower()
        if "auth" in err_msg or "key" in err_msg or "401" in err_msg or "403" in err_msg:
            return False, "invalid key"
        if "rate" in err_msg or "429" in err_msg:
            return False, "rate limited"
        if "connection" in err_msg or "unreachable" in err_msg or "timeout" in err_msg:
            return False, "network problem or provider unreachable"
        return False, f"provider error: {str(e)}"


def run_setup() -> None:
    """Run interactive SleepCode setup wizard."""
    console.print("[bold cyan]Welcome to SleepCode Setup Wizard![/bold cyan]\n")

    config_path = get_config_path()
    existing_config: Optional[SleepCodeConfig] = None
    if config_path.exists():
        import yaml

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                existing_config = SleepCodeConfig(**data)
        except Exception:
            existing_config = None

    console.print("Please select your primary LLM provider:")
    for idx, (_p_code, p_label) in enumerate(PROVIDERS, 1):
        console.print(f"  {idx}. {p_label}")

    provider_choice = typer.prompt("\nEnter choice (1-7)", type=int, default=1)
    if not (1 <= provider_choice <= len(PROVIDERS)):
        console.print("[bold red]Invalid choice.[/bold red]")
        raise typer.Exit(code=1)

    provider_code, provider_label = PROVIDERS[provider_choice - 1]

    if existing_config and provider_code in existing_config.keys:
        confirm = typer.confirm(
            f"An API key for '{provider_label}' is already configured. Overwrite?",
            default=False,
        )
        if not confirm:
            console.print("[yellow]Setup cancelled. Existing config kept.[/yellow]")
            return

    key_or_url = ""
    if provider_code == "ollama":
        key_or_url = typer.prompt("Enter Ollama host URL", default="http://localhost:11434")
    else:
        import getpass

        key_or_url = getpass.getpass(f"Enter API key for {provider_label}: ").strip()
        if not key_or_url:
            console.print("[bold red]API key cannot be empty.[/bold red]")
            raise typer.Exit(code=1)

    default_model_suggestion = DEFAULT_MODELS.get(provider_code, f"{provider_code}/default")
    console.print("\n[dim]Note: Check provider's docs for current model names.[/dim]")
    model_str = typer.prompt("Default model string", default=default_model_suggestion).strip()

    _task_budget = typer.prompt("Default budget per task (USD)", type=float, default=1.00)
    _night_budget = typer.prompt("Default budget per night (USD)", type=float, default=5.00)

    console.print("\nTesting provider connection with 1 minimal call...")
    success, reason = test_key_minimal(provider_code, key_or_url, model_str)
    if success:
        console.print("[bold green]Key works![/bold green]")
    else:
        warn_msg = (
            f"[bold yellow]Warning: Key test failed ({reason}). "
            "Config will still be saved.[/bold yellow]"
        )
        console.print(warn_msg)

    config = existing_config or SleepCodeConfig()
    config.keys[provider_code] = key_or_url
    config.default_model = model_str

    created_path = create_config_file_securely(config)
    msg = f"\n[bold green]Configuration saved securely to {created_path} (mode 0600)[/bold green]"
    console.print(msg)
