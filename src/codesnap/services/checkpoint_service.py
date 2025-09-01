from ..models import Checkpoint, Prompt
from ..storage import StorageManager
from .file_service import FileService


class CheckpointService:
    """Manages checkpoint operations."""

    def __init__(
        self,
        storage_manager: StorageManager,
        file_service: FileService,
    ):
        self.storage = storage_manager
        self.file_service = file_service
        self.project_root = file_service.project_root

    def create_checkpoint(
        self,
        description: str = "",
        tags: list[str] | None = None,
        prompt: Prompt | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint with current project state."""

        # Create the checkpoint
        checkpoint = Checkpoint(
            id=self.storage.get_next_checkpoint_id(),
            description=description,
            prompt=prompt,
            tags=tags or [],
        )

        # Capture file snapshots
        project_files = self.file_service.get_project_files()

        for file_path in project_files:
            relative_path = file_path.relative_to(self.project_root)
            content = self.file_service.read_file_content(file_path)
            if content is not None:
                content_hash = self.storage.save_file_snapshot(file_path, content)
                checkpoint.file_snapshots[str(relative_path)] = content_hash

        # Save the checkpoint
        self.storage.save_checkpoint(checkpoint)

        return checkpoint

    def create_initial_checkpoint(
        self, description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt."""
        return self.create_checkpoint(description=description)
