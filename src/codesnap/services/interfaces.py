"""Interfaces and abstract base classes for CodeSnap services.

This module defines the abstract interfaces that all service implementations
should follow, ensuring consistent API and enabling dependency injection.
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any, Protocol

from ..models import Checkpoint, CodeChange, Prompt


class IStorageManager(Protocol):
    """Protocol for storage management operations."""

    @property
    @abstractmethod
    def checkpoints_dir(self) -> Path:
        """Get the checkpoints directory."""
        ...

    @abstractmethod
    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint to storage."""
        ...

    @abstractmethod
    def load_checkpoint(self, checkpoint_id: int) -> Checkpoint | None:
        """Load a checkpoint from storage."""
        ...

    @abstractmethod
    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints."""
        ...

    @abstractmethod
    def get_next_checkpoint_id(self) -> int:
        """Get the next available checkpoint ID."""
        ...

    @abstractmethod
    def save_file_snapshot(self, content: str) -> str:
        """Save a file snapshot and return its content hash."""
        ...

    @abstractmethod
    def load_file_snapshot(self, content_hash: str) -> str | None:
        """Load a file snapshot by its hash."""
        ...

    @abstractmethod
    def export_data(
        self,
        output_path: Path,
        fmt: Any,
        checkpoint_system: Any | None = None,
    ) -> None:
        """Export data in the specified format."""
        ...


class IFileService(Protocol):
    """Protocol for file system operations."""

    @property
    @abstractmethod
    def project_root(self) -> Path:
        """Get the project root directory."""
        ...

    @abstractmethod
    def get_project_files(self, root: Path | None = None) -> list[Path]:
        """Get all files under a root that aren't ignored."""
        ...

    @abstractmethod
    def read_file_content(self, file_path: Path) -> str | None:
        """Read file content, return None if it exceeds size limit or doesn't exist."""
        ...

    @abstractmethod
    def generate_diff(self, old_content: str, new_content: str) -> str:
        """Generate a unified diff between two content strings."""
        ...

    @abstractmethod
    def generate_diff_rich(self, old_content: str, new_content: str) -> Any:
        """Generate a rich Text diff between two content strings."""
        ...


class ICheckpointService(Protocol):
    """Protocol for checkpoint operations."""

    @property
    @abstractmethod
    def file_service(self) -> "IFileService":
        """Get the file service instance."""
        ...

    @property
    @abstractmethod
    def project_root(self) -> Path:
        """Get the project root directory."""
        ...

    @abstractmethod
    def create_checkpoint(
        self,
        description: str = "",
        tags: list[str] | None = None,
        prompt: Prompt | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint with current project state."""
        ...

    @abstractmethod
    def create_initial_checkpoint(
        self, description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt."""
        ...


class IComparisonService(Protocol):
    """Protocol for comparison operations."""

    @abstractmethod
    def compare_checkpoints(
        self, checkpoint1_id: int, checkpoint2_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare two checkpoints and return the differences."""
        ...

    @abstractmethod
    def compare_with_current(
        self, checkpoint_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare a checkpoint with the current project state."""
        ...


class IRestoreService(Protocol):
    """Protocol for restore operations."""

    @abstractmethod
    def restore_checkpoint(
        self, checkpoint_id: int, restore_path: Path | None = None
    ) -> bool:
        """Restore project state from a checkpoint."""
        ...


class IFileMonitorService(Protocol):
    """Protocol for file monitoring operations."""

    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring file changes in the project directory."""
        ...

    @abstractmethod
    def stop_monitoring(self) -> set[str]:
        """Stop monitoring and return the set of changed files."""
        ...

    @abstractmethod
    def get_changed_files(self) -> set[str]:
        """Get the current set of changed files."""
        ...

    @abstractmethod
    def is_file_changed(self, relative_path: str) -> bool:
        """Check if a specific file has been changed."""
        ...


class ServiceError(Exception):
    """Base exception for service-related errors."""

    def __init__(self, message: str, service_name: str | None = None):
        self.service_name = service_name
        super().__init__(f"{f'[{service_name}] ' if service_name else ''}{message}")


class CheckpointError(ServiceError):
    """Exception raised for checkpoint-related errors."""

    pass


class ComparisonError(ServiceError):
    """Exception raised for comparison-related errors."""

    pass


class RestoreError(ServiceError):
    """Exception raised for restore-related errors."""

    pass


class FileServiceError(ServiceError):
    """Exception raised for file service-related errors."""

    pass


class StorageError(ServiceError):
    """Exception raised for storage-related errors."""

    pass
