"""Application state management for ComPlexionist GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from complexionist.statistics import ScanStatistics


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
class ConnectionStatus:
    """Connection status for services."""

    plex_connected: bool = False
    plex_server_name: str = ""
    tmdb_connected: bool = False
    tvdb_connected: bool = False
    error_message: str = ""
    is_checking: bool = True  # True while testing connections at startup


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
    scan_stats: ScanStatistics | None = None
    scanning_screen: Any | None = None  # Reference to ScanningScreen for progress updates

    # Results
    movie_report: Any | None = None  # MovieGapReport
    tv_report: Any | None = None  # TVGapReport

    # Ignored item names cache (for settings display)
    ignored_collection_names: dict[int, str] = field(default_factory=dict)
    ignored_show_names: dict[int, str] = field(default_factory=dict)

    def reset_scan(self) -> None:
        """Reset scan-related state."""
        self.scan_progress = ScanProgress()
        self.scan_stats = None
        self.movie_report = None
        self.tv_report = None
