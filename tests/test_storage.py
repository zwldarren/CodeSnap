import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from codesnap.storage import StorageManager


class TestStorageManager:
    """Test cases for the StorageManager class."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.storage = StorageManager(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment after each test."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_storage_manager_creation_with_custom_path(self):
        """Test storage manager creation with custom base path."""
        storage = StorageManager(self.temp_dir)
        assert storage.base_path == self.temp_dir
        assert storage.checkpoints_dir.exists()
        assert storage.files_dir.exists()

    def test_storage_manager_creation_without_path(self):
        """Test storage manager creation without custom path."""
        # Save original cwd
        original_cwd = Path.cwd()

        try:
            # Change to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                import os

                os.chdir(temp_path)

                storage = StorageManager()
                expected_path = temp_path / ".codesnap"
                assert storage.base_path == expected_path
                assert storage.checkpoints_dir.exists()
                assert storage.files_dir.exists()
        finally:
            # Restore original cwd
            import os

            os.chdir(original_cwd)

    def test_checkpoints_dir_property(self):
        """Test checkpoints_dir property."""
        expected_dir = self.temp_dir / "checkpoints"
        assert self.storage.checkpoints_dir == expected_dir

    def test_get_file_hash(self):
        """Test file hash generation."""
        content = "test content"
        hash1 = self.storage._get_file_hash(content)
        hash2 = self.storage._get_file_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hash length

    def test_get_file_hash_different_content(self):
        """Test file hash generation with different content."""
        content1 = "content 1"
        content2 = "content 2"

        hash1 = self.storage._get_file_hash(content1)
        hash2 = self.storage._get_file_hash(content2)

        assert hash1 != hash2

    def test_save_json(self):
        """Test saving data as JSON."""
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        file_path = self.temp_dir / "test.json"

        self.storage._save_json(file_path, test_data)

        assert file_path.exists()
        with open(file_path) as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_load_json_existing_file(self):
        """Test loading JSON data from existing file."""
        test_data = {"key": "value", "number": 42}
        file_path = self.temp_dir / "test.json"

        # Save data first
        with open(file_path, "w") as f:
            json.dump(test_data, f)

        # Load data
        loaded_data = self.storage._load_json(file_path)
        assert loaded_data == test_data

    def test_load_json_nonexistent_file(self):
        """Test loading JSON data from nonexistent file."""
        file_path = self.temp_dir / "nonexistent.json"
        loaded_data = self.storage._load_json(file_path)
        assert loaded_data == {}

    def test_directories_created_on_init(self):
        """Test that required directories are created on initialization."""
        # Delete directories to test creation
        if self.storage.checkpoints_dir.exists():
            self.storage.checkpoints_dir.rmdir()
        if self.storage.files_dir.exists():
            self.storage.files_dir.rmdir()

        # Create new storage manager
        storage = StorageManager(self.temp_dir)

        assert storage.checkpoints_dir.exists()
        assert storage.files_dir.exists()

    def test_base_path_creation(self):
        """Test that base path is created if it doesn't exist."""
        # Remove temp directory
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

        # Create storage manager
        storage = StorageManager(self.temp_dir)

        assert storage.base_path.exists()
        assert storage.base_path.is_dir()

    def test_file_hash_consistency(self):
        """Test that file hash generation is consistent."""
        content = "consistent content"

        # Generate hash multiple times
        hashes = [self.storage._get_file_hash(content) for _ in range(5)]

        # All hashes should be identical
        assert all(h == hashes[0] for h in hashes)

    def test_json_save_with_datetime(self):
        """Test JSON saving with datetime objects."""
        test_data = {"timestamp": datetime.now(), "key": "value"}
        file_path = self.temp_dir / "test_with_datetime.json"

        # Should not raise an exception
        self.storage._save_json(file_path, test_data)
        assert file_path.exists()
