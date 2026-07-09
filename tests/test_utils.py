"""Tests for utility functions (is_date_past, retry_with_backoff)."""

from datetime import date, timedelta

import pytest

from complexionist.utils import is_date_past, retry_with_backoff


class TestIsDatePast:
    """Tests for is_date_past and its 24-hour grace period.

    The function returns True only for dates at least one full day before
    today: content released "today" or "yesterday" is still within the
    grace period and is NOT considered past.
    """

    def test_none_is_not_past(self) -> None:
        assert is_date_past(None) is False

    def test_today_is_not_past(self) -> None:
        assert is_date_past(date.today()) is False

    def test_yesterday_is_not_past(self) -> None:
        # 24h grace period: released yesterday is still "too recent"
        assert is_date_past(date.today() - timedelta(days=1)) is False

    def test_two_days_ago_is_past(self) -> None:
        assert is_date_past(date.today() - timedelta(days=2)) is True

    def test_future_date_is_not_past(self) -> None:
        assert is_date_past(date.today() + timedelta(days=30)) is False

    def test_distant_past_is_past(self) -> None:
        assert is_date_past(date(2020, 1, 1)) is True


class _RateLimitedError(Exception):
    """Test exception carrying a retry_after hint (like TMDBRateLimitError)."""

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    @pytest.fixture(autouse=True)
    def _record_sleeps(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Record (and neutralize) backoff sleeps."""
        self.sleep_calls: list[float] = []
        monkeypatch.setattr(
            "complexionist.utils.time.sleep",
            lambda seconds: self.sleep_calls.append(seconds),
        )

    def test_succeeds_after_transient_failures(self) -> None:
        """Two transient failures then success: result returned, backoff doubles."""
        attempts: list[int] = []

        @retry_with_backoff(max_retries=3, base_delay=1.0, retry_on=(ValueError,))
        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise ValueError("transient")
            return "ok"

        assert flaky() == "ok"
        assert len(attempts) == 3
        # Exponential backoff: 1.0 * 2^0, then 1.0 * 2^1
        assert self.sleep_calls == [1.0, 2.0]

    def test_exhausts_retries_and_reraises(self) -> None:
        """After max_retries + 1 attempts the last exception is re-raised."""
        attempts: list[int] = []

        @retry_with_backoff(max_retries=2, base_delay=1.0, retry_on=(ValueError,))
        def always_fails() -> None:
            attempts.append(1)
            raise ValueError(f"failure {len(attempts)}")

        with pytest.raises(ValueError, match="failure 3"):
            always_fails()

        assert len(attempts) == 3  # initial call + 2 retries
        assert self.sleep_calls == [1.0, 2.0]  # no sleep after the final attempt

    def test_honors_retry_after(self) -> None:
        """A retry_after hint larger than the computed backoff wins."""
        attempts: list[int] = []

        @retry_with_backoff(max_retries=1, base_delay=1.0, retry_on=(_RateLimitedError,))
        def rate_limited() -> str:
            attempts.append(1)
            if len(attempts) == 1:
                raise _RateLimitedError("slow down", retry_after=10)
            return "ok"

        assert rate_limited() == "ok"
        assert self.sleep_calls == [10.0]

    def test_respects_max_delay(self) -> None:
        """Computed backoff is capped at max_delay."""
        attempts: list[int] = []

        @retry_with_backoff(max_retries=3, base_delay=10.0, max_delay=15.0, retry_on=(ValueError,))
        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 4:
                raise ValueError("transient")
            return "ok"

        assert flaky() == "ok"
        # 10 * 2^0 = 10, then 10 * 2^1 = 20 -> capped to 15, again capped
        assert self.sleep_calls == [10.0, 15.0, 15.0]

    def test_non_matching_exception_propagates_immediately(self) -> None:
        """Exceptions not in retry_on are not retried."""
        attempts: list[int] = []

        @retry_with_backoff(max_retries=3, base_delay=1.0, retry_on=(ValueError,))
        def wrong_error() -> None:
            attempts.append(1)
            raise KeyError("not retryable")

        with pytest.raises(KeyError):
            wrong_error()

        assert len(attempts) == 1
        assert self.sleep_calls == []
