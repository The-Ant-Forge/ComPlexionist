"""Mixin classes for Pydantic models.

Provides reusable properties for common model patterns.
"""

from __future__ import annotations

from datetime import date


class EpisodeCodeMixin:
    """Mixin providing episode_code property.

    Requires the model to have season_number and episode_number fields.

    Example:
        ```python
        class Episode(EpisodeCodeMixin, BaseModel):
            season_number: int
            episode_number: int

        ep = Episode(season_number=1, episode_number=5)
        print(ep.episode_code)  # "S01E05"
        ```
    """

    season_number: int
    episode_number: int

    @property
    def episode_code(self) -> str:
        """Get the episode code in S01E05 format."""
        return f"S{self.season_number:02d}E{self.episode_number:02d}"


class DateAwareMixin:
    """Mixin for models with date fields that need release/air checks.

    Provides helper methods to check if content is available based on a date field.

    Example:
        ```python
        class Movie(DateAwareMixin, BaseModel):
            release_date: date | None = None

        movie = Movie(release_date=date(2024, 1, 1))
        if movie.is_date_past(movie.release_date):
            print("Released!")
        ```
    """

    @staticmethod
    def is_date_past(d: date | None) -> bool:
        """Check if a date is in the past (before today).

        Uses yesterday as the cutoff to account for timezone differences —
        content released/aired "today" may not be available in all regions.

        Args:
            d: Date to check, or None.

        Returns:
            True if the date is before today, False if today or later or None.
        """
        if d is None:
            return False
        return d < date.today()

    @staticmethod
    def is_date_future(d: date | None) -> bool:
        """Check if a date is today or in the future.

        Uses today as the boundary (inclusive) to account for timezone
        differences — content released "today" is still treated as upcoming.

        Args:
            d: Date to check, or None.

        Returns:
            True if the date is today or later, False if before today or None.
        """
        if d is None:
            return False
        return d >= date.today()
