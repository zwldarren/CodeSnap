from typing import TYPE_CHECKING

from ..config import Config
from .interfaces import FileServiceError, IFileMonitorService, IFileService

if TYPE_CHECKING:
    from ..config import Config


class FileMonitorService(IFileMonitorService):
    """
    Monitors file changes in the project directory.

    This service tracks file modifications during a coding session
    and can report which files have been changed since monitoring started.
    """

    def __init__(self, config: Config, file_service: IFileService):
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
        """Start monitoring file changes in the project directory.

        Raises:
            FileServiceError: If monitoring startup fails
        """
        try:
            self.is_monitoring = True
            self.changed_files = set()

            # Capture initial file states
            project_files = self.file_service.get_project_files()
            for file_path in project_files:
                relative_path = str(file_path.relative_to(self.project_root))

                mod_time = file_path.stat().st_mtime
                self.initial_file_states[relative_path] = mod_time
        except Exception as e:
            raise FileServiceError(
                f"Failed to start file monitoring: {str(e)}",
                service_name="FileMonitorService",
            ) from e

    def stop_monitoring(self) -> set[str]:
        """
        Stop monitoring and return the set of changed files.

        Returns:
            Set of relative file paths that were modified during monitoring

        Raises:
            FileServiceError: If monitoring stop fails
        """
        try:
            self.is_monitoring = False

            # Check for final changes
            self._check_for_changes()

            return self.changed_files.copy()
        except Exception as e:
            raise FileServiceError(
                f"Failed to stop file monitoring: {str(e)}",
                service_name="FileMonitorService",
            ) from e

    def _check_for_changes(self) -> None:
        if not self.is_monitoring:
            return

        try:
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
        except Exception as e:
            raise FileServiceError(
                f"Failed to check for file changes: {str(e)}",
                service_name="FileMonitorService",
            ) from e

    def get_changed_files(self) -> set[str]:
        """
        Get the current set of changed files.

        Returns:
            Set of relative file paths that have been modified

        Raises:
            FileServiceError: If file change retrieval fails
        """
        try:
            self._check_for_changes()
            return self.changed_files.copy()
        except Exception as e:
            raise FileServiceError(
                f"Failed to get changed files: {str(e)}",
                service_name="FileMonitorService",
            ) from e

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
