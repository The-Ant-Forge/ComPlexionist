"""Tests for the configuration module."""

import os
import tempfile
from pathlib import Path

from complexionist.config import (
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
        assert cfg.pin is None

    def test_options_config_defaults(self) -> None:
        """Test OptionsConfig has correct defaults."""
        cfg = OptionsConfig()
        assert cfg.exclude_future is True
        assert cfg.exclude_specials is True
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
            assert cfg.options.exclude_future is True
        finally:
            temp_path.unlink()

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
            assert cfg.options.exclude_future is False
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
            assert cfg.options.exclude_future is True
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
