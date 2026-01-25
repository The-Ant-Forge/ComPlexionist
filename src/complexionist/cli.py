"""Command-line interface for ComPlexionist."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from complexionist import __version__
from complexionist.config import get_config

if TYPE_CHECKING:
    from complexionist.gaps import EpisodeGapReport, MovieGapReport
    from complexionist.statistics import ScanStatistics

console = Console()

# Plex brand color
PLEX_YELLOW = "#F7C600"


def _show_movie_summary(
    report: MovieGapReport,
    stats: ScanStatistics,
    csv_path: Path | None,
) -> None:
    """Display summary report for movie scan.

    Args:
        report: The movie gap report.
        stats: Scan statistics.
        csv_path: Path to saved CSV file, or None if not saved.
    """
    from datetime import datetime

    from rich.prompt import Confirm

    from complexionist.statistics import calculate_movie_score

    # Calculate score
    total_owned = sum(g.owned_movies for g in report.collections_with_gaps)
    total_missing = report.total_missing
    score = calculate_movie_score(total_owned, total_missing)

    # Report header
    console.print()
    console.print(
        f"[bold]Report:[/bold] {report.library_name} | [bold]Movies[/bold] Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    console.print()

    # Score
    if score >= 90:
        score_color = "green"
    elif score >= 70:
        score_color = "yellow"
    else:
        score_color = "red"
    console.print(
        f"[bold]Library Score:[/bold] [{score_color}]{score:.1f}%[/{score_color}] complete"
    )
    console.print()

    # Stats
    console.print(f"[dim]Collections analyzed:[/dim] {report.unique_collections}")
    console.print(f"[dim]Movies scanned:[/dim] {report.total_movies_scanned}")
    if report.collections_with_gaps:
        console.print(f"[dim]Collections with gaps:[/dim] {len(report.collections_with_gaps)}")
        console.print(f"[dim]Missing movies:[/dim] {report.total_missing}")
    else:
        console.print("[green]All collections are complete![/green]")
    console.print()

    # Performance stats
    console.print(f"[dim]Time taken:[/dim] {stats._format_duration(stats.total_duration)}")
    if stats.cache_hits > 0:
        console.print(
            f"[dim]API calls:[/dim] {stats.total_api_calls} | "
            f"[dim]Cache hits:[/dim] {stats.cache_hits} ({stats.cache_hit_rate:.0f}%)"
        )
    else:
        console.print(f"[dim]API calls:[/dim] {stats.total_api_calls}")
    console.print()

    # CSV saved
    if csv_path:
        console.print(f"[green]CSV saved:[/green] {csv_path}")
        console.print()

    # Offer to show details
    if report.collections_with_gaps:
        if Confirm.ask("View missing movies list?", default=False):
            _output_movies_text(report, verbose=True)


def _show_tv_summary(
    report: EpisodeGapReport,
    stats: ScanStatistics,
    csv_path: Path | None,
) -> None:
    """Display summary report for TV scan.

    Args:
        report: The episode gap report.
        stats: Scan statistics.
        csv_path: Path to saved CSV file, or None if not saved.
    """
    from datetime import datetime

    from rich.prompt import Confirm

    from complexionist.statistics import calculate_tv_score

    # Calculate score
    score = calculate_tv_score(report.shows_with_gaps)

    # Report header
    console.print()
    console.print(
        f"[bold]Report:[/bold] {report.library_name} | [bold]TV[/bold] Scanner | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    console.print()

    # Score
    if score >= 90:
        score_color = "green"
    elif score >= 70:
        score_color = "yellow"
    else:
        score_color = "red"
    console.print(
        f"[bold]Library Score:[/bold] [{score_color}]{score:.1f}%[/{score_color}] complete"
    )
    console.print()

    # Stats
    console.print(f"[dim]Shows analyzed:[/dim] {report.shows_with_tvdb_id}")
    console.print(f"[dim]Episodes owned:[/dim] {report.total_episodes_owned}")
    if report.shows_with_gaps:
        console.print(f"[dim]Shows with gaps:[/dim] {len(report.shows_with_gaps)}")
        console.print(f"[dim]Missing episodes:[/dim] {report.total_missing}")
        # Show top 3 shows with most missing episodes
        sorted_shows = sorted(report.shows_with_gaps, key=lambda s: s.missing_count, reverse=True)
        top_shows = sorted_shows[:3]
        top_shows_str = ", ".join(f"{s.show_title} ({s.missing_count})" for s in top_shows)
        console.print(f"[dim]Top gaps:[/dim] {top_shows_str}")
    else:
        console.print("[green]All shows are complete![/green]")
    console.print()

    # Performance stats
    console.print(f"[dim]Time taken:[/dim] {stats._format_duration(stats.total_duration)}")
    if stats.cache_hits > 0:
        console.print(
            f"[dim]API calls:[/dim] {stats.total_api_calls} | "
            f"[dim]Cache hits:[/dim] {stats.cache_hits} ({stats.cache_hit_rate:.0f}%)"
        )
    else:
        console.print(f"[dim]API calls:[/dim] {stats.total_api_calls}")
    console.print()

    # CSV saved
    if csv_path:
        console.print(f"[green]CSV saved:[/green] {csv_path}")
        console.print()

    # Offer to show details
    if report.shows_with_gaps:
        if Confirm.ask("View missing episodes list?", default=False):
            _output_episodes_text(report, verbose=True)


def _show_splash() -> None:
    """Display the application splash banner."""
    # ASCII art banner (no trailing whitespace)
    banner = r"""
   _____                _____  _           _             _     _
  / ____|              |  __ \| |         (_)           (_)   | |
 | |     ___  _ __ ___ | |__) | | _____  ___  ___  _ __  _ ___| |_
 | |    / _ \| '_ ` _ \|  ___/| |/ _ \ \/ / |/ _ \| '_ \| / __| __|
 | |___| (_) | | | | | | |    | |  __/>  <| | (_) | | | | \__ \ |_
  \_____\___/|_| |_| |_|_|    |_|\___/_/\_\_|\___/|_| |_|_|___/\__|

  """

    # Create styled banner text
    banner_text = Text(banner, style=f"bold {PLEX_YELLOW}")

    # Tagline and version
    tagline = Text(" Completing your Plex Media Server libraries", style="dim")
    version = Text(f"v{__version__}", style="dim")

    # Build the panel content
    content = Text()
    content.append_text(banner_text)
    content.append("\n")
    content.append_text(tagline)
    content.append("  ")
    content.append_text(version)

    panel = Panel(
        content,
        border_style=PLEX_YELLOW,
        padding=(0, 2),
    )
    console.print(panel)


class BannerGroup(click.Group):
    """Custom Click group that shows banner before help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Show banner before help text."""
        _show_splash()
        console.print()
        super().format_help(ctx, formatter)


class BannerCommand(click.Command):
    """Custom Click command that shows banner before help."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Show banner before help text."""
        _show_splash()
        console.print()
        super().format_help(ctx, formatter)


def _show_help_hints() -> None:
    """Display helpful hints for getting started."""
    console.print()
    console.print("[bold]Quick Start:[/bold]")
    console.print(
        f"  [{PLEX_YELLOW}]complexionist movies[/]     Find missing movies in collections"
    )
    console.print(f"  [{PLEX_YELLOW}]complexionist tv[/]         Find missing TV episodes")
    console.print(f"  [{PLEX_YELLOW}]complexionist scan[/]       Scan both libraries")
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(f"  [{PLEX_YELLOW}]complexionist config setup[/]     Run setup wizard")
    console.print(f"  [{PLEX_YELLOW}]complexionist config show[/]      Show current config")
    console.print()
    console.print("[dim]Use --help with any command for more options.[/dim]")
    console.print()


def _has_valid_config() -> bool:
    """Check if configuration has minimum required credentials.

    Returns:
        True if Plex URL, token, TMDB key, and TVDB key are all set.
    """
    from complexionist.config import find_config_file, get_config

    if find_config_file() is None:
        return False

    cfg = get_config()
    return bool(cfg.plex.url and cfg.plex.token and cfg.tmdb.api_key and cfg.tvdb.api_key)


def _run_interactive_start(ctx: click.Context) -> None:
    """Run interactive mode selection when config is valid."""
    console.print()
    console.print("[bold]What would you like to scan?[/bold]")
    console.print()
    console.print(f"  [{PLEX_YELLOW}]M[/] - Movies (find missing collection movies)")
    console.print(f"  [{PLEX_YELLOW}]T[/] - TV Shows (find missing episodes)")
    console.print(f"  [{PLEX_YELLOW}]B[/] - Both")
    console.print()

    choice = Prompt.ask(
        "Select",
        choices=["m", "t", "b", "M", "T", "B"],
        default="M",
        show_choices=False,
    )

    choice = choice.upper()
    console.print()

    if choice == "M":
        ctx.invoke(movies)
    elif choice == "T":
        ctx.invoke(tv)
    elif choice == "B":
        ctx.invoke(scan)


def _handle_no_args(ctx: click.Context) -> None:
    """Handle invocation with no arguments.

    Shows splash banner and either:
    - Offers onboarding wizard if no config exists
    - Offers interactive M/T/B prompt if config is valid
    - Shows help hints otherwise
    """
    from rich.prompt import Confirm

    from complexionist.setup import detect_first_run, run_setup_wizard

    # Always show splash banner
    _show_splash()

    # Check if this is first run (no config)
    if detect_first_run():
        console.print()
        console.print("[yellow]No configuration file found.[/yellow]")
        console.print()

        if Confirm.ask("Start setup? It's 4 easy steps...", default=True):
            result = run_setup_wizard()
            if result is not None:
                # Config created - offer interactive start
                console.print()
                if Confirm.ask("Ready to scan your library?", default=True):
                    _run_interactive_start(ctx)
            return
        else:
            # User declined - save example ini and show help
            console.print()
            example_path = Path.cwd() / "complexionist.ini.example"
            if not example_path.exists():
                # Copy from package or create minimal example
                _save_example_ini(example_path)
                console.print(f"[dim]Example config saved to:[/dim] {example_path}")
            _show_help_hints()
            return

    # Config exists - check if it's valid
    if _has_valid_config():
        # Valid config - offer interactive start
        _run_interactive_start(ctx)
    else:
        # Config exists but incomplete
        console.print()
        console.print("[yellow]Configuration incomplete.[/yellow]")
        console.print("[dim]Run 'complexionist config setup' to complete configuration.[/dim]")
        console.print()
        _show_help_hints()


def _save_example_ini(path: Path) -> None:
    """Save an example INI configuration file.

    Args:
        path: Path to save the example file.
    """
    example_content = """\
; ComPlexionist Configuration Example
; Copy this file to complexionist.ini and fill in your values.
;
; Config file search order:
;   1. Same directory as the executable
;   2. Current working directory
;   3. ~/.complexionist/

[plex]
; Your Plex server URL
url = http://your-plex-server:32400

; Your Plex authentication token
; Find it: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
token = your-plex-token

[tmdb]
; TMDB API key for movie collection data
; Get one free: https://www.themoviedb.org/settings/api
api_key = your-tmdb-api-key

[tvdb]
; TVDB API key for TV episode data
; Get one: https://thetvdb.com/api-information
api_key = your-tvdb-api-key

[options]
; Exclude movies not yet released (default: true)
exclude_future = true

; Exclude Season 0 specials (default: true)
exclude_specials = true

; Skip episodes aired within this many hours (default: 24)
recent_threshold_hours = 24

; Minimum movies in a collection to report (default: 2)
min_collection_size = 2

; Minimum owned movies to show collection gaps (default: 2)
min_owned = 2

[exclusions]
; Comma-separated list of TV shows to skip
; shows = Daily Talk Show, Another Show

; Comma-separated list of collections to skip
; collections = Anthology Collection
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(example_content)


def _check_config_exists() -> None:
    """Check if configuration exists, offer setup wizard if not.

    If no config exists and user declines setup, exits the program.
    Otherwise returns normally (config exists or was created).
    """
    from complexionist.setup import check_first_run

    if not check_first_run():
        sys.exit(0)


def _list_libraries(libraries: list, lib_type: str) -> None:
    """Display available libraries as a table.

    Args:
        libraries: List of PlexLibrary objects.
        lib_type: Type description (e.g., "movie", "TV").
    """
    console.print(f"[bold]Available {lib_type} libraries:[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("#", style="dim", justify="right")
    table.add_column("Name", style="white")
    table.add_column("Type", style="dim")

    for i, lib in enumerate(libraries, 1):
        table.add_row(str(i), lib.title, lib.type)

    console.print(table)
    console.print()
    console.print("[dim]Use --library to specify which library to scan.[/dim]")
    console.print('[dim]Example: complexionist movies --library "Movies"[/dim]')


def _select_library_interactive(libraries: list, lib_type: str) -> str | None:
    """Interactively prompt user to select a library.

    Args:
        libraries: List of PlexLibrary objects.
        lib_type: Type description (e.g., "movie", "TV").

    Returns:
        Selected library name, or None if cancelled.
    """
    console.print(f"[bold]Multiple {lib_type} libraries found. Please select one:[/bold]")
    console.print()

    for i, lib in enumerate(libraries, 1):
        console.print(f"  [cyan]{i}[/cyan]. {lib.title}")

    console.print()

    while True:
        choice = Prompt.ask(
            f"Enter number (1-{len(libraries)})",
            default="1",
        )

        try:
            idx = int(choice)
            if 1 <= idx <= len(libraries):
                return libraries[idx - 1].title
            console.print(f"[red]Please enter a number between 1 and {len(libraries)}[/red]")
        except ValueError:
            # Check if they typed a library name directly
            names = {lib.title.lower(): lib.title for lib in libraries}
            if choice.lower() in names:
                return names[choice.lower()]
            console.print("[red]Please enter a valid number or library name[/red]")


def _resolve_libraries(
    plex_client,
    requested: tuple[str, ...],
    get_libraries_fn,
    lib_type: str,
) -> list[str] | None:
    """Resolve library names from user input.

    Args:
        plex_client: PlexClient instance.
        requested: Tuple of requested library names (can be empty).
        get_libraries_fn: Function to get available libraries (e.g., plex.get_movie_libraries).
        lib_type: Type description for error messages (e.g., "movie", "TV").

    Returns:
        List of library names to scan, or None if should exit (listed libraries).
    """
    available = get_libraries_fn()

    if not available:
        console.print(f"[yellow]No {lib_type} libraries found on this Plex server.[/yellow]")
        return None

    # If no library specified, handle based on count
    if not requested:
        if len(available) == 1:
            # Only one library - use it automatically
            return [available[0].title]
        else:
            # Multiple libraries - prompt for selection
            selected = _select_library_interactive(available, lib_type)
            if selected is None:
                return None
            return [selected]

    # Validate requested libraries
    available_names = {lib.title for lib in available}
    library_names = []

    for name in requested:
        if name not in available_names:
            console.print(f"[red]Library not found:[/red] {name}")
            console.print()
            _list_libraries(available, lib_type)
            return None
        library_names.append(name)

    return library_names


@click.group(cls=BannerGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="complexionist")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-q", "--quiet", is_flag=True, help="Minimal output (no progress, only results)")
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """ComPlexionist - Find missing movies and TV episodes in your Plex library."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Handle no-args invocation (just running 'complexionist' with no command)
    if ctx.invoked_subcommand is None:
        _handle_no_args(ctx)


@main.command(cls=BannerCommand)
@click.option(
    "--library",
    "-l",
    multiple=True,
    help="Movie library name(s) to scan (can specify multiple)",
)
@click.option("--include-future", is_flag=True, help="Include unreleased movies")
@click.option(
    "--min-collection-size",
    type=int,
    default=None,
    help="Minimum collection size to report (default: from config or 2)",
)
@click.option(
    "--min-owned",
    type=int,
    default=None,
    help="Minimum owned movies to report collection gaps (default: from config or 2)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.option(
    "--no-csv",
    is_flag=True,
    help="Disable automatic CSV file output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration without running scan",
)
@click.pass_context
def movies(
    ctx: click.Context,
    library: tuple[str, ...],
    include_future: bool,
    min_collection_size: int | None,
    min_owned: int | None,
    format: str,
    no_csv: bool,
    dry_run: bool,
) -> None:
    """Find missing movies from collections in your Plex library.

    If no --library is specified, lists available movie libraries.
    """
    from complexionist.cache import Cache
    from complexionist.gaps import MovieGapFinder
    from complexionist.plex import PlexClient, PlexError
    from complexionist.statistics import ScanStatistics
    from complexionist.tmdb import TMDBClient, TMDBError

    # Check for first-run (offers setup wizard if no config)
    _check_config_exists()

    # Show splash banner
    _show_splash()

    # Handle dry-run mode
    if dry_run:
        from complexionist.validation import validate_config

        validate_config()
        return

    quiet = ctx.obj.get("quiet", False)
    cfg = get_config()

    # Use CLI option or config default
    if min_collection_size is None:
        min_collection_size = cfg.options.min_collection_size
    if min_owned is None:
        min_owned = cfg.options.min_owned

    # Create cache
    cache = Cache()

    # Progress tracking state
    progress_task = None
    progress_ctx = None

    def progress_callback(stage: str, current: int, total: int) -> None:
        nonlocal progress_task, progress_ctx
        if progress_ctx is not None and progress_task is not None:
            progress_ctx.update(progress_task, description=stage, completed=current, total=total)

    try:
        # Connect to Plex first (needed to resolve libraries)
        try:
            plex = PlexClient()
            plex.connect()
        except PlexError as e:
            console.print(f"[red]Plex error:[/red] {e}")
            sys.exit(1)

        # Resolve library names
        library_names = _resolve_libraries(plex, library, plex.get_movie_libraries, "movie")
        if library_names is None:
            # Either listed libraries or no libraries found
            return

        # Connect to TMDB
        try:
            tmdb = TMDBClient(cache=cache)
            tmdb.test_connection()
        except TMDBError as e:
            console.print(f"[red]TMDB error:[/red] {e}")
            sys.exit(1)

        # Scan each library
        for lib_name in library_names:
            if len(library_names) > 1:
                console.print(f"\n[bold blue]Scanning library: {lib_name}[/bold blue]")

            # Start statistics tracking
            stats = ScanStatistics()
            stats.start()

            if quiet:
                # Quiet mode: no progress indicators
                finder = MovieGapFinder(
                    plex_client=plex,
                    tmdb_client=tmdb,
                    include_future=include_future,
                    min_collection_size=min_collection_size,
                    min_owned=min_owned,
                    excluded_collections=cfg.exclusions.collections,
                )
                report = finder.find_gaps(lib_name)
            else:
                # Normal mode with progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                    transient=False,
                ) as progress:
                    progress_ctx = progress
                    progress_task = progress.add_task("Scanning...", total=None)

                    # Find gaps
                    finder = MovieGapFinder(
                        plex_client=plex,
                        tmdb_client=tmdb,
                        include_future=include_future,
                        min_collection_size=min_collection_size,
                        min_owned=min_owned,
                        excluded_collections=cfg.exclusions.collections,
                        progress_callback=progress_callback,
                    )

                    report = finder.find_gaps(lib_name)

            # Stop statistics tracking
            stats.stop()

            # Output results
            if format == "json":
                _output_movies_json(report)
            elif format == "csv":
                _output_movies_csv(report)
            else:
                # Save CSV first (unless --no-csv)
                csv_path = None
                if not no_csv and report.collections_with_gaps:
                    csv_path = _save_movies_csv(report)

                # Show summary with option to view details
                _show_movie_summary(report, stats, csv_path)

        # Flush any pending cache writes
        cache.flush()

    except KeyboardInterrupt:
        # Still flush cache on interrupt to preserve progress
        cache.flush()
        console.print("\n[yellow]Scan cancelled.[/yellow]")
        sys.exit(130)


def _output_movies_text(report: MovieGapReport, verbose: bool) -> None:
    """Output movie gap report as formatted text."""
    console.print()
    console.print(f"[bold blue]Movie Collection Gaps - {report.library_name}[/bold blue]")
    console.print()

    # Summary
    console.print(f"[dim]Movies scanned:[/dim] {report.total_movies_scanned}")
    console.print(f"[dim]With TMDB ID:[/dim] {report.movies_with_tmdb_id}")
    console.print(f"[dim]In collections:[/dim] {report.movies_in_collections}")
    console.print(f"[dim]Unique collections:[/dim] {report.unique_collections}")
    console.print()

    if not report.collections_with_gaps:
        console.print("[green]All collections are complete![/green]")
        return

    console.print(
        f"[yellow]Found {report.total_missing} missing movies in {len(report.collections_with_gaps)} collections[/yellow]"
    )
    console.print()

    for gap in report.collections_with_gaps:
        # Collection header
        console.print(
            f"[bold]{gap.collection_name}[/bold] ({gap.owned_movies}/{gap.total_movies} - {gap.completion_percent:.0f}%)"
        )

        # Missing movies table
        table = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
        table.add_column("Title", style="white")
        table.add_column("Year", style="dim", justify="right")

        for movie in gap.missing_movies:
            table.add_row(movie.title, str(movie.year) if movie.year else "TBA")

        console.print(table)
        console.print()


def _output_movies_json(report: MovieGapReport) -> None:
    """Output movie gap report as JSON."""
    output = {
        "library_name": report.library_name,
        "total_movies_scanned": report.total_movies_scanned,
        "movies_with_tmdb_id": report.movies_with_tmdb_id,
        "movies_in_collections": report.movies_in_collections,
        "unique_collections": report.unique_collections,
        "total_missing": report.total_missing,
        "collections": [
            {
                "id": gap.collection_id,
                "name": gap.collection_name,
                "total": gap.total_movies,
                "owned": gap.owned_movies,
                "missing": [
                    {
                        "tmdb_id": m.tmdb_id,
                        "title": m.title,
                        "year": m.year,
                        "release_date": m.release_date.isoformat() if m.release_date else None,
                    }
                    for m in gap.missing_movies
                ],
            }
            for gap in report.collections_with_gaps
        ],
    }
    console.print_json(json.dumps(output))


def _output_movies_csv(report: MovieGapReport) -> None:
    """Output movie gap report as CSV."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Collection", "Movie Title", "Year", "TMDB ID", "Release Date"])

    for gap in report.collections_with_gaps:
        for movie in gap.missing_movies:
            writer.writerow(
                [
                    gap.collection_name,
                    movie.title,
                    movie.year or "",
                    movie.tmdb_id,
                    movie.release_date.isoformat() if movie.release_date else "",
                ]
            )

    console.print(output.getvalue())


def _save_movies_csv(report: MovieGapReport) -> Path:
    """Save movie gap report as CSV file.

    Args:
        report: Movie gap report to save.

    Returns:
        Path to saved CSV file.
    """
    import csv

    # Create filename: {LibraryName}_movie_gaps_{YYYY-MM-DD}.csv
    # Sanitize library name for use in filename
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in report.library_name)
    safe_name = safe_name.replace(" ", "_")
    filename = f"{safe_name}_movie_gaps_{date.today().isoformat()}.csv"
    filepath = Path.cwd() / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Collection", "Movie Title", "Year", "TMDB ID", "Release Date"])

        for gap in report.collections_with_gaps:
            for movie in gap.missing_movies:
                writer.writerow(
                    [
                        gap.collection_name,
                        movie.title,
                        movie.year or "",
                        movie.tmdb_id,
                        movie.release_date.isoformat() if movie.release_date else "",
                    ]
                )

    return filepath


def _output_episodes_text(report: EpisodeGapReport, verbose: bool) -> None:
    """Output episode gap report as formatted text."""
    console.print()
    console.print(f"[bold blue]TV Episode Gaps - {report.library_name}[/bold blue]")
    console.print()

    # Summary
    console.print(f"[dim]Shows scanned:[/dim] {report.total_shows_scanned}")
    console.print(f"[dim]With TVDB ID:[/dim] {report.shows_with_tvdb_id}")
    console.print(f"[dim]Episodes owned:[/dim] {report.total_episodes_owned}")
    console.print()

    if not report.shows_with_gaps:
        console.print("[green]All shows are complete![/green]")
        return

    console.print(
        f"[yellow]Found {report.total_missing} missing episodes in {len(report.shows_with_gaps)} shows[/yellow]"
    )
    console.print()

    for show in report.shows_with_gaps:
        # Show header
        console.print(
            f"[bold]{show.show_title}[/bold] ({show.owned_episodes}/{show.total_episodes} - {show.completion_percent:.0f}%)"
        )

        for season in show.seasons_with_gaps:
            console.print(f"  [dim]Season {season.season_number}:[/dim]")

            # Show first few episodes, summarize if too many
            max_display = 5 if not verbose else len(season.missing_episodes)
            displayed = season.missing_episodes[:max_display]

            for ep in displayed:
                title_part = f" - {ep.title}" if ep.title else ""
                console.print(f"    {ep.episode_code}{title_part}")

            remaining = len(season.missing_episodes) - max_display
            if remaining > 0:
                console.print(f"    [dim]... and {remaining} more[/dim]")

        console.print()


def _output_episodes_json(report: EpisodeGapReport) -> None:
    """Output episode gap report as JSON."""
    output = {
        "library_name": report.library_name,
        "total_shows_scanned": report.total_shows_scanned,
        "shows_with_tvdb_id": report.shows_with_tvdb_id,
        "total_episodes_owned": report.total_episodes_owned,
        "total_missing": report.total_missing,
        "shows": [
            {
                "tvdb_id": show.tvdb_id,
                "title": show.show_title,
                "total_episodes": show.total_episodes,
                "owned_episodes": show.owned_episodes,
                "seasons": [
                    {
                        "season": season.season_number,
                        "total": season.total_episodes,
                        "owned": season.owned_episodes,
                        "missing": [
                            {
                                "tvdb_id": ep.tvdb_id,
                                "episode_code": ep.episode_code,
                                "title": ep.title,
                                "aired": ep.aired.isoformat() if ep.aired else None,
                            }
                            for ep in season.missing_episodes
                        ],
                    }
                    for season in show.seasons_with_gaps
                ],
            }
            for show in report.shows_with_gaps
        ],
    }
    console.print_json(json.dumps(output))


def _output_episodes_csv(report: EpisodeGapReport) -> None:
    """Output episode gap report as CSV."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Show", "Season", "Episode", "Title", "TVDB ID", "Aired"])

    for show in report.shows_with_gaps:
        for season in show.seasons_with_gaps:
            for ep in season.missing_episodes:
                writer.writerow(
                    [
                        show.show_title,
                        season.season_number,
                        ep.episode_code,
                        ep.title or "",
                        ep.tvdb_id,
                        ep.aired.isoformat() if ep.aired else "",
                    ]
                )

    console.print(output.getvalue())


@main.command(cls=BannerCommand)
@click.option(
    "--library",
    "-l",
    multiple=True,
    help="TV library name(s) to scan (can specify multiple)",
)
@click.option("--include-future", is_flag=True, help="Include unaired episodes")
@click.option("--include-specials", is_flag=True, help="Include Season 0 (specials)")
@click.option(
    "--recent-threshold",
    type=int,
    default=None,
    help="Skip episodes aired within this many hours (default: from config or 24)",
)
@click.option(
    "--exclude-show",
    multiple=True,
    help="Show title to exclude (can be used multiple times)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.option(
    "--no-csv",
    is_flag=True,
    help="Disable automatic CSV file output",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Validate configuration without running scan",
)
@click.pass_context
def tv(
    ctx: click.Context,
    library: tuple[str, ...],
    include_future: bool,
    include_specials: bool,
    recent_threshold: int | None,
    exclude_show: tuple[str, ...],
    format: str,
    no_csv: bool,
    dry_run: bool,
) -> None:
    """Find missing episodes from TV shows in your Plex library.

    If no --library is specified, lists available TV libraries.
    """
    from complexionist.cache import Cache
    from complexionist.gaps import EpisodeGapFinder
    from complexionist.plex import PlexClient, PlexError
    from complexionist.statistics import ScanStatistics
    from complexionist.tvdb import TVDBClient, TVDBError

    # Check for first-run (offers setup wizard if no config)
    _check_config_exists()

    # Show splash banner
    _show_splash()

    # Handle dry-run mode
    if dry_run:
        from complexionist.validation import validate_config

        validate_config()
        return

    quiet = ctx.obj.get("quiet", False)
    cfg = get_config()

    # Use CLI option or config default
    if recent_threshold is None:
        recent_threshold = cfg.options.recent_threshold_hours

    # Combine CLI exclusions with config exclusions
    excluded_shows = list(exclude_show) + cfg.exclusions.shows

    # Create cache
    cache = Cache()

    # Progress tracking state
    progress_task = None
    progress_ctx = None

    def progress_callback(stage: str, current: int, total: int) -> None:
        nonlocal progress_task, progress_ctx
        if progress_ctx is not None and progress_task is not None:
            progress_ctx.update(progress_task, description=stage, completed=current, total=total)

    try:
        # Connect to Plex first (needed to resolve libraries)
        try:
            plex = PlexClient()
            plex.connect()
        except PlexError as e:
            console.print(f"[red]Plex error:[/red] {e}")
            sys.exit(1)

        # Resolve library names
        library_names = _resolve_libraries(plex, library, plex.get_tv_libraries, "TV")
        if library_names is None:
            # Either listed libraries or no libraries found
            return

        # Connect to TVDB
        try:
            tvdb = TVDBClient(cache=cache)
            tvdb.test_connection()
        except TVDBError as e:
            console.print(f"[red]TVDB error:[/red] {e}")
            sys.exit(1)

        # Scan each library
        for lib_name in library_names:
            if len(library_names) > 1:
                console.print(f"\n[bold blue]Scanning library: {lib_name}[/bold blue]")

            # Start statistics tracking
            stats = ScanStatistics()
            stats.start()

            if quiet:
                # Quiet mode: no progress indicators
                finder = EpisodeGapFinder(
                    plex_client=plex,
                    tvdb_client=tvdb,
                    include_future=include_future,
                    include_specials=include_specials,
                    recent_threshold_hours=recent_threshold,
                    excluded_shows=excluded_shows,
                )
                report = finder.find_gaps(lib_name)
            else:
                # Normal mode with progress
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                    transient=False,
                ) as progress:
                    progress_ctx = progress
                    progress_task = progress.add_task("Scanning...", total=None)

                    # Find gaps
                    finder = EpisodeGapFinder(
                        plex_client=plex,
                        tvdb_client=tvdb,
                        include_future=include_future,
                        include_specials=include_specials,
                        recent_threshold_hours=recent_threshold,
                        excluded_shows=excluded_shows,
                        progress_callback=progress_callback,
                    )

                    report = finder.find_gaps(lib_name)

            # Stop statistics tracking
            stats.stop()

            # Output results
            if format == "json":
                _output_episodes_json(report)
            elif format == "csv":
                _output_episodes_csv(report)
            else:
                # Save CSV first (unless --no-csv)
                csv_path = None
                if not no_csv and report.shows_with_gaps:
                    csv_path = _save_tv_csv(report)

                # Show summary with option to view details
                _show_tv_summary(report, stats, csv_path)

        # Flush any pending cache writes
        cache.flush()

    except KeyboardInterrupt:
        # Still flush cache on interrupt to preserve progress
        cache.flush()
        console.print("\n[yellow]Scan cancelled.[/yellow]")
        sys.exit(130)


def _save_tv_csv(report: EpisodeGapReport) -> Path:
    """Save episode gap report as CSV file.

    Args:
        report: Episode gap report to save.

    Returns:
        Path to saved CSV file.
    """
    import csv

    # Create filename: {LibraryName}_tv_gaps_{YYYY-MM-DD}.csv
    safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in report.library_name)
    safe_name = safe_name.replace(" ", "_")
    filename = f"{safe_name}_tv_gaps_{date.today().isoformat()}.csv"
    filepath = Path.cwd() / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Show", "Season", "Episode", "Title", "TVDB ID", "Aired"])

        for show in report.shows_with_gaps:
            for season in show.seasons_with_gaps:
                for ep in season.missing_episodes:
                    writer.writerow(
                        [
                            show.show_title,
                            season.season_number,
                            ep.episode_code,
                            ep.title or "",
                            ep.tvdb_id,
                            ep.aired.isoformat() if ep.aired else "",
                        ]
                    )

    return filepath


@main.command(cls=BannerCommand)
@click.option(
    "--library",
    "-l",
    multiple=True,
    help="Library name(s) to scan (can specify multiple)",
)
@click.option("--include-future", is_flag=True, help="Include unreleased content")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.pass_context
def scan(
    ctx: click.Context,
    library: tuple[str, ...],
    include_future: bool,
    format: str,
) -> None:
    """Scan both movie and TV libraries for missing content.

    If no --library is specified, lists available libraries for each type.
    """
    # Check for first-run (offers setup wizard if no config)
    _check_config_exists()

    console.print("[bold blue]ComPlexionist Scan[/bold blue]")
    console.print()

    # Invoke movies command
    console.print("[bold]Movie Collections[/bold]")
    ctx.invoke(
        movies,
        library=library,
        include_future=include_future,
        format=format,
    )
    console.print()

    # Invoke tv command
    console.print("[bold]TV Shows[/bold]")
    ctx.invoke(
        tv,
        library=library,
        include_future=include_future,
        include_specials=False,
        format=format,
    )


@main.group()
def config() -> None:
    """Manage ComPlexionist configuration."""
    pass


@config.command(name="show")
def config_show() -> None:
    """Show current configuration."""
    from complexionist.config import find_config_file, get_config

    cfg = get_config()
    config_file = find_config_file()

    console.print("[bold]Current Configuration[/bold]")
    console.print()

    if config_file:
        console.print(f"[dim]Config file:[/dim] {config_file}")
    else:
        console.print("[dim]Config file:[/dim] (none - using defaults)")
    console.print()

    # Plex
    console.print("[bold]Plex:[/bold]")
    url = cfg.plex.url or "[red](not set)[/red]"
    token = "(set)" if cfg.plex.token else "[red](not set)[/red]"
    console.print(f"  URL: {url}")
    console.print(f"  Token: {token}")
    console.print()

    # Options
    console.print("[bold]Options:[/bold]")
    console.print(f"  Exclude future: {cfg.options.exclude_future}")
    console.print(f"  Exclude specials: {cfg.options.exclude_specials}")
    console.print(f"  Recent threshold: {cfg.options.recent_threshold_hours} hours")
    console.print(f"  Min collection size: {cfg.options.min_collection_size}")
    console.print(f"  Min owned: {cfg.options.min_owned}")
    console.print()

    # Exclusions
    console.print("[bold]Exclusions:[/bold]")
    if cfg.exclusions.shows:
        console.print(f"  Shows: {', '.join(cfg.exclusions.shows)}")
    else:
        console.print("  Shows: (none)")
    if cfg.exclusions.collections:
        console.print(f"  Collections: {', '.join(cfg.exclusions.collections)}")
    else:
        console.print("  Collections: (none)")


@config.command(name="path")
def config_path() -> None:
    """Show configuration file paths."""
    from pathlib import Path

    from complexionist.config import find_config_file, get_config_paths

    console.print("[bold]Configuration paths (in priority order):[/bold]")
    config_file = find_config_file()

    for path in get_config_paths():
        if path.exists():
            if path == config_file:
                console.print(f"  [green]{path}[/green] (active)")
            else:
                console.print(f"  {path} (exists)")
        else:
            console.print(f"  [dim]{path}[/dim]")

    console.print()
    console.print("[bold]Other paths:[/bold]")
    home = Path.home()
    config_dir = home / ".complexionist"
    console.print(f"  Cache dir: {config_dir / 'cache'}")
    console.print(f"  .env file: {Path.cwd() / '.env'}")


@config.command(name="init")
@click.option("--force", is_flag=True, help="Overwrite existing config file")
def config_init(force: bool) -> None:
    """Create a default configuration file (INI format)."""
    from pathlib import Path

    from complexionist.config import save_default_config

    # Save in current directory for portability
    config_path = Path.cwd() / "complexionist.ini"

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/yellow] {config_path}")
        console.print("Use --force to overwrite.")
        sys.exit(1)

    save_default_config(config_path)
    console.print(f"[green]Created config file:[/green] {config_path}")
    console.print("Edit this file to add your API keys and customize settings.")


@config.command(name="validate")
def config_validate() -> None:
    """Validate configuration by testing service connections."""
    from complexionist.validation import validate_config

    success = validate_config()
    sys.exit(0 if success else 1)


@config.command(name="setup")
def config_setup() -> None:
    """Run the interactive setup wizard."""
    from complexionist.setup import run_setup_wizard

    result = run_setup_wizard()
    sys.exit(0 if result else 1)


@main.group()
def cache() -> None:
    """Manage the API response cache."""
    pass


@cache.command(name="clear")
@click.confirmation_option(prompt="Are you sure you want to clear the cache?")
def cache_clear() -> None:
    """Clear all cached API responses."""
    from complexionist.cache import Cache

    cache = Cache()
    count = cache.clear()

    if count == 0:
        console.print("[dim]Cache is already empty.[/dim]")
    else:
        console.print(f"[green]Cleared {count} cached entries.[/green]")


@cache.command(name="stats")
def cache_stats() -> None:
    """Show cache statistics."""
    from complexionist.cache import Cache

    cache = Cache()
    stats = cache.stats()

    console.print("[bold]Cache Statistics[/bold]")
    console.print()

    if stats.total_entries == 0:
        console.print("[dim]Cache is empty.[/dim]")
        console.print()
        console.print(f"Cache location: {cache.cache_dir}")
        return

    console.print(f"[bold]Total entries:[/bold] {stats.total_entries}")
    console.print(f"[bold]Total size:[/bold] {stats.total_size_kb:.1f} KB")
    console.print()

    console.print("[bold]By category:[/bold]")
    console.print(f"  TMDB movies:      {stats.tmdb_movies}")
    console.print(f"  TMDB collections: {stats.tmdb_collections}")
    console.print(f"  TVDB episodes:    {stats.tvdb_episodes}")
    console.print()

    if stats.oldest_entry:
        console.print(f"[bold]Oldest entry:[/bold] {stats.oldest_entry.strftime('%Y-%m-%d %H:%M')}")
    if stats.newest_entry:
        console.print(f"[bold]Newest entry:[/bold] {stats.newest_entry.strftime('%Y-%m-%d %H:%M')}")
    console.print()

    # Check for expired entries
    expired = cache.get_expired_count()
    if expired > 0:
        console.print(f"[yellow]Expired entries:[/yellow] {expired}")
        console.print("[dim]Run 'cache clear' to remove expired entries.[/dim]")

    console.print()
    console.print(f"Cache location: {cache.cache_dir}")


@cache.command(name="refresh")
@click.confirmation_option(prompt="This will clear all cached data and fingerprints. Continue?")
def cache_refresh() -> None:
    """Force refresh - clear all cache and library fingerprints.

    Use this when you want to ensure fresh data is fetched on the next scan.
    """
    from complexionist.cache import Cache

    cache = Cache()
    count = cache.refresh()

    if count == 0:
        console.print("[dim]Cache was already empty.[/dim]")
    else:
        console.print(f"[green]Refreshed cache - cleared {count} entries.[/green]")
    console.print("[dim]Library fingerprints have been reset.[/dim]")


if __name__ == "__main__":
    main()
