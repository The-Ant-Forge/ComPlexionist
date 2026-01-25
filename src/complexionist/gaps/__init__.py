"""Gap detection logic for movies and TV episodes."""

from complexionist.gaps.episodes import EpisodeGapFinder, parse_multi_episode_filename
from complexionist.gaps.models import (
    CollectionGap,
    EpisodeGapReport,
    MissingEpisode,
    MissingMovie,
    MovieGapReport,
    SeasonGap,
    ShowGap,
)
from complexionist.gaps.movies import MovieGapFinder

__all__ = [
    # Movie gap detection
    "MovieGapFinder",
    "MovieGapReport",
    "CollectionGap",
    "MissingMovie",
    # Episode gap detection
    "EpisodeGapFinder",
    "EpisodeGapReport",
    "ShowGap",
    "SeasonGap",
    "MissingEpisode",
    "parse_multi_episode_filename",
]
