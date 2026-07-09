"""Tests for GUI onboarding connection tests (error-message sanitization).

The TMDB key rides in the request URL, so raw exception text (which can
embed the full URL) must never be interpolated into user-facing messages.
"""

from __future__ import annotations

import pytest
import requests

SECRET = "SECRETKEY123"


def _raise_connection_error(*args: object, **kwargs: object) -> None:
    raise requests.exceptions.ConnectionError(
        "HTTPSConnectionPool(host='api.themoviedb.org', port=443): Max retries "
        f"exceeded with url: /3/configuration?api_key={SECRET}"
    )


def _raise_unexpected(*args: object, **kwargs: object) -> None:
    raise RuntimeError(f"unexpected failure for url ?api_key={SECRET}")


class TestOnboardingMessageSanitization:
    def test_tmdb_connection_error_does_not_leak_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from complexionist.gui.screens import onboarding

        monkeypatch.setattr("requests.get", _raise_connection_error)
        ok, message = onboarding._test_tmdb_connection(SECRET)
        assert ok is False
        assert SECRET not in message

    def test_tmdb_unexpected_error_does_not_leak_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from complexionist.gui.screens import onboarding

        monkeypatch.setattr("requests.get", _raise_unexpected)
        ok, message = onboarding._test_tmdb_connection(SECRET)
        assert ok is False
        assert SECRET not in message

    def test_tvdb_connection_error_does_not_leak_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from complexionist.gui.screens import onboarding

        monkeypatch.setattr("requests.post", _raise_connection_error)
        ok, message = onboarding._test_tvdb_connection(SECRET)
        assert ok is False
        assert SECRET not in message

    def test_tvdb_unexpected_error_does_not_leak_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from complexionist.gui.screens import onboarding

        monkeypatch.setattr("requests.post", _raise_unexpected)
        ok, message = onboarding._test_tvdb_connection(SECRET)
        assert ok is False
        assert SECRET not in message

    def test_plex_unexpected_error_does_not_leak_token(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from complexionist.gui.screens import onboarding

        monkeypatch.setattr("requests.get", _raise_unexpected)
        ok, message, name = onboarding._test_plex_connection("http://plex:32400", SECRET)
        assert ok is False
        assert SECRET not in message
        assert name == ""
