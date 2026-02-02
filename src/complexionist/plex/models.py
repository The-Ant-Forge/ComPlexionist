"""Data models for Plex content."""

from pydantic import BaseModel, Field


class PlexLibrary(BaseModel):
    """A Plex library section."""

    key: str
    title: str
    type: str  # "movie", "show", "artist", "photo"
    locations: list[str] = []  # Folder paths configured for this library

    @property
    def is_movie_library(self) -> bool:
        """Check if this is a movie library."""
        return self.type == "movie"

    @property
    def is_tv_library(self) -> bool:
        """Check if this is a TV show library."""
        return self.type == "show"


class PlexMovie(BaseModel):
    """A movie from Plex."""

    rating_key: str
    title: str
    year: int | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None
    guid: str = ""  # Plex's internal GUID
    file_path: str | None = None

    @property
    def has_tmdb_id(self) -> bool:
        """Check if this movie has a TMDB ID."""
        return self.tmdb_id is not None


class PlexShow(BaseModel):
    """A TV show from Plex."""

    rating_key: str
    title: str
    year: int | None = None
    tvdb_id: int | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None
    guid: str = ""  # Plex's internal GUID

    @property
    def has_tvdb_id(self) -> bool:
        """Check if this show has a TVDB ID."""
        return self.tvdb_id is not None


class PlexEpisode(BaseModel):
    """An episode from Plex."""

    rating_key: str
    title: str
    season_number: int
    episode_number: int
    show_title: str = ""
    file_path: str | None = None

    @property
    def episode_code(self) -> str:
        """Get the episode code (e.g., 'S01E05')."""
        return f"S{self.season_number:02d}E{self.episode_number:02d}"


class PlexSeason(BaseModel):
    """A season from Plex."""

    rating_key: str
    title: str
    season_number: int
    episode_count: int = 0


class PlexShowWithEpisodes(BaseModel):
    """A TV show with all its episodes."""

    show: PlexShow
    episodes: list[PlexEpisode] = Field(default_factory=list)

    @property
    def seasons(self) -> dict[int, list[PlexEpisode]]:
        """Get episodes grouped by season number."""
        result: dict[int, list[PlexEpisode]] = {}
        for ep in self.episodes:
            if ep.season_number not in result:
                result[ep.season_number] = []
            result[ep.season_number].append(ep)
        return result

    @property
    def episode_numbers_by_season(self) -> dict[int, set[int]]:
        """Get set of episode numbers for each season."""
        result: dict[int, set[int]] = {}
        for ep in self.episodes:
            if ep.season_number not in result:
                result[ep.season_number] = set()
            result[ep.season_number].add(ep.episode_number)
        return result
