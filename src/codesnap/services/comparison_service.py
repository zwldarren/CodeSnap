from typing import TYPE_CHECKING

from ..models import CodeChange
from .interfaces import (
    ComparisonError,
    IComparisonService,
    IFileService,
    IStorageManager,
)

if TYPE_CHECKING:
    pass


class ComparisonService(IComparisonService):
    """Compares checkpoints and generates differences.

    This service handles comparison operations between checkpoints
    and between checkpoints and the current project state.
    """

    def __init__(
        self,
        storage: IStorageManager,
        file_system: IFileService,
    ):
        """Initialize the checkpoint comparator.

        Args:
            storage: Storage manager instance for data retrieval
            file_system: File service instance for file operations
        """
        self.storage = storage
        self.file_system = file_system

    def _compare_files(
        self,
        file_path: str,
        old_content_hash: str | None,
        new_content_hash: str | None,
        use_rich: bool = False,
    ) -> CodeChange | None:
        try:
            old_content = (
                self.storage.load_file_snapshot(old_content_hash)
                if old_content_hash
                else None
            )
            new_content = (
                self.storage.load_file_snapshot(new_content_hash)
                if new_content_hash
                else None
            )

            return self._compare_content(file_path, old_content, new_content, use_rich)
        except Exception as e:
            raise ComparisonError(
                f"Failed to compare files for '{file_path}': {str(e)}",
                service_name="ComparisonService",
            ) from e

    def _compare_content(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        use_rich: bool = False,
    ) -> CodeChange | None:
        try:

            def make_diff(a: str, b: str):
                diff_func = (
                    self.file_system.generate_diff_rich
                    if use_rich
                    else self.file_system.generate_diff
                )
                return diff_func(a, b)

            # Always compare actual content, not just hashes
            if old_content is not None and new_content is not None:
                # File exists in both versions, compare content
                if old_content == new_content:
                    return None  # No change
                else:
                    # File modified
                    diff = make_diff(old_content, new_content)
                    return CodeChange(
                        file_path=file_path,
                        change_type="modified",
                        old_content=old_content,
                        new_content=new_content,
                        diff=diff,
                    )
            elif old_content is not None and new_content is None:
                # File deleted
                diff = make_diff(old_content, "")
                return CodeChange(
                    file_path=file_path,
                    change_type="deleted",
                    old_content=old_content,
                    new_content=None,
                    diff=diff,
                )
            elif old_content is None and new_content is not None:
                # File added
                diff = make_diff("", new_content)
                return CodeChange(
                    file_path=file_path,
                    change_type="added",
                    old_content=None,
                    new_content=new_content,
                    diff=diff,
                )
            return None
        except Exception as e:
            raise ComparisonError(
                f"Failed to compare content for '{file_path}': {str(e)}",
                service_name="ComparisonService",
            ) from e

    def compare_checkpoints(
        self, checkpoint1_id: int, checkpoint2_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare two checkpoints and return the differences."""
        try:
            checkpoint1 = self.storage.load_checkpoint(int(checkpoint1_id))
            checkpoint2 = self.storage.load_checkpoint(int(checkpoint2_id))

            if not checkpoint1 or not checkpoint2:
                raise ComparisonError(
                    f"One or both checkpoints not found: {checkpoint1_id}, "
                    f"{checkpoint2_id}",
                    service_name="ComparisonService",
                )

            changes = []
            all_files = set(checkpoint1.file_snapshots.keys()) | set(
                checkpoint2.file_snapshots.keys()
            )

            for file_path in all_files:
                hash1 = checkpoint1.file_snapshots.get(file_path)
                hash2 = checkpoint2.file_snapshots.get(file_path)

                change = self._compare_files(file_path, hash1, hash2, use_rich)
                if change:
                    changes.append(change)

            return changes

        except Exception as e:
            if isinstance(e, ComparisonError):
                raise
            raise ComparisonError(
                f"Failed to compare checkpoints {checkpoint1_id} and {checkpoint2_id}: "
                f"{str(e)}",
                service_name="ComparisonService",
            ) from e

    def compare_with_current(
        self, checkpoint_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare a checkpoint with the current project state."""
        try:
            checkpoint = self.storage.load_checkpoint(int(checkpoint_id))
            if not checkpoint:
                raise ComparisonError(
                    f"Checkpoint not found: {checkpoint_id}",
                    service_name="ComparisonService",
                )

            changes = []
            current_files = {
                str(f.relative_to(self.file_system.project_root)): f
                for f in self.file_system.get_project_files()
            }
            all_files = set(checkpoint.file_snapshots.keys()) | set(
                current_files.keys()
            )

            for file_path in all_files:
                checkpoint_hash = checkpoint.file_snapshots.get(file_path)
                current_file = current_files.get(file_path)

                # Load checkpoint content from storage
                checkpoint_content = (
                    self.storage.load_file_snapshot(checkpoint_hash)
                    if checkpoint_hash
                    else None
                )
                # Load current content from filesystem
                current_content = (
                    self.file_system.read_file_content(current_file)
                    if current_file
                    else None
                )

                change = self._compare_content(
                    file_path, checkpoint_content, current_content, use_rich
                )
                if change:
                    changes.append(change)

            return changes

        except Exception as e:
            if isinstance(e, ComparisonError):
                raise
            raise ComparisonError(
                f"Failed to compare checkpoint {checkpoint_id} with current: {str(e)}",
                service_name="ComparisonService",
            ) from e
