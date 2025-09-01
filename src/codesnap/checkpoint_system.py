from pathlib import Path
from typing import TYPE_CHECKING

from .config import Config
from .models import Checkpoint, CodeChange, Prompt
from .services import ServiceFactory
from .services.interfaces import (
    CheckpointError,
)
from .storage import StorageManager

if TYPE_CHECKING:
    pass


class CheckpointSystem:
    """Manages code checkpoints with version control functionality.

    This is the main entry point for the CodeSnap system, providing
    a high-level API for checkpoint operations, comparisons, and restores.
    """

    def __init__(self, storage_manager: StorageManager, config: Config | None = None):
        """
        Initialize the checkpoint system.

        Args:
            storage_manager: Storage manager instance
            config: Configuration object (optional, creates default if not provided)
        """
        self.storage = storage_manager
        self.config = config or Config()
        self.project_root = self.config.project_root

        # Initialize services
        self.services = ServiceFactory(self.storage, self.config)

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
            return self.services.checkpoint.create_checkpoint(
                description=description,
                tags=tags,
                prompt=prompt,
            )
        except CheckpointError:
            raise
        except Exception as e:
            raise CheckpointError(
                f"Failed to create checkpoint: {str(e)}",
                service_name="CheckpointSystem",
            ) from e

    def create_initial_checkpoint(
        self, description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt.

        Args:
            description: Description for the initial checkpoint

        Returns:
            The created initial checkpoint object

        Raises:
            CheckpointError: If initial checkpoint creation fails
        """
        try:
            return self.services.checkpoint.create_initial_checkpoint(
                description=description
            )
        except CheckpointError:
            raise
        except Exception as e:
            raise CheckpointError(
                f"Failed to create initial checkpoint: {str(e)}",
                service_name="CheckpointSystem",
            ) from e

    def restore_checkpoint(
        self, checkpoint_id: int, restore_path: Path | None = None
    ) -> bool:
        """Restore project state from a checkpoint."""
        return self.services.restore.restore_checkpoint(checkpoint_id, restore_path)

    def compare_checkpoints(
        self, checkpoint1_id: int, checkpoint2_id: int
    ) -> list[CodeChange]:
        """Compare two checkpoints and return the differences."""
        return self.services.comparison.compare_checkpoints(
            checkpoint1_id, checkpoint2_id, use_rich=True
        )

    def compare_with_current(self, checkpoint_id: int) -> list[CodeChange]:
        """Compare a checkpoint with the current project state."""
        return self.services.comparison.compare_with_current(
            checkpoint_id, use_rich=True
        )
