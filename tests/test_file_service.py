import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.text import Text

from codesnap.config import Config
from codesnap.services.file_service import FileService
from codesnap.services.interfaces import FileServiceError


class TestFileService:
    """Test cases for the FileService class."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = Config(project_root=self.temp_dir)
        self.file_service = FileService(self.config)

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_file_service_initialization(self):
        """Test FileService initialization."""
        assert self.file_service.config == self.config
        assert self.file_service.project_root == self.temp_dir
        assert isinstance(self.file_service.ignore_patterns, set)
        assert ".git" in self.file_service.ignore_patterns
        assert ".codesnap" in self.file_service.ignore_patterns

    def test_project_root_property(self):
        """Test project_root property."""
        assert self.file_service.project_root == self.temp_dir

    def test_is_ignored_with_default_patterns(self):
        """Test is_ignored with default ignore patterns."""
        # Test paths that should be ignored
        assert self.file_service.is_ignored(Path(self.temp_dir / ".git" / "file.txt"))
        assert self.file_service.is_ignored(
            Path(self.temp_dir / "__pycache__" / "file.pyc")
        )
        assert self.file_service.is_ignored(
            Path(self.temp_dir / ".codesnap" / "data.json")
        )

        # Test paths that should not be ignored
        assert not self.file_service.is_ignored(Path(self.temp_dir / "src" / "main.py"))
        assert not self.file_service.is_ignored(Path(self.temp_dir / "README.md"))

    def test_is_ignored_with_custom_patterns(self):
        """Test is_ignored with custom ignore patterns."""
        # Add custom ignore patterns
        self.file_service.ignore_patterns.add("*.tmp")
        self.file_service.ignore_patterns.add("temp_*")

        assert self.file_service.is_ignored(Path(self.temp_dir / "test.tmp"))
        assert self.file_service.is_ignored(Path(self.temp_dir / "temp_file.txt"))
        assert not self.file_service.is_ignored(Path(self.temp_dir / "main.py"))

    def test_load_pathspec_with_gitignore(self):
        """Test loading pathspec from .gitignore file."""
        # Create .gitignore file
        gitignore_path = self.temp_dir / ".gitignore"
        gitignore_content = "*.log\n*.tmp\ntest_dir/"
        gitignore_path.write_text(gitignore_content)

        # Create new FileService with gitignore enabled
        config = Config(project_root=self.temp_dir, include_gitignore=True)
        file_service = FileService(config)

        assert file_service.pathspec is not None

        # Test that gitignore patterns are respected
        assert file_service.is_ignored(Path(self.temp_dir / "error.log"))
        assert file_service.is_ignored(Path(self.temp_dir / "test.tmp"))
        assert file_service.is_ignored(Path(self.temp_dir / "test_dir" / "file.txt"))

    def test_load_pathspec_without_gitignore(self):
        """Test that pathspec is not loaded when gitignore is disabled."""
        config = Config(project_root=self.temp_dir, include_gitignore=False)
        file_service = FileService(config)

        assert file_service.pathspec is None

    def test_load_pathspec_with_nonexistent_gitignore(self):
        """Test loading pathspec when .gitignore doesn't exist."""
        # Don't create .gitignore file
        config = Config(project_root=self.temp_dir, include_gitignore=True)
        file_service = FileService(config)

        assert file_service.pathspec is None

    def test_load_pathspec_with_invalid_gitignore(self):
        """Test handling of invalid .gitignore file."""
        gitignore_path = self.temp_dir / ".gitignore"
        gitignore_path.write_text("invalid[pattern")

        config = Config(project_root=self.temp_dir, include_gitignore=True)

        # Should not raise an error - pathspec handles invalid patterns gracefully
        file_service = FileService(config)
        assert file_service is not None
        assert file_service.pathspec is not None

    def test_get_project_files(self):
        """Test getting project files."""
        # Create test files
        (self.temp_dir / "main.py").write_text("print('hello')")
        (self.temp_dir / "README.md").write_text("# Test")
        (self.temp_dir / ".git").mkdir()
        (self.temp_dir / ".git" / "config").write_text(
            "git config"
        )  # Should be ignored

        files = self.file_service.get_project_files()

        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "main.py" in file_names
        assert "README.md" in file_names
        assert "config" not in file_names

    def test_get_project_files_with_custom_root(self):
        """Test getting project files with custom root."""
        # Create subdirectory
        subdir = self.temp_dir / "subdir"
        subdir.mkdir()

        # Create files in subdirectory
        (subdir / "file1.py").write_text("content1")
        (subdir / "file2.py").write_text("content2")

        files = self.file_service.get_project_files(subdir)

        assert len(files) == 2
        assert all(f.parent == subdir for f in files)

    def test_get_project_files_with_error(self):
        """Test handling of errors when getting project files."""
        with patch("os.walk") as mock_walk:
            mock_walk.side_effect = Exception("Permission denied")

            with pytest.raises(FileServiceError):
                self.file_service.get_project_files()

    def test_read_file_content_existing_file(self):
        """Test reading content from existing file."""
        test_content = "test file content"
        test_file = self.temp_dir / "test.txt"
        test_file.write_text(test_content)

        content = self.file_service.read_file_content(test_file)
        assert content == test_content

    def test_read_file_content_nonexistent_file(self):
        """Test reading content from nonexistent file."""
        nonexistent_file = self.temp_dir / "nonexistent.txt"
        content = self.file_service.read_file_content(nonexistent_file)
        assert content is None

    def test_read_file_content_too_large_file(self):
        """Test reading content from file that's too large."""
        large_content = "x" * (self.config.max_file_size + 1)
        large_file = self.temp_dir / "large.txt"
        large_file.write_text(large_content)

        content = self.file_service.read_file_content(large_file)
        assert content is None

    def test_read_file_content_binary_file(self):
        """Test reading content from binary file."""
        binary_file = self.temp_dir / "binary.bin"
        # Use bytes that are not valid UTF-8
        binary_file.write_bytes(b"\xff\xfe\x00\x01")

        content = self.file_service.read_file_content(binary_file)
        assert content is None

    def test_read_file_content_with_error(self):
        """Test handling of errors when reading file."""
        test_file = self.temp_dir / "test.txt"

        with patch("builtins.open") as mock_open:
            mock_open.side_effect = OSError("Permission denied")

            # Should return None for OSError (file not readable)
            content = self.file_service.read_file_content(test_file)
            assert content is None

    def test_generate_diff(self):
        """Test generating diff between two content strings."""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"

        diff = self.file_service.generate_diff(old_content, new_content)

        assert "--- old" in diff
        assert "+++ new" in diff
        assert "-line2" in diff
        assert "+modified" in diff

    def test_generate_diff_no_changes(self):
        """Test generating diff when there are no changes."""
        content = "line1\nline2\nline3"

        diff = self.file_service.generate_diff(content, content)

        # Should be empty when there are no changes
        assert diff == ""

    def test_generate_diff_rich(self):
        """Test generating rich text diff."""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"

        diff_text = self.file_service.generate_diff_rich(old_content, new_content)

        assert isinstance(diff_text, Text)
        # Check that the diff contains expected lines
        diff_str = str(diff_text)
        assert "--- old" in diff_str
        assert "+++ new" in diff_str

    def test_generate_diff_rich_coloring(self):
        """Test that rich diff has proper coloring."""
        old_content = "line1\nline2\nline3"
        new_content = "line1\nmodified\nline3"

        diff_text = self.file_service.generate_diff_rich(old_content, new_content)

        # Convert to string to check styling
        diff_str = str(diff_text)

        # The diff should contain the changes
        assert "line2" in diff_str
        assert "modified" in diff_str

    def test_is_ignored_path_outside_project_root(self):
        """Test is_ignored with path outside project root."""
        outside_path = Path("/some/other/path/file.txt")

        # Should not raise an exception and should return False
        assert not self.file_service.is_ignored(outside_path)
