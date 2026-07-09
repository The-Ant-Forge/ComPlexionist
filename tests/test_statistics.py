"""Tests for the statistics module."""

import threading
import time
from datetime import timedelta
from io import StringIO

from rich.console import Console

from complexionist.statistics import PhaseStats, ScanStatistics


class TestPhaseStats:
    """Tests for PhaseStats dataclass."""

    def test_duration_while_running(self) -> None:
        """Test duration calculation while phase is running."""
        phase = PhaseStats(name="Test", started_at=time.time() - 1)
        # Should be approximately 1 second
        assert 0.9 < phase.duration_seconds < 1.5

    def test_duration_after_ended(self) -> None:
        """Test duration calculation after phase has ended."""
        start = time.time()
        phase = PhaseStats(name="Test", started_at=start, ended_at=start + 2.5)
        assert abs(phase.duration_seconds - 2.5) < 0.01


class TestScanStatistics:
    """Tests for ScanStatistics class."""

    def test_start_and_stop(self) -> None:
        """Test starting and stopping statistics."""
        stats = ScanStatistics()
        stats.start()
        time.sleep(0.1)
        stats.stop()

        assert stats.total_duration.total_seconds() >= 0.1
        assert ScanStatistics.get_current() is stats

    def test_get_current(self) -> None:
        """Test get_current returns active instance."""
        ScanStatistics.reset_current()
        assert ScanStatistics.get_current() is None

        stats = ScanStatistics()
        stats.start()
        assert ScanStatistics.get_current() is stats

        ScanStatistics.reset_current()
        assert ScanStatistics.get_current() is None

    def test_record_api_calls(self) -> None:
        """Test recording API calls."""
        stats = ScanStatistics()

        stats.record_api_call("tmdb_movie")
        stats.record_api_call("tmdb_movie")
        stats.record_api_call("tmdb_collection")
        stats.record_api_call("tvdb_series")
        stats.record_api_call("tvdb_episode")
        stats.record_api_call("tvdb_episode")

        assert stats.tmdb_movie_requests == 2
        assert stats.tmdb_collection_requests == 1
        assert stats.tvdb_series_requests == 1
        assert stats.tvdb_episode_requests == 2
        assert stats.total_api_calls == 6

    def test_record_cache_hits_and_misses(self) -> None:
        """Test recording cache hits and misses."""
        stats = ScanStatistics()

        stats.record_cache_hit()
        stats.record_cache_hit()
        stats.record_cache_hit()
        stats.record_cache_miss()

        assert stats.cache_hits == 3
        assert stats.cache_misses == 1
        assert stats.cache_hit_rate == 75.0

    def test_cache_hit_rate_empty(self) -> None:
        """Test cache hit rate when no cache operations."""
        stats = ScanStatistics()
        assert stats.cache_hit_rate == 0.0

    def test_phase_tracking(self) -> None:
        """Test phase start and end."""
        stats = ScanStatistics()
        stats.start()

        stats.start_phase("Phase 1")
        time.sleep(0.05)
        stats.end_phase(item_count=100)

        stats.start_phase("Phase 2")
        time.sleep(0.05)
        stats.end_phase(item_count=50)

        stats.stop()

        assert len(stats.phases) == 2
        assert stats.phases[0].name == "Phase 1"
        assert stats.phases[0].item_count == 100
        assert stats.phases[1].name == "Phase 2"
        assert stats.phases[1].item_count == 50

    def test_auto_end_phase_on_new_phase(self) -> None:
        """Test that starting a new phase ends the current one."""
        stats = ScanStatistics()

        stats.start_phase("Phase 1")
        stats.start_phase("Phase 2")  # Should auto-end Phase 1
        stats.end_phase()

        assert len(stats.phases) == 2
        assert stats.phases[0].name == "Phase 1"
        assert stats.phases[1].name == "Phase 2"

    def test_print_summary(self) -> None:
        """Test printing summary to console."""
        stats = ScanStatistics()
        stats.start()

        stats.start_phase("Fetching movies")
        stats.record_api_call("tmdb_movie")
        stats.record_cache_miss()
        stats.end_phase(item_count=50)

        stats.start_phase("Checking collections")
        stats.record_api_call("tmdb_collection")
        stats.record_cache_hit()
        stats.end_phase(item_count=10)

        stats.stop()

        # Capture output (no_color to avoid ANSI escape codes)
        output = StringIO()
        console = Console(file=output, force_terminal=False, no_color=True, width=80)
        stats.print_summary(console)

        output_text = output.getvalue()
        assert "Scan Summary" in output_text
        assert "Fetching movies" in output_text
        assert "50 items" in output_text
        assert "API calls" in output_text
        assert "Cache" in output_text
        assert "50%" in output_text  # Hit rate

    def test_format_duration_seconds(self) -> None:
        """Test duration formatting for seconds."""
        stats = ScanStatistics()
        result = stats._format_duration(timedelta(seconds=5.5))
        assert result == "5.5s"

    def test_format_duration_minutes(self) -> None:
        """Test duration formatting for minutes."""
        stats = ScanStatistics()
        result = stats._format_duration(timedelta(minutes=2, seconds=30))
        assert result == "2m 30.0s"


class TestScanStatisticsThreadSafety:
    """Verify counters don't lose increments under concurrent access."""

    def test_concurrent_api_call_recording(self) -> None:
        stats = ScanStatistics()
        stats.start()
        iterations = 500

        def record_calls() -> None:
            for _ in range(iterations):
                stats.record_api_call("tmdb_movie")

        t1 = threading.Thread(target=record_calls)
        t2 = threading.Thread(target=record_calls)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert stats.tmdb_movie_requests == iterations * 2

    def test_concurrent_cache_hit_recording(self) -> None:
        stats = ScanStatistics()
        stats.start()
        iterations = 500

        def record_hits() -> None:
            for _ in range(iterations):
                stats.record_cache_hit("tmdb")

        t1 = threading.Thread(target=record_hits)
        t2 = threading.Thread(target=record_hits)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert stats.cache_hits == iterations * 2
        assert stats.cache_hits_tmdb == iterations * 2

    def test_concurrent_cache_miss_recording(self) -> None:
        stats = ScanStatistics()
        stats.start()
        iterations = 500

        def record_misses() -> None:
            for _ in range(iterations):
                stats.record_cache_miss("tmdb")
                stats.record_api_call("tmdb_movie")

        t1 = threading.Thread(target=record_misses)
        t2 = threading.Thread(target=record_misses)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert stats.cache_misses == iterations * 2
        assert stats.cache_misses_tmdb == iterations * 2
        assert stats.tmdb_movie_requests == iterations * 2


class TestSkippedItems:
    """Tests for the skipped-item counter (review 2026-07 finding 7)."""

    def test_record_skipped_increments(self) -> None:
        stats = ScanStatistics()
        assert stats.items_skipped == 0
        stats.record_skipped()
        stats.record_skipped()
        assert stats.items_skipped == 2

    def test_record_skipped_item_uses_current_instance(self) -> None:
        from complexionist.statistics import record_skipped_item

        stats = ScanStatistics()
        stats.start()
        try:
            record_skipped_item()
            assert stats.items_skipped == 1
        finally:
            ScanStatistics.reset_current()

    def test_record_skipped_item_noop_without_active_scan(self) -> None:
        from complexionist.statistics import record_skipped_item

        ScanStatistics.reset_current()
        record_skipped_item()  # must not raise

    def test_concurrent_skipped_recording(self) -> None:
        stats = ScanStatistics()
        iterations = 500

        def record() -> None:
            for _ in range(iterations):
                stats.record_skipped()

        t1 = threading.Thread(target=record)
        t2 = threading.Thread(target=record)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert stats.items_skipped == iterations * 2
