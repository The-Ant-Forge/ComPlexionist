"""Data models for TVDB API responses."""

from datetime import date

from pydantic import BaseModel, Field


class TVDBEpisode(BaseModel):
    """An episode from TVDB."""

    id: int
    series_id: int = Field(alias="seriesId")
    name: str | None = None
    season_number: int = Field(alias="seasonNumber")
    episode_number: int = Field(alias="number")
    aired: date | None = None
    overview: str | None = None
    runtime: int | None = None

    model_config = {"populate_by_name": True}

    @property
    def episode_code(self) -> str:
        """Get the episode code (e.g., 'S01E05')."""
        return f"S{self.season_number:02d}E{self.episode_number:02d}"

    @property
    def is_aired(self) -> bool:
        """Check if the episode has aired."""
        if self.aired is None:
            return False
        return self.aired <= date.today()

    @property
    def is_special(self) -> bool:
        """Check if this is a special (Season 0)."""
        return self.season_number == 0


class TVDBSeries(BaseModel):
    """A TV series from TVDB."""

    id: int
    name: str | None = None  # TVDB sometimes returns None for bad data
    slug: str | None = None
    status: str | None = None  # e.g., "Continuing", "Ended"
    first_aired: date | None = Field(default=None, alias="firstAired")
    overview: str | None = None
    year: int | None = None
    image: str | None = None  # Full URL to poster image

    model_config = {"populate_by_name": True}

    @property
    def url(self) -> str:
        """Get the TVDB series page URL."""
        if self.slug:
            return f"https://www.thetvdb.com/series/{self.slug}"
        return f"https://www.thetvdb.com/dereferrer/series/{self.id}"


class TVDBSeriesExtended(TVDBSeries):
    """Extended series info with episodes."""

    episodes: list[TVDBEpisode] = Field(default_factory=list)

    @property
    def aired_episodes(self) -> list[TVDBEpisode]:
        """Get only aired episodes."""
        return [ep for ep in self.episodes if ep.is_aired]

    @property
    def regular_episodes(self) -> list[TVDBEpisode]:
        """Get non-special episodes (excluding Season 0)."""
        return [ep for ep in self.episodes if not ep.is_special]

    @property
    def aired_regular_episodes(self) -> list[TVDBEpisode]:
        """Get aired non-special episodes."""
        return [ep for ep in self.episodes if ep.is_aired and not ep.is_special]

    def episodes_by_season(self) -> dict[int, list[TVDBEpisode]]:
        """Get episodes grouped by season number."""
        result: dict[int, list[TVDBEpisode]] = {}
        for ep in self.episodes:
            if ep.season_number not in result:
                result[ep.season_number] = []
            result[ep.season_number].append(ep)
        return result
