import logging
import os
from pathlib import Path

from .config import Config

logger = logging.getLogger(__name__)


class FileSystemManager:
    """
    Manages file system operations for the checkpoint system.

    Handles file discovery, reading, and filtering based on ignore patterns.
    This class is responsible for interacting with the project's file system
    while respecting configuration settings like ignore patterns and file size limits.
    """

    def __init__(self, config: Config):
        """
        Initialize the file system manager.

        Args:
            config: Configuration object containing file system settings
        """
        self.config: Config = config
        self.project_root: Path = config.project_root
        self.ignore_patterns: set[str] = self._load_ignore_patterns()

    def _load_ignore_patterns(self) -> set[str]:
        """Load ignore patterns from configuration and .gitignore file."""
        patterns = set(self.config.default_ignore_patterns)
        patterns.update(self.config.ignore_patterns)

        # Try to load .gitignore if configured
        if self.config.include_gitignore:
            gitignore_path = self.project_root / ".gitignore"
            if gitignore_path.exists():
                try:
                    with open(gitignore_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            # Skip comments and empty lines
                            if line and not line.startswith("#"):
                                # Remove trailing slashes for directories
                                if line.endswith("/"):
                                    line = line[:-1]
                                patterns.add(line)
                    logger.debug(f"Loaded ignore patterns from {gitignore_path}")
                except (UnicodeDecodeError, FileNotFoundError) as e:
                    logger.warning(f"Failed to load .gitignore: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading .gitignore: {e}")

        logger.debug(f"Ignore patterns: {patterns}")
        return patterns

    def is_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        # Check if any part of the path matches ignore patterns
        for part in path.parts:
            if part in self.ignore_patterns:
                logger.debug(f"Ignored path: {path} (matched pattern: {part})")
                return True
        return False

    def get_project_files(self) -> list[Path]:
        """Get all files in the project that aren't ignored."""
        files = []
        try:
            for root, dirs, filenames in os.walk(self.project_root):
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if d not in self.ignore_patterns]

                for filename in filenames:
                    file_path = Path(root) / filename
                    if not self.is_ignored(file_path):
                        files.append(file_path)
            logger.debug(f"Found {len(files)} project files")
        except Exception as e:
            logger.error(f"Error walking project directory: {e}")
            raise

        return files

    def read_file_content(self, file_path: Path) -> str | None:
        """Read file content, return None if it exceeds size limit or doesn't exist."""
        try:
            # Check file size before reading
            file_size = file_path.stat().st_size
            if file_size > self.config.max_file_size:
                logger.warning(
                    f"File {file_path} exceeds size limit "
                    f"({file_size} > {self.config.max_file_size} bytes)"
                )
                return None

            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                logger.debug(f"Read file: {file_path} (size: {len(content)} bytes)")
                return content
        except (UnicodeDecodeError, FileNotFoundError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading file {file_path}: {e}")
            return None
