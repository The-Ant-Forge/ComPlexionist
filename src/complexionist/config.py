"""Configuration management for ComPlexionist."""

from __future__ import annotations

import configparser
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PlexConfig(BaseModel):
    """Plex server configuration."""

    url: str | None = None
    token: str | None = None


class TMDBConfig(BaseModel):
    """TMDB API configuration."""

    api_key: str | None = None
    ignored_collections: list[int] = Field(default_factory=list)


class TVDBConfig(BaseModel):
    """TVDB API configuration."""

    api_key: str | None = None
    pin: str | None = None
    ignored_shows: list[int] = Field(default_factory=list)


class OptionsConfig(BaseModel):
    """General options configuration."""

    exclude_future: bool = True
    exclude_specials: bool = True
    recent_threshold_hours: int = 24
    min_collection_size: int = 2
    min_owned: int = 2  # Minimum owned movies to report collection gaps
    find: bool = False  # Enable NZB search links (secret feature)


class ExclusionsConfig(BaseModel):
    """Content exclusion configuration."""

    shows: list[str] = Field(default_factory=list)
    collections: list[str] = Field(default_factory=list)


class PathsConfig(BaseModel):
    """Path mapping configuration for remote/network access.

    When Plex returns paths using the server's mount points (e.g., \\\\volume1\\video),
    but your local machine accesses the same files via a different path
    (e.g., \\\\Storage4\\video), use these settings to map the paths.
    """

    plex_prefix: str | None = None  # Path prefix as Plex sees it
    local_prefix: str | None = None  # Path prefix as local machine sees it


class AppConfig(BaseModel):
    """Application configuration."""

    plex: PlexConfig = Field(default_factory=PlexConfig)
    tmdb: TMDBConfig = Field(default_factory=TMDBConfig)
    tvdb: TVDBConfig = Field(default_factory=TVDBConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    exclusions: ExclusionsConfig = Field(default_factory=ExclusionsConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)


# Global config instance
_config: AppConfig | None = None
_config_path: Path | None = None  # Track where config was loaded from


def get_exe_directory() -> Path:
    """Get the directory containing the executable (or script).

    Handles both normal Python execution and PyInstaller bundles.

    Returns:
        Path to the directory containing the exe or main script.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle - use executable location
        return Path(sys.executable).parent
    else:
        # Running as Python script - use current working directory
        # (not __file__ since that's inside the package)
        return Path.cwd()


def get_config_paths() -> list[Path]:
    """Get list of config file paths to search, in priority order.

    Search order:
    1. Exe directory (for portability with PyInstaller)
    2. Current working directory
    3. User home directory (~/.complexionist/)

    INI format (.cfg) is preferred over YAML for new installs.

    Returns:
        List of paths to check for config files.
    """
    paths = []

    exe_dir = get_exe_directory()
    home_dir = Path.home() / ".complexionist"

    # 1. Exe directory - INI format (highest priority)
    paths.append(exe_dir / "complexionist.ini")

    # 2. Current directory - INI format
    cwd = Path.cwd()
    if cwd != exe_dir:  # Avoid duplicates
        paths.append(cwd / "complexionist.ini")

    # 3. Home directory - INI format
    paths.append(home_dir / "complexionist.ini")

    # 4. Legacy YAML support (backwards compatibility, lower priority)
    paths.append(cwd / "config.yaml")
    paths.append(cwd / "config.yml")
    paths.append(cwd / ".complexionist.yaml")
    paths.append(cwd / ".complexionist.yml")
    paths.append(home_dir / "config.yaml")
    paths.append(home_dir / "config.yml")

    return paths


def find_config_file() -> Path | None:
    """Find the first existing config file.

    Returns:
        Path to config file if found, None otherwise.
    """
    for path in get_config_paths():
        if path.exists():
            return path
    return None


def _expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in config values.

    Supports ${VAR} and $VAR syntax.

    Args:
        value: Config value (string, dict, list, or other).

    Returns:
        Value with environment variables expanded.
    """
    if isinstance(value, str):
        # Pattern matches ${VAR} or $VAR
        pattern = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")

        def replace(match: re.Match[str]) -> str:
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, "")

        return pattern.sub(replace, value)
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    return value


def _parse_bool(value: str) -> bool:
    """Parse a boolean value from a string.

    Args:
        value: String to parse (true/false/yes/no/1/0).

    Returns:
        Boolean value.
    """
    return value.lower() in ("true", "yes", "1", "on")


def _parse_list(value: str) -> list[str]:
    """Parse a comma-separated list from a string.

    Args:
        value: Comma-separated string.

    Returns:
        List of stripped strings, excluding empty items.
    """
    if not value or not value.strip():
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_int_list(value: str) -> list[int]:
    """Parse a comma-separated list of integers from a string.

    Args:
        value: Comma-separated string of integers.

    Returns:
        List of integers, excluding invalid items.
    """
    if not value or not value.strip():
        return []
    result = []
    for item in value.split(","):
        item = item.strip()
        if item:
            try:
                result.append(int(item))
            except ValueError:
                pass  # Skip invalid integers
    return result


def _load_ini_config(path: Path) -> dict[str, Any]:
    """Load configuration from INI file.

    Args:
        path: Path to INI config file.

    Returns:
        Dictionary structure matching AppConfig schema.
    """
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    config: dict[str, Any] = {}

    # Parse [plex] section
    if parser.has_section("plex"):
        config["plex"] = {
            "url": parser.get("plex", "url", fallback=None),
            "token": parser.get("plex", "token", fallback=None),
        }
        # Remove None values
        config["plex"] = {k: v for k, v in config["plex"].items() if v}

    # Parse [tmdb] section
    if parser.has_section("tmdb"):
        tmdb_config: dict[str, Any] = {}
        api_key = parser.get("tmdb", "api_key", fallback=None)
        if api_key:
            tmdb_config["api_key"] = api_key
        if parser.has_option("tmdb", "ignored_collections"):
            tmdb_config["ignored_collections"] = _parse_int_list(
                parser.get("tmdb", "ignored_collections")
            )
        if tmdb_config:
            config["tmdb"] = tmdb_config

    # Parse [tvdb] section
    if parser.has_section("tvdb"):
        tvdb_config: dict[str, Any] = {
            "api_key": parser.get("tvdb", "api_key", fallback=None),
            "pin": parser.get("tvdb", "pin", fallback=None),
        }
        if parser.has_option("tvdb", "ignored_shows"):
            tvdb_config["ignored_shows"] = _parse_int_list(parser.get("tvdb", "ignored_shows"))
        # Remove None values but keep lists
        config["tvdb"] = {k: v for k, v in tvdb_config.items() if v is not None and v != ""}

    # Parse [options] section
    if parser.has_section("options"):
        options: dict[str, Any] = {}
        for key in [
            "exclude_future",
            "exclude_specials",
            "find",
        ]:
            if parser.has_option("options", key):
                options[key] = _parse_bool(parser.get("options", key))
        for key in [
            "recent_threshold_hours",
            "min_collection_size",
            "min_owned",
        ]:
            if parser.has_option("options", key):
                try:
                    options[key] = int(parser.get("options", key))
                except ValueError:
                    pass  # Keep default
        if options:
            config["options"] = options

    # Parse [exclusions] section
    if parser.has_section("exclusions"):
        exclusions: dict[str, list[str]] = {}
        if parser.has_option("exclusions", "shows"):
            exclusions["shows"] = _parse_list(parser.get("exclusions", "shows"))
        if parser.has_option("exclusions", "collections"):
            exclusions["collections"] = _parse_list(parser.get("exclusions", "collections"))
        if exclusions:
            config["exclusions"] = exclusions

    # Parse [paths] section
    if parser.has_section("paths"):
        paths: dict[str, str | None] = {}
        if parser.has_option("paths", "plex_prefix"):
            value = parser.get("paths", "plex_prefix").strip()
            if value:
                paths["plex_prefix"] = value
        if parser.has_option("paths", "local_prefix"):
            value = parser.get("paths", "local_prefix").strip()
            if value:
                paths["local_prefix"] = value
        if paths:
            config["paths"] = paths

    return config


def _load_yaml_config(path: Path) -> dict[str, Any]:
    """Load configuration from YAML file.

    Args:
        path: Path to YAML config file.

    Returns:
        Dictionary structure matching AppConfig schema.
    """
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from file.

    Supports both INI (.cfg) and YAML (.yaml/.yml) formats.
    Environment variables are expanded in all values using ${VAR} syntax.

    Args:
        path: Explicit path to config file. If None, searches default locations.

    Returns:
        Loaded configuration with environment variables expanded.
    """
    global _config, _config_path

    # Find config file
    if path is None:
        path = find_config_file()

    if path is None or not path.exists():
        # No config file, return defaults
        _config = AppConfig()
        _config_path = None
        return _config

    # Load based on file extension
    if path.suffix in (".ini", ".cfg"):
        raw_config = _load_ini_config(path)
    else:
        raw_config = _load_yaml_config(path)

    # Expand environment variables
    expanded_config = _expand_env_vars(raw_config)

    # Parse into config model
    _config = AppConfig.model_validate(expanded_config)
    _config_path = path
    return _config


def get_config_path() -> Path | None:
    """Get the path to the currently loaded config file.

    Returns:
        Path to config file, or None if using defaults.
    """
    return _config_path


def get_config() -> AppConfig:
    """Get the current configuration.

    Loads from file if not already loaded.

    Returns:
        Current application configuration.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def has_valid_config() -> bool:
    """Check if configuration has minimum required credentials.

    Checks that:
    1. A config file exists
    2. Plex URL and token are set
    3. TMDB API key is set
    4. TVDB API key is set

    Returns:
        True if all required credentials are configured.
    """
    if find_config_file() is None:
        return False

    cfg = get_config()
    return bool(cfg.plex.url and cfg.plex.token and cfg.tmdb.api_key and cfg.tvdb.api_key)


def reset_config() -> None:
    """Reset the cached configuration.

    Useful for testing or when config file changes.
    """
    global _config, _config_path
    _config = None
    _config_path = None


def get_config_dir() -> Path:
    """Get the user config directory.

    Creates the directory if it doesn't exist.

    Returns:
        Path to config directory.
    """
    config_dir = Path.home() / ".complexionist"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def save_default_config(
    path: Path | None = None,
    plex_url: str = "",
    plex_token: str = "",
    tmdb_api_key: str = "",
    tvdb_api_key: str = "",
) -> Path:
    """Save a default INI config file.

    Args:
        path: Where to save. Defaults to ./complexionist.cfg (current directory).
        plex_url: Plex server URL (optional, can use env var).
        plex_token: Plex token (optional, can use env var).
        tmdb_api_key: TMDB API key (optional, can use env var).
        tvdb_api_key: TVDB API key (optional, can use env var).

    Returns:
        Path to saved config file.
    """
    if path is None:
        path = Path.cwd() / "complexionist.ini"

    # Use provided values or fall back to env var syntax
    plex_url_value = plex_url or "${PLEX_URL}"
    plex_token_value = plex_token or "${PLEX_TOKEN}"
    tmdb_key_value = tmdb_api_key or "${TMDB_API_KEY}"
    tvdb_key_value = tvdb_api_key or "${TVDB_API_KEY}"

    default_config = f"""\
# ComPlexionist Configuration
# See: https://github.com/StephKoenig/ComPlexionist
# You can use environment variables with ${{VAR}} syntax

[plex]
# Plex server URL (e.g., http://192.168.1.100:32400)
url = {plex_url_value}
# X-Plex-Token from Plex settings
token = {plex_token_value}

[tmdb]
# TMDB API key - Get yours at: https://www.themoviedb.org/settings/api
api_key = {tmdb_key_value}

[tvdb]
# TVDB API key - Get yours at: https://thetvdb.com/api-information
api_key = {tvdb_key_value}

[options]
# Exclude unreleased movies/episodes
exclude_future = true
# Exclude Season 0 (specials)
exclude_specials = true
# Skip episodes aired within this many hours
recent_threshold_hours = 24
# Only show collections with N+ total movies
min_collection_size = 2
# Only report gaps for collections where you own N+ movies
min_owned = 2

[exclusions]
# Shows to skip (comma-separated)
shows =
# Collections to skip (comma-separated)
collections =

[paths]
# Path mapping for remote/network access (optional)
# If Plex returns paths like \\volume1\video\\... but your local machine
# accesses them as \\Storage4\video\\..., configure the mapping here:
# plex_prefix = \\volume1\video
# local_prefix = \\Storage4\video
"""

    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        f.write(default_config)

    return path


def save_default_yaml_config(path: Path | None = None) -> Path:
    """Save a default YAML config file (legacy format).

    Args:
        path: Where to save. Defaults to ~/.complexionist/config.yaml.

    Returns:
        Path to saved config file.
    """
    if path is None:
        path = get_config_dir() / "config.yaml"

    default_config = """\
# ComPlexionist Configuration (YAML format)
# See: https://github.com/StephKoenig/ComPlexionist
# Note: INI format (complexionist.cfg) is now preferred

# Plex Media Server settings
# You can use environment variables with ${VAR} syntax
plex:
  url: "${PLEX_URL}"           # e.g., http://192.168.1.100:32400
  token: "${PLEX_TOKEN}"       # X-Plex-Token from Plex settings

# TMDB (The Movie Database) API
# Get your API key at: https://www.themoviedb.org/settings/api
tmdb:
  api_key: "${TMDB_API_KEY}"

# TVDB API
# Get your API key at: https://thetvdb.com/api-information
tvdb:
  api_key: "${TVDB_API_KEY}"
  pin: ""                       # Optional subscriber PIN

# Default options (can be overridden via CLI flags)
options:
  exclude_future: true          # Exclude unreleased movies/episodes
  exclude_specials: true        # Exclude Season 0 (specials)
  recent_threshold_hours: 24    # Skip episodes aired within this many hours
  min_collection_size: 2        # Only show collections with N+ movies
  min_owned: 2                  # Only report gaps for collections you own N+ movies

# Content exclusions
exclusions:
  # Shows to skip when checking for missing episodes
  # Use exact show titles as they appear in Plex
  shows:
    # - "Daily Talk Show"
    # - "News Program"

  # Collections to skip when checking for missing movies
  collections:
    # - "Anthology Collection"
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(default_config)

    return path


def add_ignored_collection(collection_id: int) -> bool:
    """Add a collection ID to the ignore list.

    Args:
        collection_id: TMDB collection ID to ignore.

    Returns:
        True if added, False if already ignored or no config file.
    """
    config = get_config()
    if collection_id in config.tmdb.ignored_collections:
        return False

    config.tmdb.ignored_collections.append(collection_id)
    return _save_ignored_lists()


def remove_ignored_collection(collection_id: int) -> bool:
    """Remove a collection ID from the ignore list.

    Args:
        collection_id: TMDB collection ID to un-ignore.

    Returns:
        True if removed, False if not found or no config file.
    """
    config = get_config()
    if collection_id not in config.tmdb.ignored_collections:
        return False

    config.tmdb.ignored_collections.remove(collection_id)
    return _save_ignored_lists()


def add_ignored_show(show_id: int) -> bool:
    """Add a show ID to the ignore list.

    Args:
        show_id: TVDB series ID to ignore.

    Returns:
        True if added, False if already ignored or no config file.
    """
    config = get_config()
    if show_id in config.tvdb.ignored_shows:
        return False

    config.tvdb.ignored_shows.append(show_id)
    return _save_ignored_lists()


def remove_ignored_show(show_id: int) -> bool:
    """Remove a show ID from the ignore list.

    Args:
        show_id: TVDB series ID to un-ignore.

    Returns:
        True if removed, False if not found or no config file.
    """
    config = get_config()
    if show_id not in config.tvdb.ignored_shows:
        return False

    config.tvdb.ignored_shows.remove(show_id)
    return _save_ignored_lists()


def map_plex_path(path: str | None) -> str | None:
    """Map a Plex server path to the local equivalent.

    If path mapping is configured in [paths] section, replaces the plex_prefix
    with local_prefix. Otherwise returns the path unchanged.

    Handles backslash normalization for Windows UNC paths.

    Args:
        path: Path as returned by Plex server.

    Returns:
        Mapped path for local access, or original path if no mapping configured.
    """
    if not path:
        return path

    config = get_config()
    plex_prefix = config.paths.plex_prefix
    local_prefix = config.paths.local_prefix

    if not plex_prefix or not local_prefix:
        return path

    # Normalize backslashes for comparison (handle INI escaping issues)
    # Convert all backslashes to forward slashes for comparison
    path_normalized = path.replace("\\", "/")
    plex_prefix_normalized = plex_prefix.replace("\\", "/")

    if path_normalized.startswith(plex_prefix_normalized):
        # Replace the prefix, keeping original path separators
        remainder = path[len(plex_prefix) :]
        # If the remainder starts with a separator but local_prefix ends with one, avoid double
        if remainder.startswith(("\\", "/")) and local_prefix.endswith(("\\", "/")):
            remainder = remainder[1:]
        elif not remainder.startswith(("\\", "/")) and not local_prefix.endswith(("\\", "/")):
            # Add separator if needed
            remainder = "\\" + remainder if "\\" in path else "/" + remainder
        return local_prefix + remainder

    return path


def _save_ignored_lists() -> bool:
    """Save the current ignored lists to the config file.

    Updates only the ignored_collections and ignored_shows fields,
    preserving all other config values.

    Returns:
        True if saved successfully, False if no config file exists.
    """
    path = get_config_path()
    if path is None or not path.exists():
        return False

    config = get_config()

    # Read current file
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    # Update [tmdb] section with ignored_collections
    if not parser.has_section("tmdb"):
        parser.add_section("tmdb")
    ignored_collections_str = ",".join(str(id) for id in config.tmdb.ignored_collections)
    parser.set("tmdb", "ignored_collections", ignored_collections_str)

    # Update [tvdb] section with ignored_shows
    if not parser.has_section("tvdb"):
        parser.add_section("tvdb")
    ignored_shows_str = ",".join(str(id) for id in config.tvdb.ignored_shows)
    parser.set("tvdb", "ignored_shows", ignored_shows_str)

    # Write back to file
    with open(path, "w", encoding="utf-8") as f:
        parser.write(f)

    return True
