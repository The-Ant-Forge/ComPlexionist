"""Application state management for ComPlexionist GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Screen(Enum):
    """Application screens."""

    ONBOARDING = auto()
    DASHBOARD = auto()
    SCANNING = auto()
    RESULTS = auto()
    SETTINGS = auto()


class ScanType(Enum):
    """Type of scan to perform."""

    MOVIES = auto()
    TV = auto()
    BOTH = auto()


@dataclass
class ScanProgress:
    """Progress state for scanning operations."""

    phase: str = ""
    current: int = 0
    total: int = 0
    is_running: bool = False
    is_cancelled: bool = False

    @property
    def percent(self) -> float:
        """Get progress as percentage (0-100)."""
        if self.total == 0:
            return 0
        return (self.current / self.total) * 100


@dataclass
class ScanStats:
    """Statistics from a completed scan."""

    duration_seconds: float = 0.0
    api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    plex_calls: int = 0
    tmdb_calls: int = 0
    tvdb_calls: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate as percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100

    @property
    def duration_str(self) -> str:
        """Get formatted duration string."""
        if self.duration_seconds < 60:
            return f"{self.duration_seconds:.1f}s"
        minutes = int(self.duration_seconds // 60)
        seconds = self.duration_seconds % 60
        return f"{minutes}m {seconds:.0f}s"


@dataclass
class ConnectionStatus:
    """Connection status for services."""

    plex_connected: bool = False
    plex_server_name: str = ""
    tmdb_connected: bool = False
    tvdb_connected: bool = False
    error_message: str = ""


@dataclass
class AppState:
    """Global application state."""

    # Navigation
    current_screen: Screen = Screen.DASHBOARD
    dark_mode: bool = True

    # Config state
    has_valid_config: bool = False
    config_path: str = ""

    # Connection state
    connection: ConnectionStatus = field(default_factory=ConnectionStatus)

    # Library selection
    movie_libraries: list[str] = field(default_factory=list)
    tv_libraries: list[str] = field(default_factory=list)
    selected_movie_library: str = ""
    selected_tv_library: str = ""

    # Scan state
    scan_type: ScanType = ScanType.MOVIES
    scan_progress: ScanProgress = field(default_factory=ScanProgress)
    scan_stats: ScanStats | None = None
    scanning_screen: Any | None = None  # Reference to ScanningScreen for progress updates

    # Results
    movie_report: Any | None = None  # MovieGapReport
    tv_report: Any | None = None  # TVGapReport

    def reset_scan(self) -> None:
        """Reset scan-related state."""
        self.scan_progress = ScanProgress()
        self.scan_stats = None
        self.movie_report = None
        self.tv_report = None
