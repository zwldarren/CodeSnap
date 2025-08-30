import logging
from pathlib import Path


class Config:
    """
    Configuration class for CodeSnap system.

    This class provides customizable settings for the CodeSnap checkpoint system,
    including file handling, logging, and diff generation preferences.

    Example:
        ```python
        # Custom configuration
        config = Config(
            project_root=Path("/my/project"),
            ignore_patterns={"temp", "build"},
            log_level=logging.DEBUG,
            max_file_size=5 * 1024 * 1024,  # 5MB
        )
        ```
    """

    def __init__(
        self,
        project_root: Path | None = None,
        ignore_patterns: set[str] | None = None,
        default_ignore_patterns: set[str] | None = None,
        log_level: int = logging.INFO,
        enable_rich_diff: bool = True,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
        include_gitignore: bool = True,
    ):
        """
        Initialize configuration for CodeSnap.

        Args:
            project_root: Root directory of the project. Defaults to current
                working directory.
            ignore_patterns: Custom ignore patterns to use in addition to defaults.
            default_ignore_patterns: Base ignore patterns. If not provided, uses
                common patterns.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                Default: INFO.
            enable_rich_diff: Whether to enable rich diff formatting with colors.
                Default: True.
            max_file_size: Maximum file size to process in bytes. Default: 10MB.
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
        }
        self.log_level: int = log_level
        self.enable_rich_diff: bool = enable_rich_diff
        self.max_file_size: int = max_file_size
        self.include_gitignore: bool = include_gitignore

        # Configure logging
        logging.basicConfig(level=log_level)
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
