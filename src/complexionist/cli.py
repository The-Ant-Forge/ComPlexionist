"""Command-line interface for ComPlexionist."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from complexionist import __version__
from complexionist.config import get_config

if TYPE_CHECKING:
    from complexionist.gaps import EpisodeGapReport, MovieGapReport

# Load environment variables from .env file
load_dotenv()

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="complexionist")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-q", "--quiet", is_flag=True, help="Minimal output (no progress, only results)")
@click.pass_context
def main(ctx: click.Context, verbose: bool, quiet: bool) -> None:
    """ComPlexionist - Find missing movies and TV episodes in your Plex library."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet


@main.command()
@click.option("--library", "-l", default=None, help="Movie library name (default: auto-detect)")
@click.option("--no-cache", is_flag=True, help="Bypass cache and fetch fresh data")
@click.option("--include-future", is_flag=True, help="Include unreleased movies")
@click.option(
    "--min-collection-size",
    type=int,
    default=None,
    help="Minimum collection size to report (default: from config or 2)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    help="Output format",
)
@click.pass_context
def movies(
    ctx: click.Context,
    library: str | None,
    no_cache: bool,
    include_future: bool,
    min_collection_size: int | None,
    format: str,
) -> None:
    """Find missing movies from collections in your Plex library."""
    from complexionist.cache import Cache
    from complexionist.gaps import MovieGapFinder
    from complexionist.plex import PlexClient, PlexError
    from complexionist.tmdb import TMDBClient, TMDBError

    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    cfg = get_config()

    # Use CLI option or config default
    if min_collection_size is None:
        min_collection_size = cfg.options.min_collection_size

    # Create cache (disabled if --no-cache)
    cache = Cache(enabled=not no_cache)

    # Progress tracking state
    progress_task = None
    progress_ctx = None

    def progress_callback(stage: str, current: int, total: int) -> None:
        nonlocal progress_task, progress_ctx
        if progress_ctx is not None and progress_task is not None:
            progress_ctx.update(progress_task, description=stage, completed=current, total=total)

    try:
        if quiet:
            # Quiet mode: no progress indicators
            try:
                plex = PlexClient()
                plex.connect()
            except PlexError as e:
                console.print(f"[red]Plex error:[/red] {e}")
                sys.exit(1)

            try:
                tmdb = TMDBClient(cache=cache)
                tmdb.test_connection()
            except TMDBError as e:
                console.print(f"[red]TMDB error:[/red] {e}")
                sys.exit(1)

            finder = MovieGapFinder(
                plex_client=plex,
                tmdb_client=tmdb,
                include_future=include_future,
                min_collection_size=min_collection_size,
                excluded_collections=cfg.exclusions.collections,
            )
            report = finder.find_gaps(library)
        else:
            # Normal mode with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            ) as progress:
                progress_ctx = progress
                progress_task = progress.add_task("Connecting to Plex...", total=None)

                try:
                    plex = PlexClient()
                    plex.connect()
                except PlexError as e:
                    console.print(f"[red]Plex error:[/red] {e}")
                    sys.exit(1)

                progress.update(progress_task, description=f"Connected to {plex.server_name}")

                # Connect to TMDB
                progress.update(progress_task, description="Connecting to TMDB...")
                try:
                    tmdb = TMDBClient(cache=cache)
                    tmdb.test_connection()
                except TMDBError as e:
                    console.print(f"[red]TMDB error:[/red] {e}")
                    sys.exit(1)

                # Find gaps
                finder = MovieGapFinder(
                    plex_client=plex,
                    tmdb_client=tmdb,
                    include_future=include_future,
                    min_collection_size=min_collection_size,
                    excluded_collections=cfg.exclusions.collections,
                    progress_callback=progress_callback,
                )

                progress.update(progress_task, description="Scanning...", total=1, completed=0)
                report = finder.find_gaps(library)

        # Output results
        if format == "json":
            _output_movies_json(report)
        elif format == "csv":
            _output_movies_csv(report)
        else:
            _output_movies_text(report, verbose)

    except KeyboardInterrupt:
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


@main.command()
@click.option("--library", "-l", default=None, help="TV library name (default: auto-detect)")
@click.option("--no-cache", is_flag=True, help="Bypass cache and fetch fresh data")
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
@click.pass_context
def episodes(
    ctx: click.Context,
    library: str | None,
    no_cache: bool,
    include_future: bool,
    include_specials: bool,
    recent_threshold: int | None,
    exclude_show: tuple[str, ...],
    format: str,
) -> None:
    """Find missing episodes from TV shows in your Plex library."""
    from complexionist.cache import Cache
    from complexionist.gaps import EpisodeGapFinder
    from complexionist.plex import PlexClient, PlexError
    from complexionist.tvdb import TVDBClient, TVDBError

    verbose = ctx.obj.get("verbose", False)
    quiet = ctx.obj.get("quiet", False)
    cfg = get_config()

    # Use CLI option or config default
    if recent_threshold is None:
        recent_threshold = cfg.options.recent_threshold_hours

    # Combine CLI exclusions with config exclusions
    excluded_shows = list(exclude_show) + cfg.exclusions.shows

    # Create cache (disabled if --no-cache)
    cache = Cache(enabled=not no_cache)

    # Progress tracking state
    progress_task = None
    progress_ctx = None

    def progress_callback(stage: str, current: int, total: int) -> None:
        nonlocal progress_task, progress_ctx
        if progress_ctx is not None and progress_task is not None:
            progress_ctx.update(progress_task, description=stage, completed=current, total=total)

    try:
        if quiet:
            # Quiet mode: no progress indicators
            try:
                plex = PlexClient()
                plex.connect()
            except PlexError as e:
                console.print(f"[red]Plex error:[/red] {e}")
                sys.exit(1)

            try:
                tvdb = TVDBClient(cache=cache)
                tvdb.test_connection()
            except TVDBError as e:
                console.print(f"[red]TVDB error:[/red] {e}")
                sys.exit(1)

            finder = EpisodeGapFinder(
                plex_client=plex,
                tvdb_client=tvdb,
                include_future=include_future,
                include_specials=include_specials,
                recent_threshold_hours=recent_threshold,
                excluded_shows=excluded_shows,
            )
            report = finder.find_gaps(library)
        else:
            # Normal mode with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            ) as progress:
                progress_ctx = progress
                progress_task = progress.add_task("Connecting to Plex...", total=None)

                try:
                    plex = PlexClient()
                    plex.connect()
                except PlexError as e:
                    console.print(f"[red]Plex error:[/red] {e}")
                    sys.exit(1)

                progress.update(progress_task, description=f"Connected to {plex.server_name}")

                # Connect to TVDB
                progress.update(progress_task, description="Connecting to TVDB...")
                try:
                    tvdb = TVDBClient(cache=cache)
                    tvdb.test_connection()
                except TVDBError as e:
                    console.print(f"[red]TVDB error:[/red] {e}")
                    sys.exit(1)

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

                progress.update(progress_task, description="Scanning...", total=1, completed=0)
                report = finder.find_gaps(library)

        # Output results
        if format == "json":
            _output_episodes_json(report)
        elif format == "csv":
            _output_episodes_csv(report)
        else:
            _output_episodes_text(report, verbose)

    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled.[/yellow]")
        sys.exit(130)


@main.command()
@click.option("--no-cache", is_flag=True, help="Bypass cache and fetch fresh data")
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
    no_cache: bool,
    include_future: bool,
    format: str,
) -> None:
    """Scan both movie and TV libraries for missing content."""
    console.print("[bold blue]ComPlexionist Scan[/bold blue]")
    console.print()

    # Invoke movies command
    console.print("[bold]Movie Collections[/bold]")
    ctx.invoke(movies, no_cache=no_cache, include_future=include_future, format=format)
    console.print()

    # Invoke episodes command
    console.print("[bold]TV Episodes[/bold]")
    ctx.invoke(
        episodes,
        no_cache=no_cache,
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
    url = cfg.plex.url or "(from PLEX_URL env)"
    token = "(set)" if cfg.plex.token else "(from PLEX_TOKEN env)"
    console.print(f"  URL: {url}")
    console.print(f"  Token: {token}")
    console.print()

    # Options
    console.print("[bold]Options:[/bold]")
    console.print(f"  Exclude future: {cfg.options.exclude_future}")
    console.print(f"  Exclude specials: {cfg.options.exclude_specials}")
    console.print(f"  Recent threshold: {cfg.options.recent_threshold_hours} hours")
    console.print(f"  Min collection size: {cfg.options.min_collection_size}")
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
    """Create a default configuration file."""
    from complexionist.config import get_config_dir, save_default_config

    config_path = get_config_dir() / "config.yaml"

    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/yellow] {config_path}")
        console.print("Use --force to overwrite.")
        sys.exit(1)

    save_default_config(config_path)
    console.print(f"[green]Created config file:[/green] {config_path}")
    console.print("Edit this file to customize your settings.")


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


if __name__ == "__main__":
    main()
