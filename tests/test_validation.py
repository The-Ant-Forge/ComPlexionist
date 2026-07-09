"""Tests for configuration validation (complexionist.validation)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from complexionist.config import AppConfig, TMDBConfig


def test_test_connections_reports_tmdb_transport_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A transport error during the TMDB test yields a failure result, not a traceback."""
    from complexionist import validation

    cfg = AppConfig(tmdb=TMDBConfig(api_key="test-key"))
    monkeypatch.setattr("complexionist.validation.get_config", lambda: cfg)
    monkeypatch.setattr("complexionist.config.get_config", lambda: cfg)

    with patch("httpx.Client.get", MagicMock(side_effect=httpx.ConnectError("refused"))):
        result = validation.test_connections()

    assert result.tmdb_ok is False
    assert result.tmdb_error
