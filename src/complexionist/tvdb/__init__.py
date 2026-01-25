"""TVDB (TheTVDB) API integration."""

from complexionist.tvdb.client import (
    TVDBAuthError,
    TVDBClient,
    TVDBError,
    TVDBNotFoundError,
    TVDBRateLimitError,
)
from complexionist.tvdb.models import (
    TVDBEpisode,
    TVDBSeries,
    TVDBSeriesExtended,
)

__all__ = [
    "TVDBClient",
    "TVDBError",
    "TVDBAuthError",
    "TVDBNotFoundError",
    "TVDBRateLimitError",
    "TVDBEpisode",
    "TVDBSeries",
    "TVDBSeriesExtended",
]
