import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from codesnap.models import Checkpoint
from codesnap.services.comparison_service import ComparisonService
from codesnap.services.interfaces import ComparisonError, IFileService, IStorageManager


class TestComparisonService:
    """Test cases for the ComparisonService class."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_storage = Mock(spec=IStorageManager)
        self.mock_file_service = Mock(spec=IFileService)
        self.mock_file_service.project_root = self.temp_dir
        self.comparison_service = ComparisonService(
            self.mock_storage, self.mock_file_service
        )

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_comparison_service_initialization(self):
        """Test ComparisonService initialization."""
        assert self.comparison_service.storage == self.mock_storage
        assert self.comparison_service.file_system == self.mock_file_service

    def test_compare_checkpoints_basic(self):
        """Test basic checkpoint comparison."""
        # Setup mock checkpoints
        checkpoint1 = Checkpoint(
            id=1, file_snapshots={"file1.py": "hash1", "file2.py": "hash2"}
        )
        checkpoint2 = Checkpoint(
            id=2,
            file_snapshots={
                "file1.py": "hash1",
                "file2.py": "hash3",
                "file3.py": "hash4",
            },
        )

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        # Set up mock to return consistent content for same hashes
        hash_content_map = {
            "hash1": "content1",
            "hash2": "content2",
            "hash3": "content3",
            "hash4": "content4",
        }

        def mock_load_file_snapshot(hash_value):
            return hash_content_map.get(hash_value)

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Compare checkpoints
        changes = self.comparison_service.compare_checkpoints(1, 2)

        # Verify changes
        assert len(changes) == 2

        # Find file2.py change (modified)
        file2_change = next(c for c in changes if c.file_path == "file2.py")
        assert file2_change.change_type == "modified"
        assert file2_change.old_content == "content2"
        assert file2_change.new_content == "content3"

        # Find file3.py change (added)
        file3_change = next(c for c in changes if c.file_path == "file3.py")
        assert file3_change.change_type == "added"
        assert file3_change.old_content is None
        assert file3_change.new_content == "content4"

    def test_compare_checkpoints_with_rich(self):
        """Test checkpoint comparison with rich output."""
        # Setup mock checkpoints
        checkpoint1 = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})
        checkpoint2 = Checkpoint(id=2, file_snapshots={"file1.py": "hash2"})

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "old content"
            elif hash_value == "hash2":
                return "new content"
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Mock rich diff generation
        mock_diff = Mock()
        self.mock_file_service.generate_diff_rich.return_value = mock_diff

        # Compare checkpoints with rich output
        changes = self.comparison_service.compare_checkpoints(1, 2, use_rich=True)

        # Verify changes
        assert len(changes) == 1
        assert changes[0].file_path == "file1.py"
        assert changes[0].change_type == "modified"
        assert changes[0].diff == mock_diff

    def test_compare_checkpoints_file_removed(self):
        """Test checkpoint comparison when file is removed."""
        # Setup mock checkpoints
        checkpoint1 = Checkpoint(
            id=1, file_snapshots={"file1.py": "hash1", "file2.py": "hash2"}
        )
        checkpoint2 = Checkpoint(
            id=2,
            file_snapshots={"file1.py": "hash1"},  # file2.py removed
        )

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "content1"
            elif hash_value == "hash2":
                return "content2"
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Compare checkpoints
        changes = self.comparison_service.compare_checkpoints(1, 2)

        # Verify changes
        assert len(changes) == 1
        assert changes[0].file_path == "file2.py"
        assert changes[0].change_type == "deleted"
        assert changes[0].old_content == "content2"
        assert changes[0].new_content is None

    def test_compare_checkpoints_no_changes(self):
        """Test checkpoint comparison when there are no changes."""
        # Setup mock checkpoints
        checkpoint1 = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})
        checkpoint2 = Checkpoint(
            id=2,
            file_snapshots={"file1.py": "hash1"},  # Same file
        )

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "content1"
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Compare checkpoints
        changes = self.comparison_service.compare_checkpoints(1, 2)

        # Verify no changes
        assert len(changes) == 0

    def test_compare_checkpoints_nonexistent_checkpoint(self):
        """Test checkpoint comparison with nonexistent checkpoint."""
        self.mock_storage.load_checkpoint.side_effect = [None, None]

        # Should raise ComparisonError
        with pytest.raises(ComparisonError):
            self.comparison_service.compare_checkpoints(1, 2)

    def test_compare_checkpoints_one_nonexistent_checkpoint(self):
        """Test checkpoint comparison when one checkpoint doesn't exist."""
        checkpoint1 = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, None]

        # Should raise ComparisonError
        with pytest.raises(ComparisonError):
            self.comparison_service.compare_checkpoints(1, 2)

    def test_compare_checkpoints_file_snapshot_error(self):
        """Test checkpoint comparison when file snapshot loading fails."""
        checkpoint1 = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})
        checkpoint2 = Checkpoint(id=2, file_snapshots={"file1.py": "hash2"})

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "content1"
            elif hash_value == "hash2":
                raise Exception("Failed to load snapshot")
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Should raise ComparisonError
        with pytest.raises(ComparisonError):
            self.comparison_service.compare_checkpoints(1, 2)

    def test_compare_with_current_basic(self):
        """Test comparing checkpoint with current state."""
        # Setup mock checkpoint
        checkpoint = Checkpoint(
            id=1, file_snapshots={"file1.py": "hash1", "file2.py": "hash2"}
        )

        self.mock_storage.load_checkpoint.return_value = checkpoint

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "old_content"
            elif hash_value == "hash2":
                return "old_content2"
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot
        self.mock_file_service.get_project_files.return_value = [
            self.temp_dir / "file1.py",
            self.temp_dir / "file3.py",
        ]

        def mock_read_file_content(file_path):
            if file_path.name == "file1.py":
                return "new_content"
            elif file_path.name == "file3.py":
                return "new_content3"
            else:
                return None

        self.mock_file_service.read_file_content.side_effect = mock_read_file_content

        # Compare with current
        changes = self.comparison_service.compare_with_current(1)

        # Verify changes
        assert len(changes) == 3

        # Find file1.py change (modified)
        file1_change = next(c for c in changes if c.file_path == "file1.py")
        assert file1_change.change_type == "modified"
        assert file1_change.old_content == "old_content"
        assert file1_change.new_content == "new_content"

        # Find file2.py change (deleted)
        file2_change = next(c for c in changes if c.file_path == "file2.py")
        assert file2_change.change_type == "deleted"
        assert file2_change.old_content == "old_content2"
        assert file2_change.new_content is None

        # Find file3.py change (added)
        file3_change = next(c for c in changes if c.file_path == "file3.py")
        assert file3_change.change_type == "added"
        assert file3_change.old_content is None
        assert file3_change.new_content == "new_content3"

    def test_compare_with_current_with_rich(self):
        """Test comparing checkpoint with current state using rich output."""
        # Setup mock checkpoint
        checkpoint = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})

        self.mock_storage.load_checkpoint.return_value = checkpoint
        self.mock_storage.load_file_snapshot.return_value = "old_content"
        self.mock_file_service.get_project_files.return_value = [
            self.temp_dir / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "new_content"

        # Mock rich diff generation
        mock_diff = Mock()
        self.mock_file_service.generate_diff_rich.return_value = mock_diff

        # Compare with current
        changes = self.comparison_service.compare_with_current(1, use_rich=True)

        # Verify changes
        assert len(changes) == 1
        assert changes[0].file_path == "file1.py"
        assert changes[0].change_type == "modified"
        assert changes[0].diff == mock_diff

    def test_compare_with_current_nonexistent_checkpoint(self):
        """Test comparing nonexistent checkpoint with current state."""
        self.mock_storage.load_checkpoint.return_value = None

        # Should raise ComparisonError
        with pytest.raises(ComparisonError):
            self.comparison_service.compare_with_current(1)

    def test_compare_with_current_file_service_error(self):
        """Test comparing with current when file service fails."""
        checkpoint = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})

        self.mock_storage.load_checkpoint.return_value = checkpoint
        self.mock_storage.load_file_snapshot.return_value = "old_content"
        self.mock_file_service.get_project_files.side_effect = Exception(
            "File service error"
        )

        # Should raise ComparisonError
        with pytest.raises(ComparisonError):
            self.comparison_service.compare_with_current(1)

    def test_compare_with_current_unreadable_current_file(self):
        """Test comparing with current when current file is unreadable."""
        checkpoint = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})

        self.mock_storage.load_checkpoint.return_value = checkpoint
        self.mock_storage.load_file_snapshot.return_value = "old_content"
        self.mock_file_service.get_project_files.return_value = [
            self.temp_dir / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = None  # Unreadable

        # Should still work, treating unreadable file as deleted
        changes = self.comparison_service.compare_with_current(1)

        assert len(changes) == 1
        assert changes[0].file_path == "file1.py"
        assert changes[0].change_type == "deleted"
        assert changes[0].old_content == "old_content"
        assert changes[0].new_content is None

    def test_compare_checkpoints_complex_scenario(self):
        """Test checkpoint comparison with complex scenario."""
        # Setup mock checkpoints with multiple changes
        checkpoint1 = Checkpoint(
            id=1,
            file_snapshots={
                "file1.py": "hash1",
                "file2.py": "hash2",
                "file3.py": "hash3",
                "file4.py": "hash4",
            },
        )
        checkpoint2 = Checkpoint(
            id=2,
            file_snapshots={
                "file1.py": "hash1_modified",  # modified
                "file3.py": "hash3",  # unchanged
                "file5.py": "hash5",  # added
                # file2.py removed, file4.py removed
            },
        )

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        hash_content_map = {
            "hash1": "content1",
            "hash2": "content2",
            "hash3": "content3",
            "hash4": "content4",
            "hash1_modified": "content1_modified",
            "hash5": "content5",
        }

        def mock_load_file_snapshot(hash_value):
            return hash_content_map.get(hash_value)

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot

        # Compare checkpoints
        changes = self.comparison_service.compare_checkpoints(1, 2)

        # Verify changes
        assert len(changes) == 4

        # Check each change type
        changes_by_file = {c.file_path: c for c in changes}

        # file1.py - modified
        assert changes_by_file["file1.py"].change_type == "modified"
        assert changes_by_file["file1.py"].old_content == "content1"
        assert changes_by_file["file1.py"].new_content == "content1_modified"

        # file2.py - deleted
        assert changes_by_file["file2.py"].change_type == "deleted"
        assert changes_by_file["file2.py"].old_content == "content2"
        assert changes_by_file["file2.py"].new_content is None

        # file4.py - deleted
        assert changes_by_file["file4.py"].change_type == "deleted"
        assert changes_by_file["file4.py"].old_content == "content4"
        assert changes_by_file["file4.py"].new_content is None

        # file5.py - added
        assert changes_by_file["file5.py"].change_type == "added"
        assert changes_by_file["file5.py"].old_content is None
        assert changes_by_file["file5.py"].new_content == "content5"

    def test_generate_diff_calls(self):
        """Test that diff generation methods are called correctly."""
        checkpoint1 = Checkpoint(id=1, file_snapshots={"file1.py": "hash1"})
        checkpoint2 = Checkpoint(id=2, file_snapshots={"file1.py": "hash2"})

        self.mock_storage.load_checkpoint.side_effect = [checkpoint1, checkpoint2]

        def mock_load_file_snapshot(hash_value):
            if hash_value == "hash1":
                return "old"
            elif hash_value == "hash2":
                return "new"
            else:
                return None

        self.mock_storage.load_file_snapshot.side_effect = mock_load_file_snapshot
        self.mock_storage.load_checkpoint.side_effect = [
            checkpoint1,
            checkpoint2,
            checkpoint1,
            checkpoint2,
        ]

        # Test regular diff
        self.comparison_service.compare_checkpoints(1, 2)
        self.mock_file_service.generate_diff.assert_called_once_with("old", "new")

        # Reset mock
        self.mock_file_service.generate_diff.reset_mock()

        # Test rich diff
        self.comparison_service.compare_checkpoints(1, 2, use_rich=True)
        self.mock_file_service.generate_diff_rich.assert_called_once_with("old", "new")
