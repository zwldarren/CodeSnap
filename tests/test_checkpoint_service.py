import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from codesnap.models import Prompt
from codesnap.services.checkpoint_service import CheckpointService
from codesnap.services.interfaces import CheckpointError, IFileService, IStorageManager


class TestCheckpointService:
    """Test cases for the CheckpointService class."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_storage = Mock(spec=IStorageManager)
        self.mock_file_service = Mock(spec=IFileService)
        self.checkpoint_service = CheckpointService(
            self.mock_storage, self.mock_file_service
        )
        self.project_root = Path("/mock/project")
        self.mock_file_service.project_root = self.project_root

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_checkpoint_service_initialization(self):
        """Test CheckpointService initialization."""
        assert self.checkpoint_service._storage == self.mock_storage
        assert self.checkpoint_service._file_service == self.mock_file_service

    def test_file_service_property(self):
        """Test file_service property."""
        assert self.checkpoint_service.file_service == self.mock_file_service

    def test_project_root_property(self):
        """Test project_root property."""
        mock_project_root = Path("/mock/project/root")
        self.mock_file_service.project_root = mock_project_root

        assert self.checkpoint_service.project_root == mock_project_root

    def test_create_checkpoint_basic(self):
        """Test basic checkpoint creation."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py",
            self.project_root / "file2.py",
        ]
        self.mock_file_service.read_file_content.side_effect = ["content1", "content2"]
        self.mock_storage.save_file_snapshot.side_effect = ["hash1", "hash2"]

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint(
            description="Test checkpoint",
            tags=["test", "example"],
            prompt=Prompt(content="Test prompt"),
        )

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == "Test checkpoint"
        assert checkpoint.tags == ["test", "example"]
        assert checkpoint.prompt.content == "Test prompt"
        assert checkpoint.file_snapshots == {"file1.py": "hash1", "file2.py": "hash2"}

        # Verify storage was called
        self.mock_storage.save_checkpoint.assert_called_once_with(checkpoint)

    def test_create_checkpoint_without_optional_params(self):
        """Test checkpoint creation without optional parameters."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint()

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == ""
        assert checkpoint.tags == []
        assert checkpoint.prompt is None
        assert checkpoint.file_snapshots == {"file1.py": "hash1"}

    def test_create_checkpoint_with_empty_tags_list(self):
        """Test checkpoint creation with empty tags list."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        # Create checkpoint with empty tags
        checkpoint = self.checkpoint_service.create_checkpoint(tags=[])

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.tags == []

    def test_create_checkpoint_with_file_reading_error(self):
        """Test checkpoint creation when file reading fails."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = (
            None  # File can't be read
        )

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint()

        # Verify that unreadable files are skipped
        assert checkpoint.id == checkpoint_id
        assert checkpoint.file_snapshots == {}

    def test_create_checkpoint_with_no_files(self):
        """Test checkpoint creation when no files are found."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = []

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint()

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.file_snapshots == {}

    def test_create_checkpoint_storage_error(self):
        """Test checkpoint creation when storage fails."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"
        self.mock_storage.save_checkpoint.side_effect = Exception("Storage failed")

        # Should raise CheckpointError
        with pytest.raises(CheckpointError):
            self.checkpoint_service.create_checkpoint()

    def test_create_checkpoint_file_service_error(self):
        """Test checkpoint creation when file service fails."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.side_effect = Exception(
            "File service failed"
        )

        # Should raise CheckpointError
        with pytest.raises(CheckpointError):
            self.checkpoint_service.create_checkpoint()

    def test_create_initial_checkpoint(self):
        """Test creating initial checkpoint."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        # Create initial checkpoint
        checkpoint = self.checkpoint_service.create_initial_checkpoint(
            description="Initial checkpoint"
        )

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == "Initial checkpoint"
        assert checkpoint.prompt is None
        assert checkpoint.tags == []
        assert checkpoint.file_snapshots == {"file1.py": "hash1"}

    def test_create_initial_checkpoint_default_description(self):
        """Test creating initial checkpoint with default description."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        # Create initial checkpoint with default description
        checkpoint = self.checkpoint_service.create_initial_checkpoint()

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == "Initial checkpoint"
        assert checkpoint.prompt is None
        assert checkpoint.tags == []
        assert checkpoint.file_snapshots == {"file1.py": "hash1"}

    def test_create_checkpoint_with_multiple_files(self):
        """Test checkpoint creation with multiple files."""
        # Setup mocks
        checkpoint_id = 1
        files = [self.project_root / f"file{i}.py" for i in range(1, 6)]
        contents = [f"content{i}" for i in range(1, 6)]
        hashes = [f"hash{i}" for i in range(1, 6)]

        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = files
        self.mock_file_service.read_file_content.side_effect = contents
        self.mock_storage.save_file_snapshot.side_effect = hashes

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint(
            description="Multi-file checkpoint"
        )

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == "Multi-file checkpoint"
        expected_snapshots = {
            "file1.py": "hash1",
            "file2.py": "hash2",
            "file3.py": "hash3",
            "file4.py": "hash4",
            "file5.py": "hash5",
        }
        assert checkpoint.file_snapshots == expected_snapshots

        # Verify all files were processed
        assert self.mock_file_service.read_file_content.call_count == 5
        assert self.mock_storage.save_file_snapshot.call_count == 5

    def test_create_checkpoint_with_some_unreadable_files(self):
        """Test checkpoint creation with some unreadable files."""
        # Setup mocks
        checkpoint_id = 1
        files = [
            self.project_root / "file1.py",
            self.project_root / "file2.py",
            self.project_root / "file3.py",
        ]
        contents = ["content1", None, "content3"]  # file2.py is unreadable
        hashes = ["hash1", "hash3"]

        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = files
        self.mock_file_service.read_file_content.side_effect = contents
        self.mock_storage.save_file_snapshot.side_effect = hashes

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint()

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        expected_snapshots = {"file1.py": "hash1", "file3.py": "hash3"}
        assert checkpoint.file_snapshots == expected_snapshots

        # Verify only readable files were processed
        assert self.mock_storage.save_file_snapshot.call_count == 2

    def test_create_checkpoint_with_custom_description(self):
        """Test checkpoint creation with custom description."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        # Create checkpoint with custom description
        description = "Custom checkpoint description with special chars: áéíóú 🚀"
        checkpoint = self.checkpoint_service.create_checkpoint(description=description)

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == description

    def test_create_checkpoint_with_prompt_and_tags(self):
        """Test checkpoint creation with both prompt and tags."""
        # Setup mocks
        checkpoint_id = 1
        self.mock_storage.get_next_checkpoint_id.return_value = checkpoint_id
        self.mock_file_service.get_project_files.return_value = [
            self.project_root / "file1.py"
        ]
        self.mock_file_service.read_file_content.return_value = "content1"
        self.mock_storage.save_file_snapshot.return_value = "hash1"

        prompt = Prompt(content="Test prompt", tags=["prompt-tag"])
        tags = ["checkpoint-tag", "test"]

        # Create checkpoint
        checkpoint = self.checkpoint_service.create_checkpoint(
            description="Test checkpoint", tags=tags, prompt=prompt
        )

        # Verify checkpoint properties
        assert checkpoint.id == checkpoint_id
        assert checkpoint.description == "Test checkpoint"
        assert checkpoint.tags == tags
        assert checkpoint.prompt == prompt
        assert checkpoint.file_snapshots == {"file1.py": "hash1"}
