import difflib
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pathspec
from rich.text import Text

from ..config import Config
from .interfaces import FileServiceError, IFileService

if TYPE_CHECKING:
    from ..config import Config


class FileService(IFileService):
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
        self._project_root: Path = config.project_root
        self.ignore_patterns: set[str] = set(self.config.default_ignore_patterns)
        self.ignore_patterns.update(self.config.ignore_patterns)
        self.pathspec: pathspec.PathSpec | None = self._load_pathspec()

    @property
    def project_root(self) -> Path:
        """Get the project root directory."""
        return self._project_root

    def _load_pathspec(self) -> pathspec.PathSpec | None:
        """Load pathspec from .gitignore file."""
        if not self.config.include_gitignore:
            return None

        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            return None

        try:
            with open(gitignore_path, encoding="utf-8") as f:
                lines = f.readlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", lines)
        except Exception as e:
            raise FileServiceError(
                f"Failed to load .gitignore for pathspec: {str(e)}",
                service_name="FileService",
            ) from e

    def is_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            True if the path should be ignored, False otherwise
        """
        # Check against default and custom patterns first
        if any(part in self.ignore_patterns for part in path.parts):
            return True

        # Check against .gitignore patterns using pathspec
        if self.pathspec:
            try:
                # pathspec works with relative paths
                relative_path = path.relative_to(self.project_root)
                return self.pathspec.match_file(str(relative_path))
            except ValueError:
                # This can happen if the path is not within the project root,
                # which shouldn't occur with the current file discovery logic.
                return False

        return False

    def get_project_files(self, root: Path | None = None) -> list[Path]:
        """Get all files under a root that aren't ignored.

        Args:
            root: Optional root directory to scan. Defaults to configured
                `project_root`.

        Returns:
            List of absolute `Path`s for files that pass ignore filters.

        Raises:
            FileServiceError: If file discovery fails
        """
        try:
            files: list[Path] = []

            scan_root = root or self.project_root

            all_files = [
                Path(root_path) / filename
                for root_path, _, filenames in os.walk(scan_root)
                for filename in filenames
            ]

            # Filter ignored files
            files = [
                file_path for file_path in all_files if not self.is_ignored(file_path)
            ]

            return files
        except Exception as e:
            raise FileServiceError(
                f"Failed to get project files: {str(e)}", service_name="FileService"
            ) from e

    def read_file_content(self, file_path: Path) -> str | None:
        """Read file content, return None if it exceeds size limit or doesn't exist.

        Args:
            file_path: Path to the file to read

        Returns:
            File content as string, or None if file is too large or unreadable

        Raises:
            FileServiceError: If file reading fails unexpectedly
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return None

            # Check file size before reading
            file_size = file_path.stat().st_size
            if file_size > self.config.max_file_size:
                return None

            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                return content
        except (UnicodeDecodeError, OSError):
            # Skip binary/unreadable files
            return None
        except Exception as e:
            raise FileServiceError(
                f"Failed to read file '{file_path}': {str(e)}",
                service_name="FileService",
            ) from e

    @staticmethod
    def generate_diff(old_content: str, new_content: str) -> str:
        """
        Generate a unified diff between two content strings with dual line numbers.

        Args:
            old_content: The original content to compare
            new_content: The new content to compare against

        Returns:
            Unified diff string showing changes between the two contents
        """
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile="old",
            tofile="new",
        )
        return "".join(diff)

    @staticmethod
    def generate_diff_rich(old_content: str, new_content: str) -> Text:
        """
        Generate a rich Text diff between two content strings with color formatting.

        Args:
            old_content: The original content to compare
            new_content: The new content to compare against

        Returns:
            Rich Text object with color-coded diff lines
        """
        diff_lines = difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile="old",
            tofile="new",
            lineterm="",
        )

        diff_text = Text()
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                diff_text.append(line + "\n", style="green")
            elif line.startswith("-") and not line.startswith("---"):
                diff_text.append(line + "\n", style="red")
            elif (
                line.startswith("@@")
                or line.startswith("---")
                or line.startswith("+++")
            ):
                diff_text.append(line + "\n", style="cyan")
            else:
                diff_text.append(line + "\n")

        return diff_text
