import logging
from datetime import datetime
from pathlib import Path

from .comparator import CheckpointComparator
from .config import Config
from .diff import DiffGenerator
from .fs import FileSystemManager
from .models import Checkpoint, CodeChange, Prompt
from .storage import StorageManager

logger = logging.getLogger(__name__)


class CheckpointSystem:
    """Manages code checkpoints with version control functionality."""

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

        # Initialize components
        self.file_system = FileSystemManager(self.config)
        self.diff_generator = DiffGenerator()
        self.comparator = CheckpointComparator(
            storage_manager, self.file_system, self.diff_generator
        )

    def create_checkpoint(
        self,
        name: str,
        description: str = "",
        tags: list[str] | None = None,
        prompt: Prompt | None = None,
        branch_id: str | None = None,
    ) -> Checkpoint:
        """Create a new checkpoint with current project state."""
        logger.info(f"Creating checkpoint: {name}")

        try:
            # Internal branch management - get or create default branch
            if not branch_id:
                active_branch = self.storage.get_or_create_default_branch()
                branch_id = active_branch.id if active_branch else None
                logger.debug(f"Using branch ID: {branch_id}")

            # Create the checkpoint
            checkpoint = Checkpoint(
                name=name,
                description=description,
                prompt=prompt,
                tags=tags or [],
                branch_id=branch_id,
            )

            # Capture file snapshots
            project_files = self.file_system.get_project_files()
            logger.debug(f"Capturing snapshots for {len(project_files)} files")

            for file_path in project_files:
                relative_path = file_path.relative_to(self.project_root)
                content = self.file_system.read_file_content(file_path)
                if content is not None:
                    content_hash = self.storage.save_file_snapshot(file_path, content)
                    checkpoint.file_snapshots[str(relative_path)] = content_hash
                    logger.debug(f"Saved snapshot for {relative_path}")

            # Save the checkpoint
            self.storage.save_checkpoint(checkpoint)
            logger.info(f"Checkpoint created with ID: {checkpoint.id}")

            # Update the branch's current checkpoint (internal branch management)
            if branch_id:
                branch = self.storage.load_branch(branch_id)
                if branch:
                    branch.current_checkpoint_id = checkpoint.id
                    self.storage.save_branch(branch)
                    logger.debug(
                        f"Updated branch {branch_id} with checkpoint {checkpoint.id}"
                    )

            return checkpoint

        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise

    def create_initial_checkpoint(
        self, name: str = "Initial", description: str = "Initial checkpoint"
    ) -> Checkpoint:
        """Create an initial checkpoint without a prompt."""
        return self.create_checkpoint(name=name, description=description)

    def restore_checkpoint(
        self, checkpoint_id: str, restore_path: Path | None = None
    ) -> bool:
        """Restore project state from a checkpoint."""
        checkpoint = self.storage.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        restore_path = restore_path or self.project_root

        # Get current branch and check if we're restoring to a different branch
        current_branch = self.storage.get_or_create_default_branch()

        should_create_new_branch = False
        if (
            checkpoint.branch_id
            and current_branch
            and checkpoint.branch_id != current_branch.id
        ):
            should_create_new_branch = True
        elif checkpoint.branch_id and current_branch:
            # Check if this checkpoint is the latest in its branch
            branch_checkpoints = self.storage.get_checkpoints_by_branch(
                checkpoint.branch_id
            )
            if branch_checkpoints:
                latest_checkpoint = max(branch_checkpoints, key=lambda c: c.timestamp)
                if latest_checkpoint.id != checkpoint.id:
                    should_create_new_branch = True
        # If checkpoint has no branch_id, create a new branch
        elif not checkpoint.branch_id:
            should_create_new_branch = True
        elif checkpoint.branch_id:
            # Check if this checkpoint is the latest in its branch
            branch_checkpoints = self.storage.get_checkpoints_by_branch(
                checkpoint.branch_id
            )
            if branch_checkpoints:
                latest_checkpoint = max(branch_checkpoints, key=lambda c: c.timestamp)
                if latest_checkpoint.id != checkpoint.id:
                    should_create_new_branch = True
        else:
            # Check if this checkpoint is the latest in its branch
            branch_checkpoints = self.storage.get_checkpoints_by_branch(
                checkpoint.branch_id
            )
            if branch_checkpoints:
                latest_checkpoint = max(branch_checkpoints, key=lambda c: c.timestamp)
                if latest_checkpoint.id != checkpoint.id:
                    should_create_new_branch = True

        # Create a new branch if needed
        if should_create_new_branch:
            # Generate branch name based on the checkpoint being restored
            branch_name = f"branch-from-{checkpoint.name.lower().replace(' ', '-')}"
            branch_counter = 1
            while self.storage.get_branch_by_name(branch_name):
                branch_name = (
                    f"branch-from-{checkpoint.name.lower().replace(' ', '-')}"
                    f"-{branch_counter}"
                )
                branch_counter += 1

            new_branch = self.storage.create_new_branch(
                name=branch_name,
                description=f"Branch created by restoring checkpoint {checkpoint.id}",
                created_from=checkpoint_id,
            )
            current_branch = new_branch
            logger.info(f"Created new branch: {new_branch.name} (ID: {new_branch.id})")

        # Record restore operation by creating a new checkpoint with restore metadata
        current_checkpoint = self.create_checkpoint(
            name=f"Restored from {checkpoint.name}",
            description=f"Restored to checkpoint {checkpoint.id}",
            branch_id=current_branch.id if current_branch else None,
        )

        # Set restore metadata
        current_checkpoint.restored_from = checkpoint_id
        current_checkpoint.restore_timestamp = datetime.now()
        self.storage.save_checkpoint(current_checkpoint)

        # Restore each file
        for file_path_str, content_hash in checkpoint.file_snapshots.items():
            file_path = restore_path / file_path_str

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Get the file content
            content = self.storage.load_file_snapshot(content_hash)
            if content is not None:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

        return True

    def compare_checkpoints(
        self, checkpoint1_id: str, checkpoint2_id: str
    ) -> list[CodeChange]:
        """Compare two checkpoints and return the differences."""
        return self.comparator.compare_checkpoints(
            checkpoint1_id, checkpoint2_id, use_rich=True
        )

    def compare_with_current(self, checkpoint_id: str) -> list[CodeChange]:
        """Compare a checkpoint with the current project state."""
        return self.comparator.compare_with_current(checkpoint_id, use_rich=True)
