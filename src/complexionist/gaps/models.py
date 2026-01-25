"""Data models for gap detection results."""

from datetime import date

from pydantic import BaseModel, Field


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


class CollectionGap(BaseModel):
    """A collection with missing movies."""

    collection_id: int
    collection_name: str
    total_movies: int
    owned_movies: int
    missing_movies: list[MissingMovie] = Field(default_factory=list)

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
