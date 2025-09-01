from datetime import datetime

from codesnap.models import Checkpoint, CodeChange, ExportFormat, Prompt


class TestPrompt:
    """Test cases for the Prompt model."""

    def test_prompt_creation(self):
        """Test basic prompt creation."""
        prompt = Prompt(content="Test prompt")
        assert prompt.content == "Test prompt"
        assert isinstance(prompt.timestamp, datetime)
        assert prompt.tags == []
        assert prompt.metadata == {}

    def test_prompt_with_tags(self):
        """Test prompt creation with tags."""
        prompt = Prompt(content="Test prompt", tags=["test", "example"])
        assert prompt.tags == ["test", "example"]

    def test_prompt_with_metadata(self):
        """Test prompt creation with metadata."""
        metadata = {"author": "test", "priority": "high"}
        prompt = Prompt(content="Test prompt", metadata=metadata)
        assert prompt.metadata == metadata

    def test_prompt_timestamp_default(self):
        """Test that timestamp is set by default."""
        before = datetime.now()
        prompt = Prompt(content="Test prompt")
        after = datetime.now()
        assert before <= prompt.timestamp <= after


class TestCheckpoint:
    """Test cases for the Checkpoint model."""

    def test_checkpoint_creation(self):
        """Test basic checkpoint creation."""
        checkpoint = Checkpoint(id=1)
        assert checkpoint.id == 1
        assert checkpoint.description == ""
        assert checkpoint.prompt is None
        assert checkpoint.tags == []
        assert checkpoint.file_snapshots == {}
        assert checkpoint.restored_from is None
        assert checkpoint.restore_timestamp is None
        assert checkpoint.metadata == {}

    def test_checkpoint_with_prompt(self):
        """Test checkpoint with prompt."""
        prompt = Prompt(content="Test prompt")
        checkpoint = Checkpoint(id=1, prompt=prompt)
        assert checkpoint.prompt == prompt

    def test_checkpoint_with_description(self):
        """Test checkpoint with description."""
        checkpoint = Checkpoint(id=1, description="Test checkpoint")
        assert checkpoint.description == "Test checkpoint"

    def test_checkpoint_with_tags(self):
        """Test checkpoint with tags."""
        checkpoint = Checkpoint(id=1, tags=["test", "checkpoint"])
        assert checkpoint.tags == ["test", "checkpoint"]

    def test_checkpoint_with_file_snapshots(self):
        """Test checkpoint with file snapshots."""
        snapshots = {"file1.py": "content1", "file2.py": "content2"}
        checkpoint = Checkpoint(id=1, file_snapshots=snapshots)
        assert checkpoint.file_snapshots == snapshots

    def test_checkpoint_with_restore_info(self):
        """Test checkpoint with restore information."""
        checkpoint = Checkpoint(id=1, restored_from=2, restore_timestamp=datetime.now())
        assert checkpoint.restored_from == 2
        assert isinstance(checkpoint.restore_timestamp, datetime)

    def test_checkpoint_name_property_with_prompt(self):
        """Test checkpoint name property with prompt."""
        prompt = Prompt(content="This is a test prompt")
        checkpoint = Checkpoint(id=1, prompt=prompt)
        assert checkpoint.name == "This is a test prompt"

    def test_checkpoint_name_property_without_prompt(self):
        """Test checkpoint name property without prompt."""
        checkpoint = Checkpoint(id=1)
        assert checkpoint.name == "Checkpoint 1"

    def test_checkpoint_timestamp_default(self):
        """Test that timestamp is set by default."""
        before = datetime.now()
        checkpoint = Checkpoint(id=1)
        after = datetime.now()
        assert before <= checkpoint.timestamp <= after


class TestCodeChange:
    """Test cases for the CodeChange model."""

    def test_code_change_creation(self):
        """Test basic code change creation."""
        change = CodeChange(file_path="test.py", change_type="modified")
        assert change.file_path == "test.py"
        assert change.change_type == "modified"
        assert change.old_content is None
        assert change.new_content is None
        assert change.diff is None

    def test_code_change_with_content(self):
        """Test code change with old and new content."""
        change = CodeChange(
            file_path="test.py",
            change_type="modified",
            old_content="old content",
            new_content="new content",
        )
        assert change.old_content == "old content"
        assert change.new_content == "new content"

    def test_code_change_with_diff(self):
        """Test code change with diff."""
        diff_data = {"lines": [1, 2, 3], "changes": ["added", "removed"]}
        change = CodeChange(file_path="test.py", change_type="modified", diff=diff_data)
        assert change.diff == diff_data


class TestExportFormat:
    """Test cases for the ExportFormat enum."""

    def test_export_format_values(self):
        """Test that export format enum has correct values."""
        assert ExportFormat.MARKDOWN == "markdown"
        assert ExportFormat.HTML == "html"

    def test_export_format_is_string_enum(self):
        """Test that ExportFormat is a string enum."""
        assert issubclass(ExportFormat, str)
        assert isinstance(ExportFormat.MARKDOWN, str)
        assert isinstance(ExportFormat.HTML, str)
