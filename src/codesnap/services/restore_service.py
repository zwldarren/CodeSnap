from pathlib import Path

from .interfaces import (
    ICheckpointService,
    IRestoreService,
    IStorageManager,
    RestoreError,
)


class RestoreService(IRestoreService):
    """Manages checkpoint restore operations.

    This service handles restoring project state from checkpoints,
    including file restoration and cleanup of subsequent checkpoints.
    """

    def __init__(
        self,
        storage_manager: IStorageManager,
        checkpoint_service: ICheckpointService,
    ):
        """Initialize the restore service.

        Args:
            storage_manager: Storage manager instance for data retrieval
            checkpoint_service: Checkpoint service instance for file operations
        """
        self.storage = storage_manager
        self.checkpoint_service = checkpoint_service

    def restore_checkpoint(
        self, checkpoint_id: int, restore_path: Path | None = None
    ) -> bool:
        """Restore project state from a checkpoint, deleting files not in checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to restore
            restore_path: Optional path to restore to (defaults to project root)

        Returns:
            True if restore was successful, False otherwise

        Raises:
            RestoreError: If restore operation fails
        """
        try:
            checkpoint_to_restore = self.storage.load_checkpoint(int(checkpoint_id))
            if not checkpoint_to_restore:
                raise RestoreError(f"Checkpoint {checkpoint_id} not found")

            restore_path = restore_path or self.checkpoint_service.project_root

            # Get all checkpoints and remove the ones after the one we are restoring
            all_checkpoints = self.storage.list_checkpoints()
            checkpoints_to_delete = [
                c
                for c in all_checkpoints
                if c.timestamp > checkpoint_to_restore.timestamp
            ]

            for cp in checkpoints_to_delete:
                checkpoint_path = self.storage.checkpoints_dir / f"{cp.id}.json"
                if checkpoint_path.exists():
                    checkpoint_path.unlink()

            current_files = self.checkpoint_service.file_service.get_project_files(
                root=restore_path
            )

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
            for (
                file_path_str,
                content_hash,
            ) in checkpoint_to_restore.file_snapshots.items():
                file_path = restore_path / file_path_str

                # Create parent directories if they don't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Get the file content
                content = self.storage.load_file_snapshot(content_hash)
                if content is not None:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(content)

            return True

        except Exception as e:
            raise RestoreError(
                f"Failed to restore checkpoint {checkpoint_id}: {str(e)}",
                service_name="RestoreService",
            ) from e
