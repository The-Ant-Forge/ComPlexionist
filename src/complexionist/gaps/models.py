"""Data models for gap detection results."""

from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field


class OwnedMovie(BaseModel):
    """A movie that the user owns (part of a collection)."""

    tmdb_id: int
    title: str
    year: int | None = None
    file_path: str | None = None

    @property
    def display_title(self) -> str:
        """Get the title with year for display."""
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    @property
    def tmdb_url(self) -> str:
        """Get the TMDB movie page URL."""
        return f"https://www.themoviedb.org/movie/{self.tmdb_id}"


class MissingMovie(BaseModel):
    """A movie that's missing from the user's library."""

    tmdb_id: int
    title: str
    release_date: date | None = None
    year: int | None = None
    overview: str = ""

    @property
    def display_title(self) -> str:
        """Get the title with year for display."""
        if self.year:
            return f"{self.title} ({self.year})"
        return self.title

    @property
    def tmdb_url(self) -> str:
        """Get the TMDB movie page URL."""
        return f"https://www.themoviedb.org/movie/{self.tmdb_id}"


class CollectionGap(BaseModel):
    """A collection with missing movies."""

    collection_id: int
    collection_name: str
    total_movies: int
    owned_movies: int
    poster_path: str | None = None
    owned_movie_list: list[OwnedMovie] = Field(default_factory=list)
    missing_movies: list[MissingMovie] = Field(default_factory=list)

    @property
    def tmdb_url(self) -> str:
        """Get the TMDB collection page URL."""
        return f"https://www.themoviedb.org/collection/{self.collection_id}"

    @property
    def poster_url(self) -> str | None:
        """Get the full poster image URL (w185 size for thumbnails)."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w185{self.poster_path}"
        return None

    @property
    def missing_count(self) -> int:
        """Number of missing movies."""
        return len(self.missing_movies)

    @property
    def completion_percent(self) -> float:
        """Percentage of collection owned."""
        if self.total_movies == 0:
            return 100.0
        return (self.owned_movies / self.total_movies) * 100

    @property
    def folder_path(self) -> str | None:
        """Get the folder path of the first owned movie."""
        for movie in self.owned_movie_list:
            if movie.file_path:
                return str(Path(movie.file_path).parent)
        return None


class MovieGapReport(BaseModel):
    """Full report of movie collection gaps."""

    library_name: str
    total_movies_scanned: int
    movies_with_tmdb_id: int
    movies_in_collections: int
    unique_collections: int
    collections_with_gaps: list[CollectionGap] = Field(default_factory=list)

    @property
    def total_missing(self) -> int:
        """Total number of missing movies across all collections."""
        return sum(gap.missing_count for gap in self.collections_with_gaps)

    @property
    def complete_collections(self) -> int:
        """Number of collections that are complete."""
        return self.unique_collections - len(self.collections_with_gaps)


# ============================================================================
# Episode Gap Detection Models
# ============================================================================


class MissingEpisode(BaseModel):
    """An episode that's missing from the user's library."""

    tvdb_id: int
    season_number: int
    episode_number: int
    title: str | None = None
    aired: date | None = None
    overview: str = ""

    @property
    def episode_code(self) -> str:
        """Get the episode code (e.g., 'S01E05')."""
        return f"S{self.season_number:02d}E{self.episode_number:02d}"

    @property
    def display_title(self) -> str:
        """Get the episode code with title for display."""
        if self.title:
            return f"{self.episode_code} - {self.title}"
        return self.episode_code

    @property
    def aired_str(self) -> str:
        """Get the air date formatted for display."""
        if self.aired:
            return self.aired.strftime("%b %d, %Y")
        return "TBA"


class SeasonGap(BaseModel):
    """Missing episodes within a single season."""

    season_number: int
    total_episodes: int
    owned_episodes: int
    missing_episodes: list[MissingEpisode] = Field(default_factory=list)

    @property
    def missing_count(self) -> int:
        """Number of missing episodes in this season."""
        return len(self.missing_episodes)


class ShowGap(BaseModel):
    """A TV show with missing episodes."""

    tvdb_id: int
    show_title: str
    total_episodes: int
    owned_episodes: int
    poster_url: str | None = None
    first_episode_path: str | None = None
    seasons_with_gaps: list[SeasonGap] = Field(default_factory=list)

    @property
    def missing_count(self) -> int:
        """Total number of missing episodes."""
        return sum(season.missing_count for season in self.seasons_with_gaps)

    @property
    def completion_percent(self) -> float:
        """Percentage of show owned."""
        if self.total_episodes == 0:
            return 100.0
        return (self.owned_episodes / self.total_episodes) * 100

    @property
    def tvdb_url(self) -> str:
        """Get the TVDB series page URL."""
        return f"https://www.thetvdb.com/?tab=series&id={self.tvdb_id}"

    @property
    def folder_path(self) -> str | None:
        """Get the folder path of the first owned episode."""
        if self.first_episode_path:
            return str(Path(self.first_episode_path).parent)
        return None


class EpisodeGapReport(BaseModel):
    """Full report of TV episode gaps."""

    library_name: str
    total_shows_scanned: int
    shows_with_tvdb_id: int
    total_episodes_owned: int
    shows_with_gaps: list[ShowGap] = Field(default_factory=list)

    @property
    def total_missing(self) -> int:
        """Total number of missing episodes across all shows."""
        return sum(show.missing_count for show in self.shows_with_gaps)

    @property
    def complete_shows(self) -> int:
        """Number of shows with all episodes."""
        return self.shows_with_tvdb_id - len(self.shows_with_gaps)
