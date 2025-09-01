import logging
from pathlib import Path

from codesnap.config import Config


class TestConfig:
    """Test cases for the Config class."""

    def test_config_creation_with_defaults(self):
        """Test config creation with default values."""
        config = Config()
        assert isinstance(config.project_root, Path)
        assert config.ignore_patterns == set()
        assert ".git" in config.default_ignore_patterns
        assert "__pycache__" in config.default_ignore_patterns
        assert ".codesnap" in config.default_ignore_patterns
        assert config.log_level == logging.INFO
        assert config.include_gitignore is True

    def test_config_with_custom_project_root(self):
        """Test config with custom project root."""
        custom_root = Path("/custom/path")
        config = Config(project_root=custom_root)
        assert config.project_root == custom_root

    def test_config_with_custom_ignore_patterns(self):
        """Test config with custom ignore patterns."""
        custom_patterns = {"*.tmp", "*.log"}
        config = Config(ignore_patterns=custom_patterns)
        assert config.ignore_patterns == custom_patterns

    def test_config_with_custom_default_ignore_patterns(self):
        """Test config with custom default ignore patterns."""
        custom_defaults = {"custom1", "custom2"}
        config = Config(default_ignore_patterns=custom_defaults)
        assert config.default_ignore_patterns == custom_defaults

    def test_config_with_custom_log_level(self):
        """Test config with custom log level."""
        config = Config(log_level=logging.DEBUG)
        assert config.log_level == logging.DEBUG

    def test_config_with_gitignore_disabled(self):
        """Test config with gitignore disabled."""
        config = Config(include_gitignore=False)
        assert config.include_gitignore is False

    def test_config_project_root_defaults_to_cwd(self):
        """Test that project root defaults to current working directory."""
        config = Config()
        assert config.project_root == Path.cwd()

    def test_config_all_parameters_combined(self):
        """Test config with all parameters specified."""
        custom_root = Path("/test/path")
        custom_ignore = {"*.tmp"}
        custom_defaults = {"custom1"}

        config = Config(
            project_root=custom_root,
            ignore_patterns=custom_ignore,
            default_ignore_patterns=custom_defaults,
            log_level=logging.WARNING,
            include_gitignore=False,
        )

        assert config.project_root == custom_root
        assert config.ignore_patterns == custom_ignore
        assert config.default_ignore_patterns == custom_defaults
        assert config.log_level == logging.WARNING
        assert config.include_gitignore is False

    def test_config_default_ignore_patterns_contains_common_patterns(self):
        """Test that default ignore patterns contain common development patterns."""
        config = Config()
        expected_patterns = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".codesnap",
            ".venv",
            "venv",
            "env",
            ".mypy_cache",
        }

        for pattern in expected_patterns:
            assert pattern in config.default_ignore_patterns
