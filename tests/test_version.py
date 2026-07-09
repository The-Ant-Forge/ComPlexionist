"""Tests for version calculation (complexionist._version)."""

from __future__ import annotations

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
