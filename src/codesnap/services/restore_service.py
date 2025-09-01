from pathlib import Path

from ..storage import StorageManager
from .checkpoint_service import CheckpointService


class RestoreService:
    """Manages checkpoint restore operations."""

    def __init__(
        self,
        storage_manager: StorageManager,
        checkpoint_service: CheckpointService,
    ):
        self.storage = storage_manager
        self.checkpoint_service = checkpoint_service
        self.project_root = self.checkpoint_service.project_root

    def restore_checkpoint(
        self, checkpoint_id: int, restore_path: Path | None = None
    ) -> bool:
        """Restore project state from a checkpoint, deleting files not in checkpoint."""
        checkpoint_to_restore = self.storage.load_checkpoint(int(checkpoint_id))
        if not checkpoint_to_restore:
            return False

        restore_path = restore_path or self.project_root

        # Get all checkpoints and remove the ones after the one we are restoring
        all_checkpoints = self.storage.list_checkpoints()
        checkpoints_to_delete = [
            c for c in all_checkpoints if c.timestamp > checkpoint_to_restore.timestamp
        ]

        for cp in checkpoints_to_delete:
            checkpoint_path = self.storage.checkpoints_dir / f"{cp.id}.json"
            if checkpoint_path.exists():
                checkpoint_path.unlink()

        current_files = self.checkpoint_service.file_service.get_project_files()

        # Convert to relative paths for comparison
        current_relative_files = {
            str(file_path.relative_to(restore_path)) for file_path in current_files
        }

        # Get files that should exist after restore (from checkpoint)
        checkpoint_files = set(checkpoint_to_restore.file_snapshots.keys())

        # Find files to delete (exist currently but not in checkpoint)
        files_to_delete = current_relative_files - checkpoint_files

        # Delete files that shouldn't exist
        for file_path_str in files_to_delete:
            file_path = restore_path / file_path_str
            if file_path.exists():
                file_path.unlink()

        # Restore each file from checkpoint
        for file_path_str, content_hash in checkpoint_to_restore.file_snapshots.items():
            file_path = restore_path / file_path_str

            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Get the file content
            content = self.storage.load_file_snapshot(content_hash)
            if content is not None:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

        return True
