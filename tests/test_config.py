"""Tests for the configuration module."""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from complexionist.config import (
    _HAS_YAML,
    AppConfig,
    ExclusionsConfig,
    OptionsConfig,
    PlexConfig,
    TMDBConfig,
    TVDBConfig,
    _expand_env_vars,
    get_config_paths,
    load_config,
    reset_config,
    save_default_config,
)


class TestConfigModels:
    """Tests for configuration models."""

    def test_plex_config_defaults(self) -> None:
        """Test PlexConfig has correct defaults."""
        cfg = PlexConfig()
        assert cfg.url is None
        assert cfg.token is None

    def test_tmdb_config_defaults(self) -> None:
        """Test TMDBConfig has correct defaults."""
        cfg = TMDBConfig()
        assert cfg.api_key is None

    def test_tvdb_config_defaults(self) -> None:
        """Test TVDBConfig has correct defaults."""
        cfg = TVDBConfig()
        assert cfg.api_key is None

    def test_options_config_defaults(self) -> None:
        """Test OptionsConfig has correct defaults."""
        cfg = OptionsConfig()
        assert cfg.recent_threshold_hours == 24
        assert cfg.min_collection_size == 2
        assert cfg.min_owned == 2

    def test_exclusions_config_defaults(self) -> None:
        """Test ExclusionsConfig has correct defaults."""
        cfg = ExclusionsConfig()
        assert cfg.shows == []
        assert cfg.collections == []

    def test_app_config_defaults(self) -> None:
        """Test AppConfig has correct defaults."""
        cfg = AppConfig()
        assert isinstance(cfg.plex, PlexConfig)
        assert isinstance(cfg.tmdb, TMDBConfig)
        assert isinstance(cfg.tvdb, TVDBConfig)
        assert isinstance(cfg.options, OptionsConfig)
        assert isinstance(cfg.exclusions, ExclusionsConfig)


class TestEnvVarExpansion:
    """Tests for environment variable expansion."""

    def test_expand_simple_var(self) -> None:
        """Test expanding ${VAR} syntax."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            result = _expand_env_vars("prefix_${TEST_VAR}_suffix")
            assert result == "prefix_test_value_suffix"
        finally:
            del os.environ["TEST_VAR"]

    def test_expand_dollar_var(self) -> None:
        """Test expanding $VAR syntax."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            result = _expand_env_vars("prefix_$TEST_VAR")
            assert result == "prefix_test_value"
        finally:
            del os.environ["TEST_VAR"]

    def test_expand_missing_var(self) -> None:
        """Test expanding missing variable returns empty string."""
        result = _expand_env_vars("${NONEXISTENT_VAR_12345}")
        assert result == ""

    def test_expand_in_dict(self) -> None:
        """Test expanding variables in dict."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            result = _expand_env_vars({"key": "${TEST_VAR}"})
            assert result == {"key": "test_value"}
        finally:
            del os.environ["TEST_VAR"]

    def test_expand_in_list(self) -> None:
        """Test expanding variables in list."""
        os.environ["TEST_VAR"] = "test_value"
        try:
            result = _expand_env_vars(["${TEST_VAR}", "static"])
            assert result == ["test_value", "static"]
        finally:
            del os.environ["TEST_VAR"]


class TestConfigLoading:
    """Tests for configuration loading."""

    def test_load_nonexistent_file(self) -> None:
        """Test loading returns defaults when no config file exists."""
        reset_config()
        cfg = load_config(Path("/nonexistent/config.yaml"))
        assert isinstance(cfg, AppConfig)
        assert cfg.options.min_collection_size == 2

    @pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")
    def test_load_from_file(self) -> None:
        """Test loading configuration from YAML file."""
        config_content = """
options:
  min_collection_size: 5
  recent_threshold_hours: 48

exclusions:
  shows:
    - "Daily Show"
    - "News Tonight"
  collections:
    - "Anthology"
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(config_content)
            temp_path = Path(f.name)

        try:
            reset_config()
            cfg = load_config(temp_path)
            assert cfg.options.min_collection_size == 5
            assert cfg.options.recent_threshold_hours == 48
            assert "Daily Show" in cfg.exclusions.shows
            assert "News Tonight" in cfg.exclusions.shows
            assert "Anthology" in cfg.exclusions.collections
        finally:
            temp_path.unlink()

    @pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")
    def test_load_partial_config(self) -> None:
        """Test loading partial config uses defaults for missing values."""
        config_content = """
options:
  min_collection_size: 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8"
        ) as f:
            f.write(config_content)
            temp_path = Path(f.name)

        try:
            reset_config()
            cfg = load_config(temp_path)
            assert cfg.options.min_collection_size == 3
            # Default values should still be present
            assert cfg.options.recent_threshold_hours == 24
        finally:
            temp_path.unlink()

    def test_load_malformed_ini_raises_config_error(self, tmp_path: Path) -> None:
        """A malformed INI (duplicate section) raises a clean ConfigError."""
        from complexionist.errors import ConfigError

        config_path = tmp_path / "complexionist.ini"
        config_path.write_text(
            "[tmdb]\napi_key = one\n\n[tmdb]\napi_key = two\n",
            encoding="utf-8",
        )

        reset_config()
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path)

        # The message names the offending file
        assert "complexionist.ini" in str(exc_info.value)

    @pytest.mark.skipif(not _HAS_YAML, reason="PyYAML not installed")
    def test_load_invalid_values_raise_config_error(self, tmp_path: Path) -> None:
        """Values that fail model validation raise a clean ConfigError."""
        from complexionist.errors import ConfigError

        config_path = tmp_path / "config.yaml"
        config_path.write_text(
            "options:\n  min_collection_size: not-a-number\n",
            encoding="utf-8",
        )

        reset_config()
        with pytest.raises(ConfigError) as exc_info:
            load_config(config_path)

        assert "config.yaml" in str(exc_info.value)

    def test_load_ini_config(self) -> None:
        """Test loading configuration from INI file."""
        config_content = """
[plex]
url = http://192.168.1.100:32400
token = test_token

[tmdb]
api_key = tmdb_test_key

[tvdb]
api_key = tvdb_test_key

[options]
min_collection_size = 5
recent_threshold_hours = 48
min_owned = 3
# Removed key (review 2026-07 finding 15) — must be silently ignored
exclude_future = false

[exclusions]
shows = Daily Show, News Tonight
collections = Anthology
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cfg", delete=False, encoding="utf-8"
        ) as f:
            f.write(config_content)
            temp_path = Path(f.name)

        try:
            reset_config()
            cfg = load_config(temp_path)
            assert cfg.plex.url == "http://192.168.1.100:32400"
            assert cfg.plex.token == "test_token"
            assert cfg.tmdb.api_key == "tmdb_test_key"
            assert cfg.tvdb.api_key == "tvdb_test_key"
            assert cfg.options.min_collection_size == 5
            assert cfg.options.recent_threshold_hours == 48
            assert cfg.options.min_owned == 3
            # Removed keys in existing user INIs are ignored, not fatal
            assert not hasattr(cfg.options, "exclude_future")
            assert "Daily Show" in cfg.exclusions.shows
            assert "News Tonight" in cfg.exclusions.shows
            assert "Anthology" in cfg.exclusions.collections
        finally:
            temp_path.unlink()

    def test_load_ini_partial_config(self) -> None:
        """Test loading partial INI config uses defaults for missing values."""
        config_content = """
[options]
min_collection_size = 3
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".cfg", delete=False, encoding="utf-8"
        ) as f:
            f.write(config_content)
            temp_path = Path(f.name)

        try:
            reset_config()
            cfg = load_config(temp_path)
            assert cfg.options.min_collection_size == 3
            # Default values should still be present
            assert cfg.options.recent_threshold_hours == 24
            assert cfg.options.min_owned == 2
        finally:
            temp_path.unlink()


class TestConfigPaths:
    """Tests for configuration path handling."""

    def test_get_config_paths_not_empty(self) -> None:
        """Test that config paths list is not empty."""
        paths = get_config_paths()
        assert len(paths) > 0

    def test_get_config_paths_includes_cwd(self) -> None:
        """Test that config paths include current directory."""
        paths = get_config_paths()
        cwd = Path.cwd()
        assert any(p.parent == cwd for p in paths)

    def test_get_config_paths_includes_home(self) -> None:
        """Test that config paths include home directory."""
        paths = get_config_paths()
        home = Path.home()
        assert any(str(home) in str(p) for p in paths)


class TestDefaultConfig:
    """Tests for default config generation."""

    def test_save_default_config(self) -> None:
        """Test saving default INI config creates valid file."""
        import configparser

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "complexionist.cfg"
            result_path = save_default_config(config_path)

            assert result_path == config_path
            assert config_path.exists()

            # Verify it's valid INI
            parser = configparser.ConfigParser()
            parser.read(config_path)
            assert parser.has_section("plex:0")
            assert parser.has_section("tmdb")
            assert parser.has_section("tvdb")
            assert parser.has_section("options")
            assert parser.has_section("exclusions")

    def test_save_default_config_with_values(self) -> None:
        """Test saving config with actual values."""
        import configparser

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "complexionist.cfg"
            save_default_config(
                config_path,
                plex_url="http://test:32400",
                plex_token="test_token",
                tmdb_api_key="tmdb_key",
                tvdb_api_key="tvdb_key",
            )

            parser = configparser.ConfigParser()
            parser.read(config_path)
            assert parser.get("plex:0", "url") == "http://test:32400"
            assert parser.get("plex:0", "token") == "test_token"
            assert parser.get("plex:0", "name") == "Plex Server"
            assert parser.get("tmdb", "api_key") == "tmdb_key"
            assert parser.get("tvdb", "api_key") == "tvdb_key"


COMMENTED_INI = """\
# ComPlexionist Configuration
# You can use environment variables with ${VAR} syntax

[plex:0]
# Plex server (add more with [plex:1], [plex:2], etc.)
name = Main Server
url = http://localhost:32400
token = ${PLEX_TOKEN}

[tmdb]
# TMDB API key - keep this secret
api_key = tmdb-key-123
ignored_collections = 1,2

[tvdb]
; TVDB API key
api_key = tvdb-key-456

[options]
# Skip episodes aired within this many hours
recent_threshold_hours = 24
"""


class TestApplyIniUpdates:
    """Tests for the comment/raw-value-preserving INI editor (findings 1+13)."""

    def test_noop_update_returns_identical_text(self) -> None:
        from complexionist.config import _apply_ini_updates

        result = _apply_ini_updates(COMMENTED_INI, {"tmdb": {"api_key": "tmdb-key-123"}})
        assert result == COMMENTED_INI

    def test_updates_only_changed_key(self) -> None:
        from complexionist.config import _apply_ini_updates

        result = _apply_ini_updates(COMMENTED_INI, {"tmdb": {"api_key": "new-key"}})

        assert "api_key = new-key" in result
        # Everything else is untouched, comments included
        assert "# ComPlexionist Configuration" in result
        assert "# TMDB API key - keep this secret" in result
        assert "; TVDB API key" in result
        assert "token = ${PLEX_TOKEN}" in result
        assert "api_key = tvdb-key-456" in result
        # Only the one line differs
        diff = [
            (a, b)
            for a, b in zip(COMMENTED_INI.splitlines(), result.splitlines(), strict=True)
            if a != b
        ]
        assert diff == [("api_key = tmdb-key-123", "api_key = new-key")]

    def test_env_var_raw_value_preserved_when_expansion_matches(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A raw ${VAR} value expanding to the requested value is left as-is."""
        from complexionist.config import _apply_ini_updates

        monkeypatch.setenv("PLEX_TOKEN", "secret-token-xyz")

        # GUI holds the expanded token; renaming the server must not bake it in
        result = _apply_ini_updates(
            COMMENTED_INI,
            {
                "plex:0": {
                    "name": "Renamed Server",
                    "url": "http://localhost:32400",
                    "token": "secret-token-xyz",
                }
            },
        )

        assert "name = Renamed Server" in result
        assert "token = ${PLEX_TOKEN}" in result
        assert "secret-token-xyz" not in result

    def test_edited_value_replaces_env_var_reference(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A genuinely edited field gets its new literal value."""
        from complexionist.config import _apply_ini_updates

        monkeypatch.setenv("PLEX_TOKEN", "old-secret")

        result = _apply_ini_updates(COMMENTED_INI, {"plex:0": {"token": "brand-new-token"}})

        assert "token = brand-new-token" in result
        assert "${PLEX_TOKEN}" not in result

    def test_adds_missing_key_at_end_of_section(self) -> None:
        from complexionist.config import _apply_ini_updates

        result = _apply_ini_updates(COMMENTED_INI, {"tvdb": {"ignored_shows": "7,8"}})

        lines = result.splitlines()
        idx = lines.index("ignored_shows = 7,8")
        # New key lands inside [tvdb], after its existing keys, before [options]
        assert lines[idx - 1] == "api_key = tvdb-key-456"
        assert "[options]" in lines[idx + 1 :]

    def test_adds_missing_section_at_end(self) -> None:
        from complexionist.config import _apply_ini_updates

        result = _apply_ini_updates(COMMENTED_INI, {"libraries": {"movie_library": "Movies"}})

        assert result.endswith("[libraries]\nmovie_library = Movies\n")
        # Original content untouched
        assert result.startswith(COMMENTED_INI)

    def test_removes_sections(self) -> None:
        from complexionist.config import _apply_ini_updates

        result = _apply_ini_updates(COMMENTED_INI, {}, remove_sections=["plex:0"])

        assert "[plex:0]" not in result
        assert "name = Main Server" not in result
        assert "${PLEX_TOKEN}" not in result
        # Other sections and their comments survive
        assert "[tmdb]" in result
        assert "# TMDB API key - keep this secret" in result

    def test_key_matching_is_case_insensitive_and_preserves_disk_casing(self) -> None:
        from complexionist.config import _apply_ini_updates

        text = "[tmdb]\nApi_Key = old\n"
        result = _apply_ini_updates(text, {"tmdb": {"api_key": "new"}})
        assert "Api_Key = new" in result


class TestRawIniSavers:
    """save_plex_servers/_save_ignored_lists preserve raw INI content."""

    @pytest.fixture(autouse=True)
    def _reset(self) -> Iterator[None]:
        reset_config()
        yield
        reset_config()

    def _write_config(self, tmp_path: Path) -> Path:
        path = tmp_path / "complexionist.ini"
        path.write_text(COMMENTED_INI, encoding="utf-8")
        return path

    def test_server_rename_preserves_env_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from complexionist.config import PlexServerConfig, save_plex_servers

        monkeypatch.setenv("PLEX_TOKEN", "secret-token-xyz")
        path = self._write_config(tmp_path)
        load_config(path)

        assert save_plex_servers(
            [
                PlexServerConfig(
                    name="Renamed", url="http://localhost:32400", token="secret-token-xyz"
                )
            ]
        )

        content = path.read_text(encoding="utf-8")
        assert "name = Renamed" in content
        assert "token = ${PLEX_TOKEN}" in content
        assert "secret-token-xyz" not in content
        # Comments elsewhere survive
        assert "# ComPlexionist Configuration" in content
        assert "# TMDB API key - keep this secret" in content

    def test_add_server_does_not_rewrite_existing_sections(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from complexionist.config import PlexServerConfig, save_plex_servers

        monkeypatch.setenv("PLEX_TOKEN", "secret-token-xyz")
        path = self._write_config(tmp_path)
        load_config(path)

        assert save_plex_servers(
            [
                PlexServerConfig(
                    name="Main Server", url="http://localhost:32400", token="secret-token-xyz"
                ),
                PlexServerConfig(name="4K", url="http://other:32400", token="tok-2"),
            ]
        )

        content = path.read_text(encoding="utf-8")
        # First server block keeps its raw token and comment
        assert "token = ${PLEX_TOKEN}" in content
        assert "# Plex server (add more with [plex:1], [plex:2], etc.)" in content
        # New server appended
        assert "[plex:1]" in content
        assert "url = http://other:32400" in content
        assert "token = tok-2" in content

    def test_delete_server_removes_only_its_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from complexionist.config import PlexServerConfig, save_plex_servers

        monkeypatch.setenv("PLEX_TOKEN", "secret-token-xyz")
        path = tmp_path / "complexionist.ini"
        path.write_text(
            COMMENTED_INI + "\n[plex:1]\nname = 4K\nurl = http://other:32400\ntoken = tok-2\n",
            encoding="utf-8",
        )
        load_config(path)

        assert save_plex_servers(
            [
                PlexServerConfig(
                    name="Main Server", url="http://localhost:32400", token="secret-token-xyz"
                )
            ]
        )

        content = path.read_text(encoding="utf-8")
        # The [plex:1] section is gone (the comment mentioning "[plex:1]," stays)
        assert "\n[plex:1]\n" not in content
        assert "name = 4K" not in content
        assert "tok-2" not in content
        assert "token = ${PLEX_TOKEN}" in content

    def test_ignored_lists_save_preserves_comments(self, tmp_path: Path) -> None:
        from complexionist.config import add_ignored_show

        path = self._write_config(tmp_path)
        load_config(path)

        assert add_ignored_show(999)

        content = path.read_text(encoding="utf-8")
        assert "ignored_shows = 999" in content
        assert "# ComPlexionist Configuration" in content
        assert "; TVDB API key" in content
        assert "token = ${PLEX_TOKEN}" in content
        # Existing ignored_collections raw value untouched
        assert "ignored_collections = 1,2" in content
