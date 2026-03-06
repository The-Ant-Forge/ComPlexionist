"""Tests for GUI state management and persistence modules."""

import configparser
from pathlib import Path

from complexionist.gui.state import AppState, ConnectionStatus, ScanProgress, ScanType, Screen
from complexionist.gui.window_state import WindowState, validate_window_position


class TestScanProgress:
    """Tests for ScanProgress dataclass."""

    def test_defaults(self) -> None:
        p = ScanProgress()
        assert p.phase == ""
        assert p.current == 0
        assert p.total == 0
        assert not p.is_running
        assert not p.is_cancelled

    def test_percent_zero_total(self) -> None:
        p = ScanProgress(total=0, current=5)
        assert p.percent == 0

    def test_percent_halfway(self) -> None:
        p = ScanProgress(current=50, total=100)
        assert p.percent == 50.0

    def test_percent_complete(self) -> None:
        p = ScanProgress(current=10, total=10)
        assert p.percent == 100.0


class TestConnectionStatus:
    """Tests for ConnectionStatus dataclass."""

    def test_defaults(self) -> None:
        c = ConnectionStatus()
        assert not c.plex_connected
        assert c.plex_server_name == ""
        assert not c.tmdb_connected
        assert not c.tvdb_connected
        assert c.error_message == ""
        assert c.is_checking  # True by default


class TestAppState:
    """Tests for AppState dataclass."""

    def test_defaults(self) -> None:
        s = AppState()
        assert s.current_screen == Screen.DASHBOARD
        assert s.dark_mode is True
        assert not s.has_valid_config
        assert s.scan_type == ScanType.MOVIES
        assert s.movie_report is None
        assert s.tv_report is None
        assert s.scanning_screen is None

    def test_reset_scan(self) -> None:
        s = AppState()
        s.scan_progress = ScanProgress(phase="test", current=5, total=10, is_running=True)
        s.movie_report = "something"  # type: ignore[assignment]
        s.tv_report = "something"  # type: ignore[assignment]

        s.reset_scan()

        assert s.scan_progress.phase == ""
        assert s.scan_progress.current == 0
        assert not s.scan_progress.is_running
        assert s.movie_report is None
        assert s.tv_report is None
        assert s.scan_stats is None


class TestWindowState:
    """Tests for WindowState dataclass."""

    def test_defaults(self) -> None:
        w = WindowState()
        assert w.width == 1000
        assert w.height == 700
        assert w.x is None
        assert w.y is None
        assert not w.maximized

    def test_min_constraints(self) -> None:
        assert WindowState.MIN_WIDTH == 800
        assert WindowState.MIN_HEIGHT == 600


class TestValidateWindowPosition:
    """Tests for validate_window_position."""

    def test_normal_position(self) -> None:
        state = WindowState(width=1000, height=700, x=100, y=100)
        result = validate_window_position(state, 1920, 1080)
        assert result.width == 1000
        assert result.height == 700
        assert result.x == 100
        assert result.y == 100

    def test_enforces_minimum_size(self) -> None:
        state = WindowState(width=400, height=300)
        result = validate_window_position(state, 1920, 1080)
        assert result.width == WindowState.MIN_WIDTH
        assert result.height == WindowState.MIN_HEIGHT

    def test_caps_to_screen_size(self) -> None:
        state = WindowState(width=3000, height=2000)
        result = validate_window_position(state, 1920, 1080)
        assert result.width == 1920
        assert result.height == 1080

    def test_resets_offscreen_x(self) -> None:
        state = WindowState(width=1000, height=700, x=-2000, y=100)
        result = validate_window_position(state, 1920, 1080)
        assert result.x == 0

    def test_resets_offscreen_y_bottom(self) -> None:
        state = WindowState(width=1000, height=700, x=100, y=2000)
        result = validate_window_position(state, 1920, 1080)
        assert result.y == 1080 - 700

    def test_resets_negative_y(self) -> None:
        state = WindowState(width=1000, height=700, x=100, y=-50)
        result = validate_window_position(state, 1920, 1080)
        assert result.y == 0

    def test_none_position_stays_none(self) -> None:
        state = WindowState(width=1000, height=700, x=None, y=None)
        result = validate_window_position(state, 1920, 1080)
        assert result.x is None
        assert result.y is None

    def test_preserves_maximized(self) -> None:
        state = WindowState(maximized=True)
        result = validate_window_position(state, 1920, 1080)
        assert result.maximized is True


class TestWindowStatePersistence:
    """Tests for window state save/load round-trip."""

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        """Test that saving and loading produces the same state."""
        config_path = tmp_path / "complexionist.ini"
        config_path.write_text("[plex:0]\nname = Test\n", encoding="utf-8")

        # Save state
        state = WindowState(width=1200, height=800, x=50, y=75, maximized=True)
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        parser["window"] = {
            "width": str(state.width),
            "height": str(state.height),
            "x": str(state.x),
            "y": str(state.y),
            "maximized": str(state.maximized).lower(),
        }
        with open(config_path, "w", encoding="utf-8") as f:
            parser.write(f)

        # Load state
        parser2 = configparser.ConfigParser()
        parser2.read(config_path, encoding="utf-8")
        section = parser2["window"]
        loaded = WindowState(
            width=section.getint("width", 1000),
            height=section.getint("height", 700),
            x=section.getint("x") if "x" in section else None,
            y=section.getint("y") if "y" in section else None,
            maximized=section.getboolean("maximized", False),
        )

        assert loaded.width == 1200
        assert loaded.height == 800
        assert loaded.x == 50
        assert loaded.y == 75
        assert loaded.maximized is True

    def test_load_missing_section_returns_defaults(self, tmp_path: Path) -> None:
        config_path = tmp_path / "complexionist.ini"
        config_path.write_text("[plex:0]\nname = Test\n", encoding="utf-8")

        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        assert "window" not in parser
        # This is the same logic as load_window_state when section is missing
        result = WindowState()
        assert result.width == 1000
        assert result.height == 700


class TestLibrarySelectionPersistence:
    """Tests for library selection save/load round-trip."""

    def test_round_trip(self, tmp_path: Path) -> None:
        from complexionist.gui.library_state import LibrarySelection

        config_path = tmp_path / "complexionist.ini"
        config_path.write_text("[plex:0]\nname = Test\n", encoding="utf-8")

        # Save
        sel = LibrarySelection(movie_library="Movies", tv_library="TV Shows", active_server=1)
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")
        parser["libraries"] = {
            "movie_library": sel.movie_library,
            "tv_library": sel.tv_library,
            "active_server": str(sel.active_server),
        }
        with open(config_path, "w", encoding="utf-8") as f:
            parser.write(f)

        # Load
        parser2 = configparser.ConfigParser()
        parser2.read(config_path, encoding="utf-8")
        section = parser2["libraries"]
        loaded = LibrarySelection(
            movie_library=section.get("movie_library", ""),
            tv_library=section.get("tv_library", ""),
            active_server=int(section.get("active_server", "0")),
        )

        assert loaded.movie_library == "Movies"
        assert loaded.tv_library == "TV Shows"
        assert loaded.active_server == 1

    def test_defaults(self) -> None:
        from complexionist.gui.library_state import LibrarySelection

        sel = LibrarySelection()
        assert sel.movie_library == ""
        assert sel.tv_library == ""
        assert sel.active_server == 0


class TestStrings:
    """Tests for UI string constants."""

    def test_app_title_exists(self) -> None:
        from complexionist.gui import strings

        assert strings.APP_TITLE == "ComPlexionist"

    def test_all_strings_non_empty(self) -> None:
        from complexionist.gui import strings

        str_attrs = [
            attr
            for attr in dir(strings)
            if attr.isupper()
            and not attr.startswith("_")
            and isinstance(getattr(strings, attr), str)
        ]
        assert len(str_attrs) > 20  # Sanity check we're finding strings
        for attr in str_attrs:
            assert getattr(strings, attr), f"{attr} should not be empty"
