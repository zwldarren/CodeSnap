from ..config import Config
from ..storage import StorageManager
from .checkpoint_service import CheckpointService
from .comparison_service import ComparisonService
from .file_service import FileService
from .restore_service import RestoreService


class ServiceFactory:
    """Factory for creating and providing service instances."""

    def __init__(self, storage_manager: StorageManager, config: Config):
        self.storage_manager = storage_manager
        self.config = config
        self._file_service: FileService | None = None
        self._comparison_service: ComparisonService | None = None
        self._checkpoint_service: CheckpointService | None = None
        self._restore_service: RestoreService | None = None

    @property
    def file(self) -> FileService:
        if self._file_service is None:
            self._file_service = FileService(self.config)
        return self._file_service

    @property
    def comparison(self) -> ComparisonService:
        if self._comparison_service is None:
            self._comparison_service = ComparisonService(
                self.storage_manager, self.file
            )
        return self._comparison_service

    @property
    def checkpoint(self) -> CheckpointService:
        if self._checkpoint_service is None:
            self._checkpoint_service = CheckpointService(
                self.storage_manager, self.file
            )
        return self._checkpoint_service

    @property
    def restore(self) -> RestoreService:
        if self._restore_service is None:
            self._restore_service = RestoreService(
                self.storage_manager, self.checkpoint
            )
        return self._restore_service
