from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .checkpoint_system import CheckpointSystem
from .models import ExportFormat, Prompt
from .storage import StorageManager


def format_id(checkpoint_id: int | str, short: bool = True) -> str:
    """Format checkpoint ID for display.

    Args:
        checkpoint_id: The checkpoint ID to format
        short: If True, show minimal format; if False, show padded format

    Returns:
        Formatted ID string
    """
    if isinstance(checkpoint_id, str):
        return checkpoint_id
    return str(checkpoint_id)


def _resolve_checkpoint_id(storage: StorageManager, checkpoint_ref: str) -> int | None:
    """Resolve checkpoint reference (ID or name) to checkpoint ID.

    Args:
        storage: StorageManager instance
        checkpoint_ref: Checkpoint ID or name

    Returns:
        Checkpoint ID if found, None otherwise
    """
    # Try to parse as integer ID
    try:
        checkpoint_id = int(checkpoint_ref)
        checkpoint = storage.load_checkpoint(checkpoint_id)
        if checkpoint:
            return checkpoint.id
    except ValueError:
        pass

    # Try to find by name
    checkpoints = storage.list_checkpoints()
    for checkpoint in checkpoints:
        if checkpoint.name == checkpoint_ref:
            return checkpoint.id

    # If not found, show error
    console.print(f"[red]Checkpoint '{checkpoint_ref}' not found.[/red]")
    console.print("Available checkpoints:")
    for checkpoint in checkpoints:
        console.print(f"  - {checkpoint.name} (ID: {format_id(checkpoint.id)})")

    return None


console = Console()


@click.group()
@click.version_option()
def main():
    """CodeSnap - AI coding process recording and log generation system.

    Simple workflow:
      codesnap start "your prompt here"    # Start AI coding session
      # AI modifies code based on prompt
      codesnap start "next prompt"         # Start next session
      codesnap list                        # View all sessions
      codesnap diff 1 2                    # Compare sessions
    """
    pass


@main.command()
@click.argument("prompt", type=str)
@click.option("--tag", "tags", multiple=True, help="Tags to associate with this prompt")
@click.option(
    "--description", "-d", type=str, default="", help="Description for the checkpoint"
)
def start(
    prompt: str,
    tags: list[str],
    description: str,
):
    """Start AI coding session with a prompt and create checkpoint."""
    # Initialize components
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    # Check if project is initialized (has existing checkpoints)
    existing_checkpoints = storage.list_checkpoints()

    # Create the prompt
    prompt_obj = Prompt(
        content=prompt,
        tags=list(tags),
    )

    if not existing_checkpoints:
        console.print(
            "[yellow]No project found. Creating initial checkpoint...[/yellow]"
        )
        # Create initial checkpoint with the user's prompt
        checkpoint = checkpoint_system.create_checkpoint(
            description=description or "",
            tags=list(tags),
            prompt=prompt_obj,
        )
        console.print(
            f"[green]Initial checkpoint created: {format_id(checkpoint.id)}[/green]"
        )
    else:
        # Create the checkpoint with the prompt
        checkpoint = checkpoint_system.create_checkpoint(
            description=description or "",
            tags=list(tags),
            prompt=prompt_obj,
        )

    console.print("[green]AI coding session started![/green]")
    console.print(f"Prompt: {prompt}")
    console.print(f"Checkpoint ID: {format_id(checkpoint.id)}")
    console.print("[blue]Now you can make your code changes...[/blue]")


# Prompts command removed - prompts are now embedded in checkpoints


@main.command()
def list_cmd():
    """List checkpoints."""
    storage = StorageManager()
    # Show checkpoints list
    checkpoints_list = storage.list_checkpoints()

    if not checkpoints_list:
        console.print("[yellow]No checkpoints found.[/yellow]")
        return

    table = Table(title="Checkpoints")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Description", style="green")
    table.add_column("Timestamp", style="blue")
    table.add_column("Tags", style="red")

    for checkpoint in checkpoints_list:
        description = (
            checkpoint.description[:50] + "..."
            if len(checkpoint.description) > 50
            else checkpoint.description
        )
        tags = ", ".join(checkpoint.tags) if checkpoint.tags else ""

        table.add_row(
            format_id(checkpoint.id),
            checkpoint.name,
            description,
            checkpoint.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            tags,
        )

    console.print(table)


@main.command()
@click.argument("checkpoint1_id", type=str, required=False)
@click.argument("checkpoint2_id", type=str, required=False)
@click.option(
    "--current", "-c", is_flag=True, help="Compare with current project state"
)
def diff(checkpoint1_id: str | None, checkpoint2_id: str | None, current: bool):
    """Compare checkpoints or compare with current state."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    if current:
        # Compare checkpoint with current state
        if not checkpoint1_id:
            console.print("[red]Checkpoint ID is required when using --current[/red]")
            return

        # Resolve checkpoint name to ID if necessary
        resolved_id = _resolve_checkpoint_id(storage, checkpoint1_id)
        if not resolved_id:
            return

        changes = checkpoint_system.compare_with_current(resolved_id)

        if not changes:
            console.print(
                "[yellow]No differences found between checkpoint and current state.[/yellow]"  # noqa: E501
            )
            return

        console.print(
            f"[bold]Comparing checkpoint "
            f"{format_id(checkpoint1_id, short=False)} with current state[/bold]"
        )
        console.print(f"Found {len(changes)} changed files:\n")

        for change in changes:
            console.print(
                Panel(
                    f"[bold]{change.file_path}[/bold] ({change.change_type})",
                    title="File",
                )
            )

            if change.diff:
                console.print(change.diff)
            console.print()
    else:
        # Compare two checkpoints
        if not checkpoint1_id or not checkpoint2_id:
            console.print("[red]Two checkpoint IDs are required for comparison[/red]")
            return

        # Resolve checkpoint names to IDs if necessary
        resolved_id1 = _resolve_checkpoint_id(storage, checkpoint1_id)
        resolved_id2 = _resolve_checkpoint_id(storage, checkpoint2_id)

        if not resolved_id1 or not resolved_id2:
            return

        changes = checkpoint_system.compare_checkpoints(resolved_id1, resolved_id2)

        if not changes:
            console.print("[yellow]No differences found between checkpoints.[/yellow]")
            return

        console.print(
            f"[bold]Comparing checkpoints "
            f"{format_id(checkpoint1_id, short=False)} and "
            f"{format_id(checkpoint2_id, short=False)}[/bold]"
        )
        console.print(f"Found {len(changes)} changed files:\n")

        for change in changes:
            console.print(
                Panel(
                    f"[bold]{change.file_path}[/bold] ({change.change_type})",
                    title="File",
                )
            )

            if change.diff:
                console.print(change.diff)


@main.command()
@click.argument("output_path", type=click.Path())
@click.option(
    "--format",
    "-f",
    type=click.Choice([format_type.value for format_type in ExportFormat]),
    default=ExportFormat.MARKDOWN.value,
    help="Export format (default: markdown)",
)
def export(output_path: str, format_str: str):
    """Export data to a file."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    output_file = Path(output_path)
    export_format = ExportFormat(format_str)

    try:
        storage.export_data(output_file, export_format, checkpoint_system)
        console.print(f"[green]Data exported successfully to {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]Export failed: {str(e)}[/red]")


@main.command()
@click.argument("checkpoint_id", type=str)
@click.option(
    "--output", "-o", type=click.Path(), help="Output directory for restored files"
)
def restore(checkpoint_id: str, output: str | None):
    """Restore a checkpoint."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    # Resolve checkpoint name to ID if necessary
    resolved_id = _resolve_checkpoint_id(storage, checkpoint_id)
    if not resolved_id:
        return

    checkpoint = storage.load_checkpoint(resolved_id)
    if not checkpoint:
        console.print(
            f"[red]Checkpoint {format_id(resolved_id, short=False)} not found."
        )
        return

    restore_path = Path(output) if output else None

    try:
        success = checkpoint_system.restore_checkpoint(resolved_id, restore_path)
        if success:
            console.print(
                f"[green]Checkpoint '{checkpoint.name}' restored successfully![/green]"
            )
            if output:
                console.print(f"Files restored to: {output}")
        else:
            console.print(
                f"[red]Failed to restore checkpoint "
                f"{format_id(resolved_id, short=False)}.[/red]"
            )
    except Exception as e:
        console.print(f"[red]Restore failed: {str(e)}[/red]")


if __name__ == "__main__":
    main()
