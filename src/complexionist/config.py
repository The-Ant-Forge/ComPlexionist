"""Configuration management for ComPlexionist."""

from __future__ import annotations

import configparser
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from complexionist.errors import ConfigError

try:
    import yaml

    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

logger = logging.getLogger(__name__)


class PlexServerConfig(BaseModel):
    """Single Plex server configuration."""

    name: str = ""
    url: str = ""
    token: str = ""


class PlexConfig(BaseModel):
    """Plex server configuration (supports multiple servers)."""

    servers: list[PlexServerConfig] = Field(default_factory=list)

    @property
    def url(self) -> str | None:
        """URL of the first server (backward-compatible)."""
        return self.servers[0].url if self.servers else None

    @property
    def token(self) -> str | None:
        """Token of the first server (backward-compatible)."""
        return self.servers[0].token if self.servers else None


class TMDBConfig(BaseModel):
    """TMDB API configuration."""

    api_key: str | None = None
    ignored_collections: list[int] = Field(default_factory=list)


class TVDBConfig(BaseModel):
    """TVDB API configuration."""

    api_key: str | None = None
    ignored_shows: list[int] = Field(default_factory=list)


class OptionsConfig(BaseModel):
    """General options configuration."""

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


def is_frozen() -> bool:
    """Check if running as a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def get_exe_directory() -> Path:
    """Get the directory containing the executable (or script).

    Handles both normal Python execution and PyInstaller bundles.

    Returns:
        Path to the directory containing the exe or main script.
    """
    if is_frozen():
        return Path(sys.executable).parent
    return Path.cwd()


def get_assets_directory() -> Path:
    """Get the assets directory path.

    In PyInstaller bundles, assets are in the temp extraction dir.
    In development, they're relative to the project root.
    """
    if is_frozen():
        # PyInstaller-only attribute
        return Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]  # noqa: SLF001
    return Path(__file__).parent.parent.parent / "assets"


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

    # 4. Legacy YAML support (backwards compatibility, only if PyYAML installed)
    if _HAS_YAML:
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

    # Parse Plex server(s) — supports both old [plex] and new [plex:N] formats
    plex_servers: list[dict[str, str]] = []

    # New format: [plex:0], [plex:1], etc.
    for section in parser.sections():
        if section.startswith("plex:"):
            server: dict[str, str] = {}
            for key in ("name", "url", "token"):
                value = parser.get(section, key, fallback="")
                if value:
                    server[key] = value
            if server.get("url") or server.get("token"):
                plex_servers.append(server)

    # Old format: [plex] with url + token (backward compatibility)
    if not plex_servers and parser.has_section("plex"):
        url = parser.get("plex", "url", fallback=None)
        token = parser.get("plex", "token", fallback=None)
        if url or token:
            plex_servers.append(
                {
                    "name": "Plex Server",
                    "url": url or "",
                    "token": token or "",
                }
            )

    if plex_servers:
        config["plex"] = {"servers": plex_servers}

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
        }
        if parser.has_option("tvdb", "ignored_shows"):
            tvdb_config["ignored_shows"] = _parse_int_list(parser.get("tvdb", "ignored_shows"))
        # Remove None values but keep lists
        config["tvdb"] = {k: v for k, v in tvdb_config.items() if v is not None and v != ""}

    # Parse [options] section
    if parser.has_section("options"):
        options: dict[str, Any] = {}
        for key in [
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
        Dictionary structure matching AppConfig schema. Empty dict on error.
    """
    if not _HAS_YAML:
        logger.warning("PyYAML not installed — cannot load %s. Use INI format instead.", path)
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        logger.error("Failed to load config from %s: %s", path, e)
        return {}


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from file.

    Supports both INI (.cfg) and YAML (.yaml/.yml) formats.
    Environment variables are expanded in all values using ${VAR} syntax.

    Args:
        path: Explicit path to config file. If None, searches default locations.

    Returns:
        Loaded configuration with environment variables expanded.

    Raises:
        ConfigError: If the file cannot be parsed (e.g. duplicate sections)
            or fails validation. The message names the offending file.
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

    try:
        # Load based on file extension
        if path.suffix in (".ini", ".cfg"):
            raw_config = _load_ini_config(path)
        else:
            raw_config = _load_yaml_config(path)

        # Expand environment variables
        expanded_config = _expand_env_vars(raw_config)

        # Parse into config model
        _config = AppConfig.model_validate(expanded_config)
    except (configparser.Error, ValidationError) as e:
        raise ConfigError(f"Failed to load config from {path}: {e}") from e

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
    has_plex = bool(cfg.plex.servers and cfg.plex.servers[0].url and cfg.plex.servers[0].token)
    return bool(has_plex and cfg.tmdb.api_key and cfg.tvdb.api_key)


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
    plex_name: str = "Plex Server",
    tmdb_api_key: str = "",
    tvdb_api_key: str = "",
) -> Path:
    """Save a default INI config file.

    Args:
        path: Where to save. Defaults to ./complexionist.ini (current directory).
        plex_url: Plex server URL (optional, can use env var).
        plex_token: Plex token (optional, can use env var).
        plex_name: Plex server friendly name.
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
# See: https://github.com/The-Ant-Forge/ComPlexionist
# You can use environment variables with ${{VAR}} syntax

[plex:0]
# Plex server (add more with [plex:1], [plex:2], etc.)
name = {plex_name}
url = {plex_url_value}
token = {plex_token_value}

[tmdb]
# TMDB API key - Get yours at: https://www.themoviedb.org/settings/api
api_key = {tmdb_key_value}

[tvdb]
# TVDB API key - Get yours at: https://thetvdb.com/api-information
api_key = {tvdb_key_value}

[options]
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


# ---------------------------------------------------------------------------
# Raw INI editing (comment- and env-var-preserving)
# ---------------------------------------------------------------------------

_INI_SECTION_RE = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")
_INI_KEY_RE = re.compile(r"^(?P<key>[^\s\[#;][^=:]*?)\s*[=:]\s*(?P<value>.*)$")


def _apply_ini_updates(
    text: str,
    updates: dict[str, dict[str, str]],
    remove_sections: list[str] | None = None,
) -> str:
    """Apply targeted key updates to raw INI text.

    Unlike a configparser read->write round-trip, this preserves comments,
    blank lines, key ordering, and unexpanded ``${VAR}`` values. Only the
    requested keys are touched, and a key whose on-disk raw value already
    expands (via environment variables) to the requested value is left
    untouched — env-var indirection is never overwritten with the expanded
    secret.

    Args:
        text: Raw INI file content.
        updates: Mapping of section name -> {key: new value}. Missing keys
            are appended at the end of their section; missing sections are
            appended at the end of the file.
        remove_sections: Section names to delete entirely (header and body).

    Returns:
        The updated INI text.
    """
    remove = set(remove_sections or [])
    # Keys still to be written, per section (copied so we can pop as we go)
    pending: dict[str, dict[str, str]] = {s: dict(kv) for s, kv in updates.items()}

    out: list[str] = []
    current: str | None = None
    skipping = False  # inside a section being removed
    skip_continuations = False  # dropping continuation lines of a replaced key

    def flush_new_keys(section: str | None) -> None:
        """Append not-yet-seen keys at the end of the section just closed."""
        if section is None:
            return
        remaining = pending.pop(section, None)
        if not remaining:
            return
        # Insert before trailing blank lines so keys land inside the section
        insert_at = len(out)
        while insert_at > 0 and out[insert_at - 1].strip() == "":
            insert_at -= 1
        out[insert_at:insert_at] = [f"{key} = {value}" for key, value in remaining.items()]

    for line in text.splitlines():
        header = _INI_SECTION_RE.match(line)
        if header:
            if not skipping:
                flush_new_keys(current)
            current = header.group("name")
            skipping = current in remove
            skip_continuations = False
            if not skipping:
                out.append(line)
            continue

        if skipping:
            continue

        if skip_continuations and line[:1] in (" ", "\t") and line.strip():
            continue  # continuation line of the value we just replaced
        skip_continuations = False

        section_updates = pending.get(current) if current is not None else None
        if section_updates:
            key_match = _INI_KEY_RE.match(line)
            if key_match:
                disk_key = key_match.group("key")
                lookup = {k.lower(): k for k in section_updates}
                if disk_key.lower() in lookup:
                    new_value = section_updates.pop(lookup[disk_key.lower()])
                    raw_value = key_match.group("value")
                    if _expand_env_vars(raw_value) == new_value:
                        # Raw value (possibly ${VAR}) already yields the
                        # requested value — leave it exactly as written.
                        out.append(line)
                    else:
                        out.append(f"{disk_key} = {new_value}")
                        skip_continuations = True
                    continue

        out.append(line)

    if not skipping:
        flush_new_keys(current)

    # Sections that never appeared in the file: append them at the end
    for section, keys in pending.items():
        if not keys:
            continue
        if out and out[-1].strip() != "":
            out.append("")
        out.append(f"[{section}]")
        out.extend(f"{key} = {value}" for key, value in keys.items())

    result = "\n".join(out)
    if text.endswith("\n") and result:
        result += "\n"
    return result


def update_ini_file(
    path: Path,
    updates: dict[str, dict[str, str]],
    remove_sections: list[str] | None = None,
) -> None:
    """Update specific keys in an INI file, preserving all other raw content.

    See :func:`_apply_ini_updates` for the exact semantics. Skips the write
    entirely when nothing would change.

    Args:
        path: INI file to update (must exist).
        updates: Mapping of section name -> {key: new value}.
        remove_sections: Section names to delete entirely.
    """
    text = path.read_text(encoding="utf-8")
    new_text = _apply_ini_updates(text, updates, remove_sections)
    if new_text != text:
        path.write_text(new_text, encoding="utf-8")


def save_plex_servers(servers: list[PlexServerConfig]) -> bool:
    """Save the full Plex server list to the INI config file.

    Uses the raw INI update path: comments, ordering, and unexpanded
    ``${VAR}`` values are preserved, and only fields whose values actually
    changed are rewritten. Plex sections beyond the new server count (and
    any legacy [plex] section) are removed.

    Args:
        servers: List of PlexServerConfig to save.

    Returns:
        True if saved successfully, False if no config file exists.
    """
    path = get_config_path()
    if path is None or not path.exists():
        return False

    text = path.read_text(encoding="utf-8")
    existing = re.findall(r"^\[(plex(?::[^\]]*)?)\]", text, flags=re.MULTILINE)

    updates: dict[str, dict[str, str]] = {
        f"plex:{i}": {"name": server.name, "url": server.url, "token": server.token}
        for i, server in enumerate(servers)
    }
    stale = [section for section in existing if section not in updates]

    update_ini_file(path, updates, remove_sections=stale)

    # Reset cached config so it reloads with new values
    reset_config()

    # Update in-memory config
    global _config
    _config = load_config(path)

    return True


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

    Updates only the ignored_collections and ignored_shows keys via the raw
    INI update path — comments and all other raw values are preserved.

    Returns:
        True if saved successfully, False if no config file exists.
    """
    path = get_config_path()
    if path is None or not path.exists():
        return False

    config = get_config()

    update_ini_file(
        path,
        {
            "tmdb": {
                "ignored_collections": ",".join(str(id) for id in config.tmdb.ignored_collections)
            },
            "tvdb": {"ignored_shows": ",".join(str(id) for id in config.tvdb.ignored_shows)},
        },
    )

    return True
