from ..config import Config
from .file_service import FileService


class FileMonitorService:
    """
    Monitors file changes in the project directory.

    This service tracks file modifications during a coding session
    and can report which files have been changed since monitoring started.
    """

    def __init__(self, config: Config, file_service: FileService):
        """
        Initialize the file monitor service.

        Args:
            config: Configuration object
            file_service: File service instance for file operations
        """
        self.config = config
        self.file_service = file_service
        self.project_root = config.project_root
        self.is_monitoring = False
        self.initial_file_states: dict[str, float] = {}  # path -> modification time
        self.changed_files: set[str] = set()

    def start_monitoring(self) -> None:
        """Start monitoring file changes in the project directory."""
        self.is_monitoring = True
        self.changed_files = set()

        # Capture initial file states
        project_files = self.file_service.get_project_files()
        for file_path in project_files:
            relative_path = str(file_path.relative_to(self.project_root))

            mod_time = file_path.stat().st_mtime
            self.initial_file_states[relative_path] = mod_time

    def stop_monitoring(self) -> set[str]:
        """
        Stop monitoring and return the set of changed files.

        Returns:
            Set of relative file paths that were modified during monitoring
        """
        self.is_monitoring = False

        # Check for final changes
        self._check_for_changes()

        return self.changed_files.copy()

    def _check_for_changes(self) -> None:
        """Check for file changes since monitoring started."""
        if not self.is_monitoring:
            return

        project_files = self.file_service.get_project_files()

        # Check for modifications to existing files
        for file_path in project_files:
            relative_path = str(file_path.relative_to(self.project_root))

            # Skip files we weren't tracking initially
            if relative_path not in self.initial_file_states:
                # This is a new file
                self.changed_files.add(relative_path)
                continue

            current_mod_time = file_path.stat().st_mtime
            initial_mod_time = self.initial_file_states[relative_path]

            if current_mod_time > initial_mod_time:
                self.changed_files.add(relative_path)

        # Check for deleted files
        for relative_path in self.initial_file_states:
            file_path = self.project_root / relative_path
            if not file_path.exists():
                self.changed_files.add(relative_path)

    def get_changed_files(self) -> set[str]:
        """
        Get the current set of changed files.

        Returns:
            Set of relative file paths that have been modified
        """
        self._check_for_changes()
        return self.changed_files.copy()

    def is_file_changed(self, relative_path: str) -> bool:
        """
        Check if a specific file has been changed.

        Args:
            relative_path: Relative path to the file

        Returns:
            True if the file has been modified, False otherwise
        """
        self._check_for_changes()
        return relative_path in self.changed_files
