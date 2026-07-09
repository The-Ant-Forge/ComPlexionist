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

    def test_reset_scan_cancels_old_progress(self) -> None:
        """reset_scan marks the outgoing ScanProgress cancelled (finding 11).

        A scan thread bound to the old object must see is_cancelled and stop;
        the fresh ScanProgress starts clean.
        """
        s = AppState()
        old_progress = s.scan_progress
        old_progress.is_running = True

        s.reset_scan()

        assert old_progress.is_cancelled is True
        assert s.scan_progress is not old_progress
        assert not s.scan_progress.is_cancelled
        assert not s.scan_progress.is_running

    def test_second_scan_guard_condition(self) -> None:
        """The start_scan guard blocks while scan_progress.is_running (finding 11)."""
        s = AppState()
        assert not s.scan_progress.is_running  # first scan may start

        s.scan_progress.is_running = True
        assert s.scan_progress.is_running  # second scan must be blocked

        # Completion clears the flag, allowing the next scan
        s.scan_progress.is_running = False
        assert not s.scan_progress.is_running


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

    def test_save_preserves_comments(self, tmp_path: Path, monkeypatch) -> None:
        """Saving the selection edits only [libraries]; comments survive (finding 13)."""
        from complexionist.config import reset_config
        from complexionist.gui.library_state import LibrarySelection, save_library_selection

        config_path = tmp_path / "complexionist.ini"
        config_path.write_text(
            "# my precious comment\n[plex:0]\nname = Test\ntoken = ${PLEX_TOKEN}\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        reset_config()
        try:
            sel = LibrarySelection(movie_library="Movies", tv_library="TV", active_server=0)
            assert save_library_selection(sel)
        finally:
            reset_config()

        content = config_path.read_text(encoding="utf-8")
        assert "# my precious comment" in content
        assert "token = ${PLEX_TOKEN}" in content
        assert "[libraries]" in content
        assert "movie_library = Movies" in content

    def test_save_skips_write_when_unchanged(self, tmp_path: Path, monkeypatch) -> None:
        """An unchanged selection performs no file write at all (finding 13)."""
        import complexionist.config as config_mod
        from complexionist.config import reset_config
        from complexionist.gui.library_state import LibrarySelection, save_library_selection

        config_path = tmp_path / "complexionist.ini"
        config_path.write_text(
            "[plex:0]\nname = Test\n\n[libraries]\n"
            "movie_library = Movies\ntv_library = TV\nactive_server = 0\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        reset_config()

        calls: list[object] = []
        original = config_mod.update_ini_file

        def spy(*args: object, **kwargs: object) -> None:
            calls.append(args)
            original(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(config_mod, "update_ini_file", spy)
        try:
            sel = LibrarySelection(movie_library="Movies", tv_library="TV", active_server=0)
            assert save_library_selection(sel)
        finally:
            reset_config()

        assert calls == []


class TestStartupErrors:
    """Tests for startup connection-error logging and surfacing."""

    def test_initialize_state_logs_startup_error(self, tmp_path, monkeypatch) -> None:
        """Startup connection failures are written to the error log."""
        import complexionist.config as config_mod
        from complexionist.gui import app as gui_app

        monkeypatch.setattr(config_mod, "get_exe_directory", lambda: tmp_path)

        def _raise(state: AppState, cfg: object) -> None:
            raise RuntimeError("no route to host")

        monkeypatch.setattr(gui_app, "_test_connections", _raise)

        state = AppState()
        state.has_valid_config = True
        gui_app._initialize_state(state)

        assert state.connection.error_message == "no route to host"
        log_file = tmp_path / "complexionist_errors.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Startup connection test" in content
        assert "no route to host" in content

    def test_dashboard_badge_tooltip_shows_error_message(self) -> None:
        """The dashboard status pills surface connection.error_message."""
        from unittest.mock import MagicMock

        from complexionist.gui.screens.dashboard import DashboardScreen

        state = AppState()
        state.connection.is_checking = False
        state.connection.plex_connected = False
        state.connection.error_message = "no route to host"

        screen = DashboardScreen(
            MagicMock(),
            state,
            on_scan=lambda scan_type: None,
            on_settings=lambda: None,
        )
        row = screen._create_status_badges()
        tooltips = [str(badge.tooltip or "") for badge in row.controls]
        assert any("no route to host" in tip for tip in tooltips)


class TestMediaBadge:
    """Tests for the results-screen pill badge rendering.

    A construction-level canary for Flet API breakage (the class of bug
    behind the v2.0.148 frozen-exe crash): if Container/Text/Border/Padding
    signatures change, this fails at import or construction time.
    """

    def test_media_badge_structure(self) -> None:
        import flet as ft

        from complexionist.gui.screens.results import (
            _BADGE_BG,
            _BADGE_BORDER,
            _BADGE_TEXT,
            _media_badge,
        )

        badge = _media_badge("1080p")

        assert isinstance(badge, ft.Container)
        assert badge.bgcolor == _BADGE_BG
        assert badge.border_radius == 8

        # Border: 1px on all sides in the badge border color
        assert badge.border is not None
        for side in (badge.border.top, badge.border.right, badge.border.bottom, badge.border.left):
            assert side is not None
            assert side.width == 1
            assert side.color == _BADGE_BORDER

        # Padding: symmetric(horizontal=6, vertical=1)
        assert badge.padding is not None
        assert badge.padding.left == 6
        assert badge.padding.right == 6
        assert badge.padding.top == 1
        assert badge.padding.bottom == 1

        # Label text
        assert isinstance(badge.content, ft.Text)
        assert badge.content.value == "1080p"
        assert badge.content.size == 11
        assert badge.content.color == _BADGE_TEXT


class TestShowSnackbar:
    """Snackbars remove themselves from page.overlay on dismiss (finding 40)."""

    def test_snackbar_removed_on_dismiss(self) -> None:
        from unittest.mock import MagicMock

        import flet as ft

        from complexionist.gui.errors import show_snackbar

        page = MagicMock()
        page.overlay = []
        snack = ft.SnackBar(content=ft.Text("hello"))

        show_snackbar(page, snack)
        assert snack in page.overlay
        assert snack.open is True

        # Simulate the dismiss event firing
        assert snack.on_dismiss is not None
        snack.on_dismiss()
        assert snack not in page.overlay

    def test_error_helper_uses_self_cleaning_snackbar(self) -> None:
        from unittest.mock import MagicMock

        from complexionist.gui.errors import show_warning

        page = MagicMock()
        page.overlay = []

        show_warning(page, "careful")
        assert len(page.overlay) == 1
        snack = page.overlay[0]
        assert snack.on_dismiss is not None
        snack.on_dismiss()
        assert page.overlay == []


class TestSearchDebounce:
    """Search input is debounced instead of rebuilding per keystroke (finding 39)."""

    @staticmethod
    def _make_screen() -> object:
        from unittest.mock import MagicMock

        from complexionist.gui.screens.results import ResultsScreen

        return ResultsScreen(
            MagicMock(), AppState(), on_back=lambda: None, on_export=lambda fmt: None
        )

    def test_new_keystroke_cancels_previous_timer(self) -> None:
        from unittest.mock import MagicMock

        screen = self._make_screen()
        event1 = MagicMock()
        event1.control.value = "a"
        screen._on_search(event1)  # type: ignore[attr-defined]
        timer1 = screen._search_debounce  # type: ignore[attr-defined]

        event2 = MagicMock()
        event2.control.value = "ab"
        screen._on_search(event2)  # type: ignore[attr-defined]
        timer2 = screen._search_debounce  # type: ignore[attr-defined]

        try:
            assert timer1 is not timer2
            # The first timer was cancelled before the second started
            assert timer1.finished.is_set()
            assert not timer2.finished.is_set()
        finally:
            timer2.cancel()

    def test_debounce_fires_via_run_task(self) -> None:
        import time
        from unittest.mock import MagicMock

        screen = self._make_screen()
        event = MagicMock()
        event.control.value = "query"
        screen._on_search(event)  # type: ignore[attr-defined]

        # No immediate rebuild — only after the ~250ms debounce interval
        assert screen.page.run_task.call_count == 0  # type: ignore[attr-defined]
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and screen.page.run_task.call_count == 0:  # type: ignore[attr-defined]
            time.sleep(0.02)
        assert screen.page.run_task.call_count == 1  # type: ignore[attr-defined]


class TestPendingMoves:
    """Tests for organize-move shutdown tracking (review 2026-07 finding 12)."""

    def test_wait_returns_immediately_with_no_thread(self) -> None:
        import complexionist.gui.screens.results as results_mod

        results_mod._move_thread = None
        results_mod.wait_for_pending_moves(timeout=0.1)  # must not raise or block

    def test_wait_joins_running_move_thread(self) -> None:
        import threading
        import time

        import complexionist.gui.screens.results as results_mod

        thread = threading.Thread(target=lambda: time.sleep(0.2), daemon=False)
        results_mod._move_thread = thread
        thread.start()
        try:
            results_mod.wait_for_pending_moves(timeout=5.0)
            assert not thread.is_alive()
        finally:
            thread.join()
            results_mod._move_thread = None


class TestFinderOptions:
    """GUI scan wiring builds finder kwargs from config (review 2026-07 finding 15)."""

    @staticmethod
    def _config() -> object:
        from complexionist.config import AppConfig

        return AppConfig.model_validate(
            {
                "options": {
                    "min_collection_size": 4,
                    "min_owned": 3,
                    "recent_threshold_hours": 48,
                },
                "exclusions": {
                    "shows": ["Daily Talk Show"],
                    "collections": ["Anthology Collection"],
                },
            }
        )

    def test_movie_finder_options(self) -> None:
        from complexionist.gui.app import _movie_finder_options

        opts = _movie_finder_options(self._config())  # type: ignore[arg-type]

        assert opts == {
            "include_future": False,
            "min_collection_size": 4,
            "min_owned": 3,
            "excluded_collections": ["Anthology Collection"],
        }

    def test_tv_finder_options(self) -> None:
        from complexionist.gui.app import _tv_finder_options

        opts = _tv_finder_options(self._config())  # type: ignore[arg-type]

        assert opts == {
            "include_future": False,
            "include_specials": False,
            "recent_threshold_hours": 48,
            "excluded_shows": ["Daily Talk Show"],
        }

    def test_options_accepted_by_finders(self) -> None:
        """Every kwarg the helpers emit is a valid finder constructor argument."""
        from unittest.mock import MagicMock

        from complexionist.gaps import EpisodeGapFinder, MovieGapFinder
        from complexionist.gui.app import _movie_finder_options, _tv_finder_options

        config = self._config()
        movie_finder = MovieGapFinder(
            plex_client=MagicMock(),
            tmdb_client=MagicMock(),
            **_movie_finder_options(config),  # type: ignore[arg-type]
        )
        assert movie_finder.min_collection_size == 4
        assert movie_finder.min_owned == 3
        assert movie_finder.excluded_collections == {"anthology collection"}

        tv_finder = EpisodeGapFinder(
            plex_client=MagicMock(),
            tvdb_client=MagicMock(),
            **_tv_finder_options(config),  # type: ignore[arg-type]
        )
        assert tv_finder.recent_threshold_hours == 48
        assert tv_finder.include_specials is False
        assert tv_finder.excluded_shows == {"daily talk show"}
