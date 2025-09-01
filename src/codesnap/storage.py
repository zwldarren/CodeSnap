import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Checkpoint, ExportFormat


class StorageManager:
    """Manages storage of prompts, checkpoints, and logs."""

    def __init__(self, base_path: str | Path | None = None):
        """Initialize the storage manager with a base path."""
        if base_path:
            self.base_path = Path(base_path)
        else:
            project_root = Path.cwd()
            self.base_path = project_root / ".codesnap"
        self.base_path.mkdir(exist_ok=True)

        # Create directories for different data types
        self.checkpoints_dir = self.base_path / "checkpoints"
        self.files_dir = self.base_path / "files"

        for directory in [
            self.checkpoints_dir,
            self.files_dir,
        ]:
            directory.mkdir(exist_ok=True)

    def _get_file_hash(self, content: str) -> str:
        """Generate a hash for file content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _save_json(self, path: Path, data: dict[str, Any]) -> None:
        """Save data as JSON to a file."""
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load JSON data from a file."""
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    # Checkpoint operations
    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save a checkpoint to storage."""
        checkpoint_path = self.checkpoints_dir / f"{checkpoint.id}.json"
        self._save_json(checkpoint_path, checkpoint.model_dump())

    def load_checkpoint(self, checkpoint_id: int) -> Checkpoint | None:
        """Load a checkpoint from storage."""
        checkpoint_path = self.checkpoints_dir / f"{checkpoint_id}.json"
        if not checkpoint_path.exists():
            return None

        data = self._load_json(checkpoint_path)
        return Checkpoint(**data)

    def list_checkpoints(self) -> list[Checkpoint]:
        """List all checkpoints."""
        checkpoints = []
        for checkpoint_file in self.checkpoints_dir.glob("*.json"):
            data = self._load_json(checkpoint_file)
            checkpoint = Checkpoint(**data)
            checkpoints.append(checkpoint)
        return sorted(checkpoints, key=lambda c: c.timestamp)

    def get_next_checkpoint_id(self) -> int:
        """Get the next available checkpoint ID."""
        existing_ids = []
        for checkpoint_file in self.checkpoints_dir.glob("*.json"):
            try:
                checkpoint_id = int(checkpoint_file.stem)
                existing_ids.append(checkpoint_id)
            except ValueError:
                continue

        return max(existing_ids) + 1 if existing_ids else 1

    # File snapshot operations
    def save_file_snapshot(self, file_path: Path, content: str) -> str:
        """Save a file snapshot and return its hash."""
        content_hash = self._get_file_hash(content)
        snapshot_path = self.files_dir / content_hash

        if not snapshot_path.exists():
            with open(snapshot_path, "w") as f:
                f.write(content)

        return content_hash

    def load_file_snapshot(self, content_hash: str) -> str | None:
        """Load a file snapshot by its hash."""
        snapshot_path = self.files_dir / content_hash
        if not snapshot_path.exists():
            return None

        with open(snapshot_path) as f:
            return f.read()

    # Export operations
    def export_data(
        self,
        output_path: Path,
        format: ExportFormat,
        checkpoint_system: Any | None = None,
    ) -> None:
        """Export data in the specified format."""
        if format == ExportFormat.JSON:
            self._export_json(output_path)
        elif format == ExportFormat.MARKDOWN:
            from .checkpoint_system import CheckpointSystem

            if checkpoint_system is None:
                checkpoint_system = CheckpointSystem(self)
            self._export_markdown(output_path, checkpoint_system)
        elif format == ExportFormat.HTML:
            from .checkpoint_system import CheckpointSystem

            if checkpoint_system is None:
                checkpoint_system = CheckpointSystem(self)
            self._export_html(output_path, checkpoint_system)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, output_path: Path) -> None:
        """Export data as JSON."""
        checkpoints = self.list_checkpoints()

        export_data = {
            "checkpoints": [c.model_dump() for c in checkpoints],
            "export_timestamp": datetime.now().isoformat(),
        }

        self._save_json(output_path, export_data)

    def _export_markdown(
        self,
        output_path: Path,
        checkpoint_system: Any | None = None,
    ) -> None:
        """Export data as Markdown, showing diffs between checkpoints chronologically."""  # noqa: E501

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# CodeSnap Export\n\n")
            f.write(f"Exported on: {datetime.now().isoformat()}\n\n")

            checkpoints = self.list_checkpoints()

            # Process checkpoints
            prev_checkpoint_id = None
            for checkpoint in checkpoints:
                # Write prompt if it exists
                if checkpoint.prompt:
                    prompt = checkpoint.prompt
                    f.write(
                        f"## Prompt: {prompt.content[:50]}"
                        f"{'...' if len(prompt.content) > 50 else ''}\n\n"
                    )

                    if prompt.tags:
                        f.write(f"**Tags:** {', '.join(prompt.tags)}\n\n")

                    # Show file summary at the beginning of each checkpoint
                    if (
                        prev_checkpoint_id
                        and checkpoint_system
                        and not checkpoint.restored_from
                    ):
                        changes = checkpoint_system.compare_checkpoints(
                            prev_checkpoint_id, checkpoint.id
                        )
                        if changes:
                            f.write("### Changed Files\n\n")
                            added_files = [
                                c.file_path for c in changes if c.change_type == "added"
                            ]
                            modified_files = [
                                c.file_path
                                for c in changes
                                if c.change_type == "modified"
                            ]
                            deleted_files = [
                                c.file_path
                                for c in changes
                                if c.change_type == "deleted"
                            ]

                            if added_files:
                                f.write("**Added:**\n")
                                for file_path in added_files:
                                    f.write(f"- `{file_path}`\n")
                                f.write("\n")

                            if modified_files:
                                f.write("**Modified:**\n")
                                for file_path in modified_files:
                                    f.write(f"- `{file_path}`\n")
                                f.write("\n")

                            if deleted_files:
                                f.write("**Deleted:**\n")
                                for file_path in deleted_files:
                                    f.write(f"- `{file_path}`\n")
                                f.write("\n")

                    # If there was a previous checkpoint, show diff
                    if (
                        prev_checkpoint_id
                        and checkpoint_system
                        and not checkpoint.restored_from
                    ):
                        f.write("### Changes from previous checkpoint\n\n")
                        changes = checkpoint_system.compare_checkpoints(
                            prev_checkpoint_id, checkpoint.id
                        )
                        if changes:
                            for change in changes:
                                f.write(
                                    f"**File:** `{change.file_path}` "
                                    f"({change.change_type})\n\n"
                                )
                                if change.diff:
                                    f.write(f"```diff\n{change.diff}\n```\n\n")
                        else:
                            f.write("No changes detected.\n\n")

                # Write checkpoint info
                # Handle restore checkpoints
                if checkpoint.restored_from:
                    f.write(f"## Restore Operation: {checkpoint.name}\n\n")

                    f.write(f"**Description:** {checkpoint.description}\n\n")
                    f.write(f"**Restored from:** {checkpoint.restored_from}\n\n")
                    if checkpoint.restore_timestamp:
                        f.write(
                            f"**Restore timestamp:** {checkpoint.restore_timestamp}\n\n"
                        )
                    if checkpoint.tags:
                        f.write(f"**Tags:** {', '.join(checkpoint.tags)}\n\n")
                    f.write("---\n\n")
                elif not checkpoint.prompt:
                    # Initial checkpoint
                    f.write(f"## Initial Checkpoint: {checkpoint.name}\n\n")

                    f.write(f"**Description:** {checkpoint.description}\n\n")
                    if checkpoint.tags:
                        f.write(f"**Tags:** {', '.join(checkpoint.tags)}\n\n")

                # Only update previous checkpoint if this is not a restore checkpoint
                if not checkpoint.restored_from:
                    prev_checkpoint_id = checkpoint.id

    def _export_html(
        self,
        output_path: Path,
        checkpoint_system: Any | None = None,
    ) -> None:
        """Export data as HTML, showing diffs between checkpoints in chronological order."""  # noqa: E501

        def escape_html(text: str) -> str:
            return (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("'", "&#39;")
                .replace('"', "&quot;")
            )

        def diff_to_html(diff: str) -> str:
            lines = diff.split("\n")
            html_lines = []
            for line in lines:
                line_escaped = escape_html(line)
                if line.startswith("+"):
                    html_lines.append(
                        f'<span style="color: green;">{line_escaped}</span>'
                    )
                elif line.startswith("-"):
                    html_lines.append(
                        f'<span style="color: red;">{line_escaped}</span>'
                    )
                elif line.startswith("@"):
                    html_lines.append(
                        f'<span style="color: cyan;">{line_escaped}</span>'
                    )
                else:
                    html_lines.append(line_escaped)
            return "\n".join(html_lines)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>CodeSnap Export</title>")
            f.write(
                """<style>
                body { font-family: sans-serif; line-height: 1.6; margin: 2em; }
                h1, h2, h3, h4 { color: #333; }
                pre {
                    background: #f4f4f4; padding: 1em; border-radius: 5px;
                    white-space: pre-wrap; word-wrap: break-word;
                }
                code {
                    font-family: monospace; background: #eee;
                    padding: 0.2em 0.4em; border-radius: 3px;
                }
                .prompt-section, .checkpoint-section {
                    margin-bottom: 2em; border-bottom: 1px solid #ddd;
                    padding-bottom: 1em;
                }
                .file-summary-section {
                    margin-left: 1em;
                    margin-bottom: 1em;
                    padding: 1em;
                    background: #f9f9f9;
                    border-radius: 5px;
                }
                .diff-section { margin-left: 1em; }
            </style>"""
            )
            f.write("</head><body>")
            f.write("<h1>CodeSnap Export</h1>")
            f.write(f"<p>Exported on: {datetime.now().isoformat()}</p>")

            checkpoints = self.list_checkpoints()

            # Process checkpoints
            prev_checkpoint_id = None
            for checkpoint in checkpoints:
                # Write prompt if it exists
                if checkpoint.prompt:
                    prompt = checkpoint.prompt
                    prompt_title = prompt.content[:50] + (
                        "..." if len(prompt.content) > 50 else ""
                    )
                    f.write('<div class="prompt-section">')
                    f.write(f"<h2>Prompt: {escape_html(prompt_title)}</h2>")

                    f.write(f"<p><strong>Timestamp:</strong> {prompt.timestamp}</p>")
                    f.write("<p><strong>Content:</strong></p>")
                    f.write(f"<pre><code>{escape_html(prompt.content)}</code></pre>")
                    if prompt.tags:
                        f.write(
                            f"<p><strong>Tags:</strong> "
                            f"{escape_html(', '.join(prompt.tags))}</p>"
                        )

                    # Show file summary at the beginning of each checkpoint
                    if (
                        prev_checkpoint_id
                        and checkpoint_system
                        and not checkpoint.restored_from
                    ):
                        changes = checkpoint_system.compare_checkpoints(
                            prev_checkpoint_id, checkpoint.id
                        )
                        if changes:
                            f.write('<div class="file-summary-section">')
                            f.write("<h3>Changed Files</h3>")

                            added_files = [
                                c for c in changes if c.change_type == "added"
                            ]
                            modified_files = [
                                c for c in changes if c.change_type == "modified"
                            ]
                            deleted_files = [
                                c for c in changes if c.change_type == "deleted"
                            ]

                            if added_files:
                                f.write("<p><strong>Added:</strong></p><ul>")
                                for change in added_files:
                                    f.write(
                                        f"<li><code>{escape_html(change.file_path)}</code></li>"
                                    )
                                f.write("</ul>")

                            if modified_files:
                                f.write("<p><strong>Modified:</strong></p><ul>")
                                for change in modified_files:
                                    f.write(
                                        f"<li><code>{escape_html(change.file_path)}</code></li>"
                                    )
                                f.write("</ul>")

                            if deleted_files:
                                f.write("<p><strong>Deleted:</strong></p><ul>")
                                for change in deleted_files:
                                    f.write(
                                        f"<li><code>{escape_html(change.file_path)}</code></li>"
                                    )
                                f.write("</ul>")

                            f.write("</div>")

                    # If there was a previous checkpoint, show diff
                    if (
                        prev_checkpoint_id
                        and checkpoint_system
                        and not checkpoint.restored_from
                    ):
                        f.write('<div class="diff-section">')
                        f.write("<h3>Changes from previous checkpoint</h3>")
                        changes = checkpoint_system.compare_checkpoints(
                            prev_checkpoint_id, checkpoint.id
                        )
                        if changes:
                            for change in changes:
                                f.write(
                                    f"<p><strong>File:</strong> "
                                    f"<code>{escape_html(change.file_path)}</code>"
                                    f" ({change.change_type})</p>"
                                )
                                if change.diff:
                                    f.write(f"<pre>{diff_to_html(change.diff)}</pre>")
                        else:
                            f.write("<p>No changes detected.</p>")
                        f.write("</div>")

                    f.write("</div>")

                # Write checkpoint info
                # Handle restore checkpoints
                if checkpoint.restored_from:
                    f.write('<div class="checkpoint-section">')
                    f.write(
                        f"<h2>Restore Operation: {escape_html(checkpoint.name)}</h2>"
                    )
                    f.write(f"<p><strong>ID:</strong> {checkpoint.id}</p>")
                    f.write(
                        f"<p><strong>Timestamp:</strong> {checkpoint.timestamp}</p>"
                    )
                    f.write(
                        f"<p><strong>Description:</strong> "
                        f"{escape_html(checkpoint.description)}</p>"
                    )
                    f.write(
                        f"<p><strong>Restored from:</strong> "
                        f"{checkpoint.restored_from}</p>"
                    )
                    if checkpoint.restore_timestamp:
                        f.write(
                            f"<p><strong>Restore timestamp:</strong> "
                            f"{checkpoint.restore_timestamp}</p>"
                        )
                    if checkpoint.tags:
                        f.write(
                            f"<p><strong>Tags:</strong> "
                            f"{escape_html(', '.join(checkpoint.tags))}</p>"
                        )
                    f.write("<hr>")
                    f.write("</div>")
                elif not checkpoint.prompt:
                    # Initial checkpoint
                    f.write('<div class="checkpoint-section">')
                    f.write(
                        f"<h2>Initial Checkpoint: {escape_html(checkpoint.name)}</h2>"
                    )
                    f.write(f"<p><strong>ID:</strong> {checkpoint.id}</p>")
                    f.write(
                        f"<p><strong>Timestamp:</strong> {checkpoint.timestamp}</p>"
                    )
                    f.write(
                        f"<p><strong>Description:</strong> "
                        f"{escape_html(checkpoint.description)}</p>"
                    )
                    if checkpoint.tags:
                        f.write(
                            f"<p><strong>Tags:</strong> "
                            f"{escape_html(', '.join(checkpoint.tags))}</p>"
                        )

                    f.write("</div>")

                # Only update previous checkpoint if this is not a restore checkpoint
                if not checkpoint.restored_from:
                    prev_checkpoint_id = checkpoint.id

            f.write("</body></html>")
