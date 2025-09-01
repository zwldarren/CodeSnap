import difflib
import os
from pathlib import Path

from rich.text import Text

from ..config import Config


class FileService:
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
                with open(gitignore_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        # Skip comments and empty lines
                        if line and not line.startswith("#"):
                            # Remove trailing slashes for directories
                            if line.endswith("/"):
                                line = line[:-1]
                            patterns.add(line)

        return patterns

    def is_ignored(self, path: Path) -> bool:
        """Check if a path should be ignored."""
        # Check if any part of the path matches ignore patterns
        return any(part in self.ignore_patterns for part in path.parts)

    def get_project_files(self) -> list[Path]:
        """Get all files in the project that aren't ignored."""
        files = []

        for root, dirs, filenames in os.walk(self.project_root):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignore_patterns]

            for filename in filenames:
                file_path = Path(root) / filename
                if not self.is_ignored(file_path):
                    files.append(file_path)

        return files

    def read_file_content(self, file_path: Path) -> str | None:
        """Read file content, return None if it exceeds size limit or doesn't exist."""
        # Check file size before reading
        file_size = file_path.stat().st_size
        if file_size > self.config.max_file_size:
            return None

        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            return content

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
            old_content.splitlines(), new_content.splitlines()
        )

        diff_text = Text()
        for line in diff_lines:
            if line.startswith("+"):
                diff_text.append(line + "\n", style="green")
            elif line.startswith("-"):
                diff_text.append(line + "\n", style="red")
            elif line.startswith("@@"):
                diff_text.append(line, style="cyan")
            else:
                diff_text.append(line + "\n")

        return diff_text
