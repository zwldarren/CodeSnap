from typing import TYPE_CHECKING

from ..config import Config
from ..storage import StorageManager
from .checkpoint_service import CheckpointService
from .comparison_service import ComparisonService
from .file_service import FileService
from .restore_service import RestoreService

# Import interfaces for type checking
if TYPE_CHECKING:
    from .interfaces import (
        ICheckpointService,
        IComparisonService,
        IFileService,
        IRestoreService,
        IStorageManager,
    )
else:
    # Create aliases for runtime to avoid circular imports
    ICheckpointService = CheckpointService
    IComparisonService = ComparisonService
    IFileService = FileService
    IRestoreService = RestoreService
    IStorageManager = StorageManager


class ServiceFactory:
    """Factory for creating and providing service instances.

    This factory ensures proper dependency injection and lazy initialization
    of service instances, following the dependency inversion principle.
    """

    def __init__(self, storage_manager: StorageManager, config: Config):
        self.storage_manager = storage_manager
        self.config = config
        self._file_service: FileService | None = None
        self._comparison_service: ComparisonService | None = None
        self._checkpoint_service: CheckpointService | None = None
        self._restore_service: RestoreService | None = None

    @property
    def file(self) -> IFileService:
        """Get the file service instance."""
        if self._file_service is None:
            self._file_service = FileService(self.config)
        return self._file_service

    @property
    def comparison(self) -> IComparisonService:
        """Get the comparison service instance."""
        if self._comparison_service is None:
            self._comparison_service = ComparisonService(
                self.storage_manager, self.file
            )
        return self._comparison_service

    @property
    def checkpoint(self) -> ICheckpointService:
        """Get the checkpoint service instance."""
        if self._checkpoint_service is None:
            self._checkpoint_service = CheckpointService(
                self.storage_manager, self.file
            )
        return self._checkpoint_service

    @property
    def restore(self) -> IRestoreService:
        """Get the restore service instance."""
        if self._restore_service is None:
            self._restore_service = RestoreService(
                self.storage_manager, self.checkpoint
            )
        return self._restore_service
