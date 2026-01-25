"""First-run setup wizard for ComPlexionist."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from complexionist.config import find_config_file, reset_config, save_default_config

console = Console()


def _prompt_url(prompt_text: str, default: str | None = None) -> str:
    """Prompt for a URL with validation.

    Args:
        prompt_text: The prompt to display.
        default: Default value (optional).

    Returns:
        Validated URL string.
    """
    while True:
        if default:
            value = Prompt.ask(prompt_text, default=default)
        else:
            value = Prompt.ask(prompt_text)

        value = value.strip()

        if not value:
            console.print("[red]URL cannot be empty.[/red]")
            continue

        if not value.startswith(("http://", "https://")):
            console.print("[red]URL must start with http:// or https://[/red]")
            continue

        return value


def _prompt_token(prompt_text: str, min_length: int = 10) -> str:
    """Prompt for a token/key with validation.

    Args:
        prompt_text: The prompt to display.
        min_length: Minimum required length.

    Returns:
        Validated token string.
    """
    while True:
        value = Prompt.ask(prompt_text)
        value = value.strip()

        if not value:
            console.print("[red]This field cannot be empty.[/red]")
            continue

        if len(value) < min_length:
            console.print(f"[red]Value seems too short (minimum {min_length} characters).[/red]")
            continue

        return value


def _test_plex_connection(url: str, token: str) -> tuple[bool, str]:
    """Test Plex server connection.

    Returns:
        Tuple of (success, message).
    """
    import requests

    try:
        # Try to get server identity
        response = requests.get(
            f"{url.rstrip('/')}/identity",
            headers={"X-Plex-Token": token, "Accept": "application/json"},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "Connected to Plex server"
        elif response.status_code == 401:
            return False, "Invalid Plex token"
        else:
            return False, f"Plex returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Cannot connect to Plex server (check URL)"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"


def _test_tmdb_connection(api_key: str) -> tuple[bool, str]:
    """Test TMDB API connection.

    Returns:
        Tuple of (success, message).
    """
    import requests

    try:
        response = requests.get(
            "https://api.themoviedb.org/3/configuration",
            params={"api_key": api_key},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "TMDB API key valid"
        elif response.status_code == 401:
            return False, "Invalid TMDB API key"
        else:
            return False, f"TMDB returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"


def _test_tvdb_connection(api_key: str) -> tuple[bool, str]:
    """Test TVDB API connection.

    Returns:
        Tuple of (success, message).
    """
    import requests

    try:
        response = requests.post(
            "https://api4.thetvdb.com/v4/login",
            json={"apikey": api_key},
            timeout=10,
        )
        if response.status_code == 200:
            return True, "TVDB API key valid"
        elif response.status_code == 401:
            return False, "Invalid TVDB API key"
        else:
            return False, f"TVDB returned status {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Connection timed out"
    except Exception as e:
        return False, f"Error: {e}"


def _prompt_and_test_plex() -> tuple[str, str]:
    """Prompt for Plex URL and token with live testing.

    Returns:
        Tuple of (url, token).
    """
    from rich.status import Status

    while True:
        plex_url = _prompt_url("Plex server URL", default="http://localhost:32400")
        plex_token = _prompt_token("Plex token", min_length=15)

        with Status("[dim]Testing Plex connection...[/dim]", console=console):
            success, message = _test_plex_connection(plex_url, plex_token)

        if success:
            console.print(f"[green]{message}[/green]")
            return plex_url, plex_token
        else:
            console.print(f"[red]{message}[/red]")
            if not Confirm.ask("Try again?", default=True):
                # Allow skipping validation but warn
                console.print("[yellow]Skipping validation - you can fix this in the config file later.[/yellow]")
                return plex_url, plex_token


def _prompt_and_test_tmdb() -> str:
    """Prompt for TMDB API key with live testing.

    Returns:
        API key string.
    """
    from rich.status import Status

    while True:
        api_key = _prompt_token("TMDB API key", min_length=20)

        with Status("[dim]Testing TMDB API key...[/dim]", console=console):
            success, message = _test_tmdb_connection(api_key)

        if success:
            console.print(f"[green]{message}[/green]")
            return api_key
        else:
            console.print(f"[red]{message}[/red]")
            if not Confirm.ask("Try again?", default=True):
                console.print("[yellow]Skipping validation - you can fix this in the config file later.[/yellow]")
                return api_key


def _prompt_and_test_tvdb() -> str:
    """Prompt for TVDB API key with live testing.

    Returns:
        API key string.
    """
    from rich.status import Status

    while True:
        api_key = _prompt_token("TVDB API key", min_length=30)

        with Status("[dim]Testing TVDB API key...[/dim]", console=console):
            success, message = _test_tvdb_connection(api_key)

        if success:
            console.print(f"[green]{message}[/green]")
            return api_key
        else:
            console.print(f"[red]{message}[/red]")
            if not Confirm.ask("Try again?", default=True):
                console.print("[yellow]Skipping validation - you can fix this in the config file later.[/yellow]")
                return api_key


def detect_first_run() -> bool:
    """Check if this is a first-run (no config exists).

    Returns:
        True if no config file was found, False otherwise.
    """
    return find_config_file() is None


def run_setup_wizard() -> Path | None:
    """Run the interactive setup wizard.

    Guides the user through setting up the minimum required configuration:
    - Plex URL and token
    - TMDB API key
    - TVDB API key

    Returns:
        Path to created config file, or None if cancelled.
    """
    console.print()
    console.print("[bold blue]ComPlexionist Setup Wizard[/bold blue]")
    console.print()
    console.print("You'll need 4 things:")
    console.print("  1. Your Plex server URL (e.g., http://192.168.1.100:32400)")
    console.print("  2. Your Plex token (X-Plex-Token)")
    console.print("  3. A TMDB API key (for movie collection data)")
    console.print("  4. A TVDB API key (for TV episode data)")
    console.print()
    console.print("[dim]This creates the minimum config to get you going.[/dim]")
    console.print("[dim]See complexionist.ini.example for all available options.[/dim]")
    console.print()

    if not Confirm.ask("Ready?", default=True):
        console.print("[yellow]Setup cancelled.[/yellow]")
        return None

    console.print()

    # Plex configuration
    console.print("[bold]1. Plex Server[/bold]")
    console.print(
        "[dim]Find your token: "
        "https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/[/dim]"
    )
    plex_url, plex_token = _prompt_and_test_plex()
    console.print()

    # TMDB configuration
    console.print("[bold]2. TMDB API Key[/bold]")
    console.print(
        "[dim]Get your free API key: https://www.themoviedb.org/settings/api[/dim]"
    )
    tmdb_api_key = _prompt_and_test_tmdb()
    console.print()

    # TVDB configuration
    console.print("[bold]3. TVDB API Key[/bold]")
    console.print(
        "[dim]Get your API key: https://thetvdb.com/api-information[/dim]"
    )
    tvdb_api_key = _prompt_and_test_tvdb()
    console.print()

    # Choose config location
    console.print("[bold]Configuration Location[/bold]")
    config_path = Path.cwd() / "complexionist.ini"
    console.print(f"Config will be saved to: [cyan]{config_path}[/cyan]")

    if not Confirm.ask("Save configuration?", default=True):
        console.print("[yellow]Setup cancelled.[/yellow]")
        return None

    # Save the config
    save_default_config(
        path=config_path,
        plex_url=plex_url,
        plex_token=plex_token,
        tmdb_api_key=tmdb_api_key,
        tvdb_api_key=tvdb_api_key,
    )

    # Reset cached config so validation loads the fresh file
    reset_config()

    console.print()
    console.print(f"[green]Configuration saved to:[/green] {config_path}")
    console.print()
    console.print("[dim]Tip: Edit complexionist.ini to customize options like[/dim]")
    console.print("[dim]exclusions, collection size filters, and more.[/dim]")
    console.print()

    # Offer to validate
    if Confirm.ask("Would you like to test the configuration?", default=True):
        from complexionist.validation import validate_config

        console.print()
        validate_config()

    return config_path


def check_first_run() -> bool:
    """Check for first run and offer to run setup wizard.

    Returns:
        True if setup was completed or config already exists, False if cancelled.
    """
    if not detect_first_run():
        return True

    console.print()
    console.print("[yellow]No configuration file found.[/yellow]")
    console.print()

    if Confirm.ask("Start setup? It's 4 easy steps...", default=True):
        result = run_setup_wizard()
        return result is not None

    console.print()
    console.print("[dim]You can run 'complexionist config init' later to create a config file.[/dim]")
    console.print()
    return False
