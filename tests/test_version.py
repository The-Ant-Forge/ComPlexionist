"""Tests for version calculation (complexionist._version)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _repo_commit_count() -> int:
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return int(result.stdout.strip())


def test_commit_count_is_anchored_to_package_repo(tmp_path: Path) -> None:
    """The commit count must come from this repo regardless of process cwd."""
    code = "from complexionist._version import _get_commit_count; print(_get_commit_count())"
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=tmp_path,  # Not a git repo: an unanchored git call would fail here
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(_repo_commit_count())


def test_baked_version_is_absent_when_running_from_source() -> None:
    """No build stamp exists outside a PyInstaller bundle, so git is used."""
    from complexionist._version import BASE_VERSION, _get_baked_version, get_version

    assert _get_baked_version() is None
    assert get_version() == f"{BASE_VERSION}.{_repo_commit_count()}"


def test_baked_version_wins_over_git_count(tmp_path: Path) -> None:
    """A bundled build stamp takes priority over the live commit count.

    This is what makes a packaged exe report its real version: git is
    unavailable inside the extracted bundle, so without the stamp every
    release reported the bare "{BASE_VERSION}.0" fallback.
    """
    (tmp_path / "_complexionist_build_version.py").write_text(
        'BUILD_VERSION = "9.9.999"\n', encoding="utf-8"
    )
    code = (
        "import complexionist._version as v;"
        "import importlib; importlib.reload(v);"
        "print(v.get_version())"
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(tmp_path),  # Stand in for the bundle's import path
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "9.9.999"


def test_empty_baked_version_falls_back_to_git(tmp_path: Path) -> None:
    """An empty stamp must not produce an empty version string."""
    (tmp_path / "_complexionist_build_version.py").write_text(
        'BUILD_VERSION = ""\n', encoding="utf-8"
    )
    code = (
        "import complexionist._version as v;"
        "import importlib; importlib.reload(v);"
        "print(v.get_version())"
    )
    env = {**os.environ, "PYTHONPATH": str(tmp_path)}
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"2.0.{_repo_commit_count()}"
