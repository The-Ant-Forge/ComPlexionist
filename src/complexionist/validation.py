"""Configuration validation for ComPlexionist."""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console

from complexionist.config import get_config

console = Console()


@dataclass
class ConnectionTestResult:
    """Result of testing connections to services."""

    # Plex
    plex_ok: bool = False
    plex_server_name: str = ""
    plex_error: str | None = None
    movie_libraries: list[str] = field(default_factory=list)
    tv_libraries: list[str] = field(default_factory=list)

    # TMDB
    tmdb_ok: bool = False
    tmdb_error: str | None = None

    # TVDB
    tvdb_ok: bool = False
    tvdb_error: str | None = None

    @property
    def all_ok(self) -> bool:
        """Check if all configured services connected successfully."""
        return self.plex_ok and self.tmdb_ok and self.tvdb_ok

    @property
    def plex_configured(self) -> bool:
        """Check if Plex is configured (even if connection failed)."""
        cfg = get_config()
        return bool(cfg.plex.servers and cfg.plex.servers[0].url and cfg.plex.servers[0].token)

    @property
    def tmdb_configured(self) -> bool:
        """Check if TMDB is configured."""
        cfg = get_config()
        return bool(cfg.tmdb.api_key)

    @property
    def tvdb_configured(self) -> bool:
        """Check if TVDB is configured."""
        cfg = get_config()
        return bool(cfg.tvdb.api_key)


def test_plex_server(
    url: str, token: str
) -> tuple[bool, str, list[str], list[str]]:
    """Test connection to a specific Plex server.

    Args:
        url: Plex server URL.
        token: Plex auth token.

    Returns:
        Tuple of (success, server_name_or_error, movie_libraries, tv_libraries).
    """
    from complexionist.plex import PlexClient, PlexError

    try:
        plex = PlexClient(url=url, token=token)
        plex.connect()
        server_name = plex.server_name or "Plex Server"
        movie_libs = [lib.title for lib in plex.get_movie_libraries()]
        tv_libs = [lib.title for lib in plex.get_tv_libraries()]
        return True, server_name, movie_libs, tv_libs
    except PlexError as e:
        return False, str(e), [], []


def test_connections(
    plex_url: str | None = None,
    plex_token: str | None = None,
) -> ConnectionTestResult:
    """Test connections to all configured services.

    Args:
        plex_url: Optional Plex URL override (for testing a specific server).
        plex_token: Optional Plex token override.

    Returns:
        ConnectionTestResult with status for each service.
    """
    from complexionist.plex import PlexClient, PlexError
    from complexionist.tmdb import TMDBClient, TMDBError
    from complexionist.tvdb import TVDBClient, TVDBError

    cfg = get_config()
    result = ConnectionTestResult()

    # Use overrides or fall back to config
    url = plex_url or cfg.plex.url
    token = plex_token or cfg.plex.token

    # Test Plex
    if url and token:
        try:
            plex = PlexClient(url=url, token=token)
            plex.connect()
            result.plex_ok = True
            result.plex_server_name = plex.server_name or "Plex Server"
            result.movie_libraries = [lib.title for lib in plex.get_movie_libraries()]
            result.tv_libraries = [lib.title for lib in plex.get_tv_libraries()]
        except PlexError as e:
            result.plex_error = str(e)

    # Test TMDB
    if cfg.tmdb.api_key:
        try:
            tmdb = TMDBClient()
            tmdb.test_connection()
            result.tmdb_ok = True
        except TMDBError as e:
            result.tmdb_error = str(e)

    # Test TVDB
    if cfg.tvdb.api_key:
        try:
            tvdb = TVDBClient()
            tvdb.login()
            result.tvdb_ok = True
        except TVDBError as e:
            result.tvdb_error = str(e)

    return result


def validate_config() -> bool:
    """Validate the current configuration with Rich console output.

    Tests connectivity to:
    - Plex server
    - TMDB API
    - TVDB API (if configured)

    Returns:
        True if all configured services are valid, False otherwise.
    """
    console.print("[bold]Validating Configuration[/bold]")
    console.print()

    result = test_connections()
    all_valid = True

    # Show Plex status
    console.print("Plex Server... ", end="")
    if not result.plex_configured:
        console.print("[yellow]Not configured[/yellow]")
        all_valid = False
    elif result.plex_ok:
        console.print(f"[green]OK[/green] ({result.plex_server_name})")
        if result.movie_libraries:
            console.print(f"  Movie libraries: {', '.join(result.movie_libraries)}")
        if result.tv_libraries:
            console.print(f"  TV libraries: {', '.join(result.tv_libraries)}")
    else:
        console.print(f"[red]Failed[/red] - {result.plex_error}")
        all_valid = False

    # Show TMDB status
    console.print("TMDB API... ", end="")
    if not result.tmdb_configured:
        console.print("[yellow]Not configured[/yellow]")
        all_valid = False
    elif result.tmdb_ok:
        console.print("[green]OK[/green]")
    else:
        console.print(f"[red]Failed[/red] - {result.tmdb_error}")
        all_valid = False

    # Show TVDB status
    console.print("TVDB API... ", end="")
    if not result.tvdb_configured:
        console.print("[yellow]Not configured[/yellow] (TV show gaps won't be detected)")
    elif result.tvdb_ok:
        console.print("[green]OK[/green]")
    else:
        console.print(f"[red]Failed[/red] - {result.tvdb_error}")
        all_valid = False

    console.print()
    if all_valid:
        console.print("[green]Configuration is valid![/green]")
    else:
        console.print("[yellow]Some services are not configured or failed validation.[/yellow]")

    return all_valid


def validate_plex_only() -> bool:
    """Validate only Plex connectivity.

    Returns:
        True if Plex is configured and accessible, False otherwise.
    """
    from complexionist.plex import PlexClient, PlexError

    cfg = get_config()
    if not cfg.plex.url or not cfg.plex.token:
        return False

    try:
        plex = PlexClient()
        plex.connect()
        return True
    except PlexError:
        return False
