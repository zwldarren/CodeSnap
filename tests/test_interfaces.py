import pytest

from codesnap.services.interfaces import (
    CheckpointError,
    ComparisonError,
    FileServiceError,
    RestoreError,
    ServiceError,
    StorageError,
)


class TestServiceError:
    """Test cases for the ServiceError base class."""

    def test_service_error_with_service_name(self):
        """Test ServiceError with service name."""
        error = ServiceError("Test message", "TestService")
        assert str(error) == "[TestService] Test message"
        assert error.service_name == "TestService"

    def test_service_error_without_service_name(self):
        """Test ServiceError without service name."""
        error = ServiceError("Test message")
        assert str(error) == "Test message"
        assert error.service_name is None

    def test_service_error_inheritance(self):
        """Test that ServiceError inherits from Exception."""
        error = ServiceError("Test message")
        assert isinstance(error, Exception)
        assert isinstance(error, ServiceError)


class TestCheckpointError:
    """Test cases for the CheckpointError class."""

    def test_checkpoint_error_with_service_name(self):
        """Test CheckpointError with service name."""
        error = CheckpointError("Checkpoint failed", "CheckpointService")
        assert str(error) == "[CheckpointService] Checkpoint failed"
        assert error.service_name == "CheckpointService"

    def test_checkpoint_error_without_service_name(self):
        """Test CheckpointError without service name."""
        error = CheckpointError("Checkpoint failed")
        assert str(error) == "Checkpoint failed"
        assert error.service_name is None

    def test_checkpoint_error_inheritance(self):
        """Test that CheckpointError inherits from ServiceError."""
        error = CheckpointError("Test message")
        assert isinstance(error, ServiceError)
        assert isinstance(error, CheckpointError)


class TestComparisonError:
    """Test cases for the ComparisonError class."""

    def test_comparison_error_with_service_name(self):
        """Test ComparisonError with service name."""
        error = ComparisonError("Comparison failed", "ComparisonService")
        assert str(error) == "[ComparisonService] Comparison failed"
        assert error.service_name == "ComparisonService"

    def test_comparison_error_without_service_name(self):
        """Test ComparisonError without service name."""
        error = ComparisonError("Comparison failed")
        assert str(error) == "Comparison failed"
        assert error.service_name is None

    def test_comparison_error_inheritance(self):
        """Test that ComparisonError inherits from ServiceError."""
        error = ComparisonError("Test message")
        assert isinstance(error, ServiceError)
        assert isinstance(error, ComparisonError)


class TestRestoreError:
    """Test cases for the RestoreError class."""

    def test_restore_error_with_service_name(self):
        """Test RestoreError with service name."""
        error = RestoreError("Restore failed", "RestoreService")
        assert str(error) == "[RestoreService] Restore failed"
        assert error.service_name == "RestoreService"

    def test_restore_error_without_service_name(self):
        """Test RestoreError without service name."""
        error = RestoreError("Restore failed")
        assert str(error) == "Restore failed"
        assert error.service_name is None

    def test_restore_error_inheritance(self):
        """Test that RestoreError inherits from ServiceError."""
        error = RestoreError("Test message")
        assert isinstance(error, ServiceError)
        assert isinstance(error, RestoreError)


class TestFileServiceError:
    """Test cases for the FileServiceError class."""

    def test_file_service_error_with_service_name(self):
        """Test FileServiceError with service name."""
        error = FileServiceError("File operation failed", "FileService")
        assert str(error) == "[FileService] File operation failed"
        assert error.service_name == "FileService"

    def test_file_service_error_without_service_name(self):
        """Test FileServiceError without service name."""
        error = FileServiceError("File operation failed")
        assert str(error) == "File operation failed"
        assert error.service_name is None

    def test_file_service_error_inheritance(self):
        """Test that FileServiceError inherits from ServiceError."""
        error = FileServiceError("Test message")
        assert isinstance(error, ServiceError)
        assert isinstance(error, FileServiceError)


class TestStorageError:
    """Test cases for the StorageError class."""

    def test_storage_error_with_service_name(self):
        """Test StorageError with service name."""
        error = StorageError("Storage operation failed", "StorageService")
        assert str(error) == "[StorageService] Storage operation failed"
        assert error.service_name == "StorageService"

    def test_storage_error_without_service_name(self):
        """Test StorageError without service name."""
        error = StorageError("Storage operation failed")
        assert str(error) == "Storage operation failed"
        assert error.service_name is None

    def test_storage_error_inheritance(self):
        """Test that StorageError inherits from ServiceError."""
        error = StorageError("Test message")
        assert isinstance(error, ServiceError)
        assert isinstance(error, StorageError)


class TestServiceErrorHierarchy:
    """Test cases for service error hierarchy and behavior."""

    def test_all_errors_inherit_from_service_error(self):
        """Test that all specific error types inherit from ServiceError."""
        errors = [
            CheckpointError("Test"),
            ComparisonError("Test"),
            RestoreError("Test"),
            FileServiceError("Test"),
            StorageError("Test"),
        ]

        for error in errors:
            assert isinstance(error, ServiceError)
            assert isinstance(error, Exception)

    def test_error_raising_and_catching(self):
        """Test raising and catching service errors."""
        with pytest.raises(ServiceError):
            raise ServiceError("Test error")

        with pytest.raises(CheckpointError):
            raise CheckpointError("Test checkpoint error")

    def test_error_chaining(self):
        """Test error chaining with service errors."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise FileServiceError("File operation failed", "FileService") from e
        except FileServiceError as caught_error:
            assert str(caught_error) == "[FileService] File operation failed"
            assert caught_error.__cause__ is not None
            assert str(caught_error.__cause__) == "Original error"

    def test_error_message_formatting(self):
        """Test that error messages are formatted correctly."""
        test_cases = [
            (ServiceError("Simple message"), "Simple message"),
            (ServiceError("Message", "Service"), "[Service] Message"),
            (CheckpointError("Checkpoint error"), "Checkpoint error"),
            (
                CheckpointError("Checkpoint error", "CheckpointService"),
                "[CheckpointService] Checkpoint error",
            ),
            (ComparisonError("Comparison error"), "Comparison error"),
            (
                ComparisonError("Comparison error", "ComparisonService"),
                "[ComparisonService] Comparison error",
            ),
            (RestoreError("Restore error"), "Restore error"),
            (
                RestoreError("Restore error", "RestoreService"),
                "[RestoreService] Restore error",
            ),
            (FileServiceError("File error"), "File error"),
            (FileServiceError("File error", "FileService"), "[FileService] File error"),
            (StorageError("Storage error"), "Storage error"),
            (
                StorageError("Storage error", "StorageService"),
                "[StorageService] Storage error",
            ),
        ]

        for error, expected_message in test_cases:
            assert str(error) == expected_message

    def test_error_attributes(self):
        """Test that error attributes are set correctly."""
        error = ServiceError("Test message", "TestService")
        assert error.service_name == "TestService"
        assert error.args == ("[TestService] Test message",)

        error_no_service = ServiceError("Test message")
        assert error_no_service.service_name is None
        assert error_no_service.args == ("Test message",)
