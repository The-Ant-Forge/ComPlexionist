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
    runtime: int | None = None

    model_config = {"populate_by_name": True}

    @property
    def episode_code(self) -> str:
        """Get the episode code (e.g., 'S01E05')."""
        return f"S{self.season_number:02d}E{self.episode_number:02d}"

    @property
    def is_aired(self) -> bool:
        """Check if the episode has aired."""
        from complexionist.utils import is_date_past

        return is_date_past(self.aired)

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
    year: int | None = None
    image: str | None = None  # Full URL to poster image

    model_config = {"populate_by_name": True}

    @property
    def url(self) -> str:
        """Get the TVDB series page URL."""
        if self.slug:
            return f"https://www.thetvdb.com/series/{self.slug}"
        return f"https://www.thetvdb.com/dereferrer/series/{self.id}"
