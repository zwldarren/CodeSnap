from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .checkpoint_system import CheckpointSystem
from .models import ExportFormat, Prompt, PromptType
from .storage import StorageManager


def format_uuid(uuid_str: str, short: bool = True) -> str:
    """Format UUID for display.

    Args:
        uuid_str: The UUID string to format
        short: If True, show first 8 chars; if False, show first 12 chars

    Returns:
        Formatted UUID string
    """
    if short:
        return uuid_str[:8]
    else:
        return uuid_str[:12]


def _resolve_checkpoint_id(storage: StorageManager, checkpoint_ref: str) -> str | None:
    """Resolve checkpoint reference (ID or name) to checkpoint ID.

    Args:
        storage: StorageManager instance
        checkpoint_ref: Checkpoint ID (full or partial) or name

    Returns:
        Full checkpoint ID if found, None otherwise
    """
    # Try to find by exact ID match first
    checkpoint = storage.load_checkpoint(checkpoint_ref)
    if checkpoint:
        return checkpoint.id

    # Try to find by partial ID match (first 8 or 12 characters)
    for checkpoint_file in storage.checkpoints_dir.glob("*.json"):
        data = storage._load_json(checkpoint_file)
        checkpoint_id = data.get("id", "")
        if checkpoint_id.startswith(checkpoint_ref):
            return checkpoint_id

    # Try to find by name
    checkpoints = storage.list_checkpoints()
    for checkpoint in checkpoints:
        if checkpoint.name == checkpoint_ref:
            return checkpoint.id

    # If not found, show error
    console.print(f"[red]Checkpoint '{checkpoint_ref}' not found.[/red]")
    console.print("Available checkpoints:")
    for checkpoint in checkpoints:
        console.print(f"  - {checkpoint.name} (ID: {format_uuid(checkpoint.id)})")

    return None


console = Console()


@click.group()
@click.version_option()
def main():
    """CodeSnap - AI coding process recording and log generation system."""
    pass


@main.command()
@click.option(
    "--name", "-n", type=str, default="Initial", help="Name for the initial checkpoint"
)
@click.option(
    "--description",
    "-d",
    type=str,
    default="Initial checkpoint",
    help="Description for the initial checkpoint",
)
def init(name: str, description: str):
    """Create an initial checkpoint without a prompt."""
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    # Check if project is already initialized
    existing_checkpoints = storage.list_checkpoints()
    if existing_checkpoints:
        console.print("[red]Project is already initialized![/red]")
        console.print(f"Found {len(existing_checkpoints)} existing checkpoint(s).")
        console.print("Use 'codesnap create' to create new checkpoints instead.")
        return

    # Create the initial checkpoint
    checkpoint = checkpoint_system.create_initial_checkpoint(
        name=name, description=description
    )

    console.print("[green]Initial checkpoint created![/green]")
    console.print(f"Checkpoint ID: {format_uuid(checkpoint.id)}")
    console.print(f"Checkpoint Name: {checkpoint.name}")


@main.command()
@click.argument("prompt", type=str)
@click.option(
    "--type",
    "-t",
    type=click.Choice([t.value for t in PromptType]),
    default=PromptType.OTHER.value,
    help="Type of prompt",
)
@click.option("--tag", "tags", multiple=True, help="Tags to associate with this prompt")
@click.option("--name", "-n", type=str, help="Name for the checkpoint")
@click.option(
    "--description", "-d", type=str, default="", help="Description for the checkpoint"
)
def create(
    prompt: str,
    type: str,
    tags: list[str],
    name: str | None,
    description: str,
):
    """Create a checkpoint with a prompt representing AI agent modifications."""
    # Initialize components
    storage = StorageManager()
    checkpoint_system = CheckpointSystem(storage)

    # Create the prompt
    prompt_obj = Prompt(
        content=prompt,
        prompt_type=PromptType(type),
        tags=list(tags),
    )

    # Generate a checkpoint name if not provided
    if not name:
        name = f"Checkpoint {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    # Create the checkpoint with the prompt
    checkpoint = checkpoint_system.create_checkpoint(
        name=name, description=description, tags=list(tags), prompt=prompt_obj
    )

    console.print("[green]Checkpoint created with prompt![/green]")
    console.print(f"Checkpoint ID: {format_uuid(checkpoint.id)}")


# Prompts command removed - prompts are now embedded in checkpoints


@main.command()
@click.option(
    "--status",
    "-s",
    type=click.Choice(["active", "archived", "deleted"]),
    default="active",
    help="Filter by checkpoint status",
)
@click.option(
    "--branches",
    "-b",
    is_flag=True,
    help="Show branches and their checkpoints in a tree view",
)
def list_cmd(status: str, branches: bool):
    """List checkpoints or branches."""
    storage = StorageManager()

    if branches:
        # Show branches and their checkpoints
        branches_list = storage.list_branches()
        checkpoints_list = storage.list_checkpoints()

        if not branches_list:
            console.print("[yellow]No branches found.[/yellow]")
            return

        # Group checkpoints by branch
        branch_checkpoints: dict = {}
        for checkpoint in checkpoints_list:
            if checkpoint.branch_id:
                if checkpoint.branch_id not in branch_checkpoints:
                    branch_checkpoints[checkpoint.branch_id] = []
                branch_checkpoints[checkpoint.branch_id].append(checkpoint)

        console.print("[bold]Branch Tree View[/bold]")
        console.print("=" * 50)

        for branch in branches_list:
            # Show branch info
            branch_color = "green" if branch.status == "active" else "yellow"
            console.print(
                f"\n[{branch_color}]Branch: {branch.name}[/{branch_color}]"
                f" (ID: {format_uuid(branch.id)})"
            )
            if branch.description:
                console.print(f"  Description: {branch.description}")
            console.print(
                f"  Created: {branch.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Show checkpoints for this branch
            if branch.id in branch_checkpoints:
                branch_cps = sorted(
                    branch_checkpoints[branch.id], key=lambda c: c.timestamp
                )
                for i, checkpoint in enumerate(branch_cps):
                    prefix = "├── " if i < len(branch_cps) - 1 else "└── "
                    checkpoint_color = "cyan" if checkpoint.restored_from else "white"

                    if checkpoint.restored_from:
                        restored_from = next(
                            (
                                cp
                                for cp in checkpoints_list
                                if cp.id == checkpoint.restored_from
                            ),
                            None,
                        )
                        restored_from_name = (
                            restored_from.name if restored_from else "unknown"
                        )
                        restored_info = (
                            f" (restored from {format_uuid(checkpoint.restored_from)}"
                            f" - {restored_from_name})"
                        )
                        console.print(
                            f"  {prefix}[{checkpoint_color}]{checkpoint.name}"
                            f"[/{checkpoint_color}]{restored_info}"
                        )
                    else:
                        console.print(
                            f"  {prefix}[{checkpoint_color}]{checkpoint.name}"
                            f"[/{checkpoint_color}]"
                        )

                    console.print(f"      ID: {format_uuid(checkpoint.id)}")
                    console.print(
                        f"      Time: "
                        f"{checkpoint.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    if checkpoint.tags:
                        console.print(f"      Tags: {', '.join(checkpoint.tags)}")
            else:
                console.print("  └── [dim]No checkpoints[/dim]")

            console.print()
    else:
        # Show checkpoints list
        checkpoints_list = storage.list_checkpoints(status)

        if not checkpoints_list:
            console.print(f"[yellow]No {status} checkpoints found.[/yellow]")
            return

        table = Table(title=f"Checkpoints ({status})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Prompt", style="yellow")
        table.add_column("Timestamp", style="blue")
        table.add_column("Tags", style="red")

        for checkpoint in checkpoints_list:
            description = (
                checkpoint.description[:50] + "..."
                if len(checkpoint.description) > 50
                else checkpoint.description
            )
            prompt_content = (
                checkpoint.prompt.content[:30] + "..."
                if checkpoint.prompt and len(checkpoint.prompt.content) > 30
                else (checkpoint.prompt.content if checkpoint.prompt else "No prompt")
            )
            tags = ", ".join(checkpoint.tags) if checkpoint.tags else ""

            table.add_row(
                format_uuid(checkpoint.id),
                checkpoint.name,
                description,
                prompt_content,
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

        changes = checkpoint_system.compare_with_current_rich(resolved_id)

        if not changes:
            console.print(
                "[yellow]No differences found between checkpoint and current state.[/yellow]"  # noqa: E501
            )
            return

        console.print(
            f"[bold]Comparing checkpoint "
            f"{format_uuid(checkpoint1_id, short=False)} with current state[/bold]"
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
            f"{format_uuid(checkpoint1_id, short=False)} and "
            f"{format_uuid(checkpoint2_id, short=False)}[/bold]"
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
    type=click.Choice([f.value for f in ExportFormat]),
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
            f"[red]Checkpoint {format_uuid(resolved_id, short=False)} not found."
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
                f"{format_uuid(resolved_id, short=False)}.[/red]"
            )
    except Exception as e:
        console.print(f"[red]Restore failed: {str(e)}[/red]")


if __name__ == "__main__":
    main()
