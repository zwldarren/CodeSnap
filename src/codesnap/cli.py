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
    """CodeSnap - AI coding process recording and log generation system."""
    pass


@main.command()
@click.option("--tag", "tags", multiple=True, help="Tags to associate with prompts")
@click.option(
    "--description", "-d", type=str, default="", help="Description for checkpoints"
)
def start(tags: list[str], description: str):
    """Start AI coding session with interactive prompt input."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    console.print("[bold green]CodeSnap Interactive Mode[/bold green]")

    # Check if there are existing checkpoints
    existing_checkpoints = storage.list_checkpoints()
    if not existing_checkpoints:
        console.print("No existing checkpoints found. Creating initial checkpoint...")
        # Create first checkpoint immediately when starting (only for new projects)
        initial_checkpoint = checkpoint_system.create_initial_checkpoint(
            description="Initial checkpoint before any changes"
        )
        console.print(
            f"[green]Initial checkpoint created: {format_id(initial_checkpoint.id)}[/green]"  # noqa: E501
        )
    else:
        console.print(f"Found {len(existing_checkpoints)} existing checkpoint(s).")

    console.print("Enter prompts and press Enter to create checkpoints.")
    console.print("Press Ctrl+C or type 'exit' to quit.\n")

    while True:
        try:
            # Get prompt from user
            prompt_text = click.prompt("Enter prompt")

            if prompt_text.lower() in ["exit", "quit", "q"]:
                console.print("[yellow]Exiting interactive mode...[/yellow]")
                break

            if not prompt_text.strip():
                console.print("[yellow]Prompt cannot be empty. Try again.[/yellow]")
                continue

            # Create prompt object
            prompt_obj = Prompt(
                content=prompt_text,
                tags=list(tags),
            )

            console.print(f"Prompt: {prompt_text}")
            console.print(
                "[blue]Make your code changes, then press Enter to create checkpoint...[/blue]"  # noqa: E501
            )

            # Wait for user to press Enter after making changes
            input()

            # Create second checkpoint AFTER user has made changes
            checkpoint = checkpoint_system.create_checkpoint(
                description=description or "",
                tags=list(tags),
                prompt=prompt_obj,
            )

            console.print(
                f"[green]Checkpoint created: {format_id(checkpoint.id)}[/green]"
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Exiting interactive mode...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            continue


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
def export(output_path: str, format: str):
    """Export data to a file."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    output_file = Path(output_path)
    export_format = ExportFormat(format)

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
