from typing import TYPE_CHECKING, Any

from ..models import Checkpoint, Prompt
from .interfaces import (
    CheckpointError,
    ICheckpointService,
    IFileService,
    IStorageManager,
)

if TYPE_CHECKING:
    pass


class CheckpointService(ICheckpointService):
    """Manages checkpoint operations.

    This service handles the creation of code checkpoints, including
    capturing file snapshots and storing checkpoint metadata.
    """

    def __init__(
        self,
        storage_manager: IStorageManager,
        file_service: IFileService,
    ):
        """Initialize the checkpoint service.

        Args:
            storage_manager: Storage manager instance for data persistence
            file_service: File service instance for file operations
        """
        self._storage = storage_manager
        self._file_service = file_service

    @property
    def file_service(self) -> IFileService:
        """Get the file service instance."""
        return self._file_service

    @property
    def project_root(self) -> Any:
        """Get the project root directory."""
        return self._file_service.project_root

    def create_checkpoint(
        self,
        description: str = "",
        tags: list[str] | None = None,
        prompt: Prompt | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint with current project state.

        Args:
            description: Optional description for the checkpoint
            tags: Optional list of tags to associate with the checkpoint
            prompt: Optional prompt object associated with the checkpoint

        Returns:
            The created checkpoint object

        Raises:
            CheckpointError: If checkpoint creation fails
        """

        try:
            # Create the checkpoint
            checkpoint = Checkpoint(
                id=self._storage.get_next_checkpoint_id(),
                description=description,
                prompt=prompt,
                tags=tags or [],
            )

            # Capture file snapshots
            project_files = self._file_service.get_project_files()

            for file_path in project_files:
                relative_path = file_path.relative_to(self.project_root)
                content = self._file_service.read_file_content(file_path)
                if content is not None:
                    content_hash = self._storage.save_file_snapshot(content)
                    checkpoint.file_snapshots[str(relative_path)] = content_hash

            # Save the checkpoint
            self._storage.save_checkpoint(checkpoint)

            return checkpoint

        except Exception as e:
            raise CheckpointError(
                f"Failed to create checkpoint: {str(e)}",
                service_name="CheckpointService",
            ) from e

    def create_initial_checkpoint(
        self, description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt.

        Args:
            description: Description for the initial checkpoint

        Returns:
            The created initial checkpoint object
        """
        return self.create_checkpoint(description=description)
