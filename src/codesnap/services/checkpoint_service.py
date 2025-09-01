import logging

from ..models import Checkpoint, Prompt
from ..storage import StorageManager
from .file_service import FileService

logger = logging.getLogger(__name__)


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
        # Generate name from prompt if available
        if prompt and prompt.content:
            name = prompt.content[:50] + ("..." if len(prompt.content) > 50 else "")
        else:
            name = f"Checkpoint {self.storage.get_next_checkpoint_id()}"

        logger.info(f"Creating checkpoint: {name}")

        try:
            # Create the checkpoint
            checkpoint = Checkpoint(
                id=self.storage.get_next_checkpoint_id(),
                description=description,
                prompt=prompt,
                tags=tags or [],
            )

            # Capture file snapshots
            project_files = self.file_service.get_project_files()
            logger.debug(f"Capturing snapshots for {len(project_files)} files")

            for file_path in project_files:
                relative_path = file_path.relative_to(self.project_root)
                content = self.file_service.read_file_content(file_path)
                if content is not None:
                    content_hash = self.storage.save_file_snapshot(file_path, content)
                    checkpoint.file_snapshots[str(relative_path)] = content_hash
                    logger.debug(f"Saved snapshot for {relative_path}")

            # Save the checkpoint
            self.storage.save_checkpoint(checkpoint)
            logger.info(f"Checkpoint created with ID: {checkpoint.id}")

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise

    def create_initial_checkpoint(
        self, description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt."""
        return self.create_checkpoint(description=description)
