from ..models import CodeChange
from ..storage import StorageManager
from .file_service import FileService


class ComparisonService:
    """Compares checkpoints and generates differences."""

    def __init__(
        self,
        storage: StorageManager,
        file_system: FileService,
    ):
        """Initialize the checkpoint comparator."""
        self.storage = storage
        self.file_system = file_system

    def _compare_files(
        self,
        file_path: str,
        old_content_hash: str | None,
        new_content_hash: str | None,
        use_rich: bool = False,
    ) -> CodeChange | None:
        """Compare two file versions and return the change if any."""
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

    def _compare_content(
        self,
        file_path: str,
        old_content: str | None,
        new_content: str | None,
        use_rich: bool = False,
    ) -> CodeChange | None:
        """Compare two file contents and return the change if any."""
        # Always compare actual content, not just hashes
        if old_content is not None and new_content is not None:
            # File exists in both versions, compare content
            if old_content == new_content:
                return None  # No change
            else:
                # File modified
                diff_func = (
                    self.file_system.generate_diff_rich
                    if use_rich
                    else self.file_system.generate_diff
                )
                diff = diff_func(old_content, new_content)
                return CodeChange(
                    file_path=file_path,
                    change_type="modified",
                    old_content=old_content,
                    new_content=new_content,
                    diff=diff,
                )
        elif old_content is not None and new_content is None:
            # File deleted
            diff_func = (
                self.file_system.generate_diff_rich
                if use_rich
                else self.file_system.generate_diff
            )
            diff = diff_func(old_content, "")
            return CodeChange(
                file_path=file_path,
                change_type="deleted",
                old_content=old_content,
                new_content=None,
                diff=diff,
            )
        elif old_content is None and new_content is not None:
            # File added
            diff_func = (
                self.file_system.generate_diff_rich
                if use_rich
                else self.file_system.generate_diff
            )
            diff = diff_func("", new_content)
            return CodeChange(
                file_path=file_path,
                change_type="added",
                old_content=None,
                new_content=new_content,
                diff=diff,
            )
        return None

    def compare_checkpoints(
        self, checkpoint1_id: int, checkpoint2_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare two checkpoints and return the differences."""
        try:
            checkpoint1 = self.storage.load_checkpoint(int(checkpoint1_id))
            checkpoint2 = self.storage.load_checkpoint(int(checkpoint2_id))

            if not checkpoint1:
                return []
            if not checkpoint2:
                return []

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

        except Exception:
            return []

    def compare_with_current(
        self, checkpoint_id: int, use_rich: bool = False
    ) -> list[CodeChange]:
        """Compare a checkpoint with the current project state."""

        checkpoint = self.storage.load_checkpoint(int(checkpoint_id))
        if not checkpoint:
            return []

        changes = []
        current_files = {
            str(f.relative_to(self.file_system.project_root)): f
            for f in self.file_system.get_project_files()
        }
        all_files = set(checkpoint.file_snapshots.keys()) | set(current_files.keys())

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
