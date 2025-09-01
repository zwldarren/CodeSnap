import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Config:
    """
    Configuration class for CodeSnap system.

    This class provides customizable settings for the CodeSnap checkpoint system,
    including file handling, logging, and diff generation preferences.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        ignore_patterns: set[str] | None = None,
        default_ignore_patterns: set[str] | None = None,
        log_level: int = logging.INFO,
        include_gitignore: bool = True,
    ):
        """
        Initialize configuration for CodeSnap.

        Args:
            project_root: Root directory of the project. If None and
                auto_detect_project_root is True, attempts to detect project root.
            ignore_patterns: Custom ignore patterns to use in addition to defaults.
            default_ignore_patterns: Base ignore patterns. If not provided, uses
                common patterns.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                Default: INFO.
            include_gitignore: Whether to include patterns from .gitignore file.
                Default: True.
        """
        self.project_root: Path = project_root or Path.cwd()
        self.ignore_patterns: set[str] = ignore_patterns or set()
        self.default_ignore_patterns: set[str] = default_ignore_patterns or {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".codesnap",
            ".venv",
            "venv",
            "env",
            ".mypy_cache",
            ".ruff_cache",
        }
        self.log_level: int = log_level
        self.include_gitignore: bool = include_gitignore
        self.max_file_size: int = 10 * 1024 * 1024

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(log_level)
