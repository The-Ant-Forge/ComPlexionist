"""Tests for the CLI module."""

import re

from click.testing import CliRunner

from complexionist import __version__
from complexionist.cli import main


def test_main_help() -> None:
    """Test that --help works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "ComPlexionist" in result.output


def test_version() -> None:
    """Test that --version works."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    # Version format: MAJOR.MINOR.PATCH (e.g., 1.1.47)
    assert re.search(r"\d+\.\d+\.\d+", result.output)
    assert __version__ in result.output


def test_movies_command_exists() -> None:
    """Test that the movies command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["movies", "--help"])
    assert result.exit_code == 0
    assert "missing movies" in result.output.lower()


def test_tv_command_exists() -> None:
    """Test that the tv command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["tv", "--help"])
    assert result.exit_code == 0
    assert "missing episodes" in result.output.lower()


def test_scan_command_exists() -> None:
    """Test that the scan command exists."""
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "movie" in result.output.lower()


def test_config_path() -> None:
    """Test the config path command."""
    runner = CliRunner()
    result = runner.invoke(main, ["config", "path"])
    assert result.exit_code == 0
    assert ".complexionist" in result.output
