"""Library selection persistence for ComPlexionist GUI.

Saves and restores the selected movie/TV library names to the INI config file.
"""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LibrarySelection:
    """Persisted library selection state."""

    movie_library: str = ""
    tv_library: str = ""
    active_server: int = 0


def _get_config_path() -> Path | None:
    """Get the path to the config file if it exists."""
    from complexionist.config import find_config_file

    return find_config_file()


def load_library_selection() -> LibrarySelection:
    """Load saved library selection from the INI config file.

    Returns:
        LibrarySelection with saved values or empty defaults.
    """
    config_path = _get_config_path()
    if config_path is None or not config_path.exists():
        return LibrarySelection()

    try:
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")

        if "libraries" not in parser:
            return LibrarySelection()

        section = parser["libraries"]
        try:
            active_server = int(section.get("active_server", "0"))
        except ValueError:
            active_server = 0
        return LibrarySelection(
            movie_library=section.get("movie_library", ""),
            tv_library=section.get("tv_library", ""),
            active_server=active_server,
        )
    except Exception:
        return LibrarySelection()


def save_library_selection(selection: LibrarySelection) -> bool:
    """Save library selection to the INI config file.

    Args:
        selection: The library selection to save.

    Returns:
        True if saved successfully, False otherwise.
    """
    config_path = _get_config_path()
    if config_path is None or not config_path.exists():
        return False

    try:
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding="utf-8")

        if "libraries" not in parser:
            parser["libraries"] = {}

        parser["libraries"]["movie_library"] = selection.movie_library
        parser["libraries"]["tv_library"] = selection.tv_library
        parser["libraries"]["active_server"] = str(selection.active_server)

        with open(config_path, "w", encoding="utf-8") as f:
            parser.write(f)

        return True
    except Exception:
        return False
