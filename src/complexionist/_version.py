"""Version calculation for ComPlexionist.

Version format: MAJOR.MINOR.PATCH where PATCH is the git commit count.
Example: 1.1.47

The base version (MAJOR.MINOR) is manually controlled.
The patch number is automatically calculated from git history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Base version - bump this manually for releases
BASE_VERSION = "2.0"


def _get_commit_count() -> int | None:
    """Get the total number of commits in this package's repository.

    The git call is anchored to the package's own directory so the count
    comes from this repo regardless of the process cwd. Inside a
    PyInstaller bundle the extracted temp location is not a repo, so git
    fails and we fall back to None (handled by the caller).

    Returns:
        Commit count, or None if git is unavailable or not in a repo.
    """
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).parent,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (subprocess.SubprocessError, FileNotFoundError, ValueError, OSError):
        # OSError catches NotADirectoryError and other path-related errors
        # that can occur in bundled executables
        pass
    return None


def get_version() -> str:
    """Get the full version string.

    Returns:
        Version string in format "MAJOR.MINOR.PATCH" (e.g., "1.1.47")
        or "MAJOR.MINOR.0" if commit count unavailable.
    """
    commit_count = _get_commit_count()
    if commit_count is not None:
        return f"{BASE_VERSION}.{commit_count}"
    return f"{BASE_VERSION}.0"


# Calculate version once at import time
__version__ = get_version()
