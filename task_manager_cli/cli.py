"""Typer-based command line interface for the task manager."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .db import get_database
from .models import Status, TaskFilters
from .services import TaskService, TagService, build_services
from .visualization.kanban import render_kanban
from .visualization.graph import render_graph

app = typer.Typer(help="Task tracker CLI with kanban and graph views.")
task_app = typer.Typer(help="Task management commands")
tag_app = typer.Typer(help="Tag management commands")
view_app = typer.Typer(help="Visualization commands")
app.add_typer(task_app, name="task")
app.add_typer(tag_app, name="tag")
app.add_typer(view_app, name="view")


@dataclass(slots=True)
class AppState:
    console: Console
    db_path: Path
    task_service: TaskService
    tag_service: TagService


def get_state(ctx: typer.Context) -> AppState:
    if ctx.obj is None:
        raise typer.BadParameter("Application state not initialised")
    return ctx.obj


@app.callback()
def main(
    ctx: typer.Context,
    db_path: Path = typer.Option(
        Path("task_manager.db"),
        help="Path to the SQLite database file.",
    ),
) -> None:
    database = get_database(str(db_path))
    task_service, tag_service = build_services(database)
    ctx.obj = AppState(
        console=Console(),
        db_path=db_path,
        task_service=task_service,
        tag_service=tag_service,
    )


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(
            "Dates must be ISO formatted, e.g. 2024-05-01 or 2024-05-01T15:30:00"
        ) from exc


def _render_task_table(tasks) -> Table:
    table = Table(title="Tasks", show_lines=False)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Title", style="bold")
    table.add_column("Status", style="magenta")
    table.add_column("Tags", style="green")
    table.add_column("Updated", style="dim")
    for task in tasks:
        tags = ", ".join(tag.name for tag in task.tags) if task.tags else "-"
        table.add_row(
            str(task.id),
            task.title,
            task.status,
            tags,
            task.updated_at.isoformat(timespec="minutes"),
        )
    return table


@task_app.command("add")
def add_task(
    ctx: typer.Context,
    title: str = typer.Argument(..., help="Title of the task"),
    description: str = typer.Option("", "--description", "-d", help="Task description"),
    status: Status = typer.Option(
        Status.TODO,
        "--status",
        "-s",
        help="Initial status",
        case_sensitive=False,
    ),
    tags: Optional[list[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Tag(s) to associate with the task",
    ),
) -> None:
    state = get_state(ctx)
    try:
        task = state.task_service.create_task(title, description, status.value, tags or [])
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Created task {task.id}[/green]")
    state.console.print(_render_task_table([task]))


@task_app.command("update")
def update_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="ID of the task to update"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    description: Optional[str] = typer.Option(None, "--description", help="New description"),
    status: Optional[Status] = typer.Option(
        None,
        "--status",
        "-s",
        help="New status",
        case_sensitive=False,
    ),
    tags: Optional[list[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Replace tags with the provided list",
    ),
) -> None:
    state = get_state(ctx)
    try:
        task = state.task_service.update_task(
            task_id,
            title,
            description,
            status.value if status else None,
            tags,
        )
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    if task is None:
        state.console.print(f"[yellow]Task {task_id} not found[/yellow]")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Updated task {task.id}[/green]")
    state.console.print(_render_task_table([task]))


@task_app.command("delete")
def delete_task(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="ID of the task to remove"),
    force: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    state = get_state(ctx)
    if not force:
        if not typer.confirm(f"Delete task {task_id}? This cannot be undone."):
            raise typer.Exit()
    state.task_service.delete_task(task_id)
    state.console.print(f"[green]Task {task_id} deleted[/green]")


@task_app.command("status")
def change_status(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
    status: Status = typer.Argument(..., help="New status", show_default=False),
) -> None:
    state = get_state(ctx)
    try:
        task = state.task_service.change_status(task_id, status.value)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Updated task {task.id} status to {task.status}[/green]")


@task_app.command("list")
def list_tasks(
    ctx: typer.Context,
    status: list[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    tag: list[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    created_after: Optional[str] = typer.Option(None, help="Filter tasks created on/after date"),
    created_before: Optional[str] = typer.Option(None, help="Filter tasks created on/before date"),
    updated_after: Optional[str] = typer.Option(None, help="Filter tasks updated on/after date"),
    updated_before: Optional[str] = typer.Option(None, help="Filter tasks updated on/before date"),
) -> None:
    state = get_state(ctx)
    filters = TaskFilters(
        statuses=[s.upper() for s in status or []],
        tag_names=tag or [],
        created_after=_parse_datetime(created_after),
        created_before=_parse_datetime(created_before),
        updated_after=_parse_datetime(updated_after),
        updated_before=_parse_datetime(updated_before),
    )
    tasks = state.task_service.list_tasks(filters)
    if not tasks:
        state.console.print("[yellow]No tasks found with the given filters.[/yellow]")
        return
    state.console.print(_render_task_table(tasks))


@task_app.command("link")
def link_tasks(
    ctx: typer.Context,
    from_task: int = typer.Argument(..., help="Task that depends on another"),
    to_task: int = typer.Argument(..., help="Dependency task"),
    link_type: str = typer.Option("dependency", help="Type of relationship"),
) -> None:
    state = get_state(ctx)
    try:
        link = state.task_service.link_tasks(from_task, to_task, link_type)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(
        f"[green]Linked task {link.from_task_id} -> {link.to_task_id} ({link.type})[/green]"
    )


@task_app.command("unlink")
def unlink_tasks(
    ctx: typer.Context,
    from_task: int = typer.Argument(..., help="Task that had a dependency"),
    to_task: int = typer.Argument(..., help="Dependent task"),
    link_type: str = typer.Option("dependency", help="Type of relationship"),
) -> None:
    state = get_state(ctx)
    state.task_service.unlink_tasks(from_task, to_task, link_type)
    state.console.print(
        f"[green]Unlinked task {from_task} -> {to_task} ({link_type})[/green]"
    )


@tag_app.command("create")
def create_tag(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Tag name"),
    color: Optional[str] = typer.Option(None, "--color", help="Optional color metadata"),
) -> None:
    state = get_state(ctx)
    try:
        tag = state.tag_service.create(name, color)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Created tag {tag.name} (id={tag.id})[/green]")


@tag_app.command("update")
def update_tag(
    ctx: typer.Context,
    tag_id: int = typer.Argument(..., help="Tag ID"),
    name: Optional[str] = typer.Option(None, "--name", help="New tag name"),
    color: Optional[str] = typer.Option(None, "--color", help="New color metadata"),
) -> None:
    state = get_state(ctx)
    try:
        tag = state.tag_service.update(tag_id, name, color)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Updated tag {tag.id}[/green]: {tag.name} ({tag.color or 'no color'})")


@tag_app.command("delete")
def delete_tag(
    ctx: typer.Context,
    tag_id: int = typer.Argument(..., help="Tag ID"),
    force: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    state = get_state(ctx)
    if not force:
        if not typer.confirm(f"Delete tag {tag_id}? Associations will be removed."):
            raise typer.Exit()
    state.tag_service.delete(tag_id)
    state.console.print(f"[green]Deleted tag {tag_id}[/green]")


@tag_app.command("list")
def list_tags(ctx: typer.Context) -> None:
    state = get_state(ctx)
    tags = state.tag_service.list_tags()
    if not tags:
        state.console.print("[yellow]No tags defined yet.[/yellow]")
        return
    table = Table(title="Tags")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Color", style="green")
    for tag in tags:
        table.add_row(str(tag.id), tag.name, tag.color or "-")
    state.console.print(table)


@tag_app.command("assign")
def assign_tag(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
    tag_name: str = typer.Argument(..., help="Existing or new tag name"),
) -> None:
    state = get_state(ctx)
    try:
        task = state.tag_service.assign_to_task(task_id, tag_name)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Assigned tag '{tag_name}' to task {task_id}[/green]")
    state.console.print(_render_task_table([task]))


@tag_app.command("remove")
def remove_tag(
    ctx: typer.Context,
    task_id: int = typer.Argument(..., help="Task ID"),
    tag_name: str = typer.Argument(..., help="Tag name to remove"),
) -> None:
    state = get_state(ctx)
    try:
        task = state.tag_service.remove_from_task(task_id, tag_name)
    except ValueError as exc:
        state.console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)
    state.console.print(f"[green]Removed tag '{tag_name}' from task {task_id}[/green]")
    state.console.print(_render_task_table([task]))


@view_app.command("kanban")
def view_kanban(
    ctx: typer.Context,
    status: list[str] = typer.Option(None, "--status", "-s", help="Filter statuses"),
    tag: list[str] = typer.Option(None, "--tag", "-t", help="Filter tags"),
) -> None:
    state = get_state(ctx)
    filters = TaskFilters(
        statuses=[s.upper() for s in status or []],
        tag_names=tag or [],
    )
    tasks = state.task_service.list_tasks(filters)
    state.console.print(render_kanban(tasks))


@view_app.command("graph")
def view_graph(ctx: typer.Context) -> None:
    state = get_state(ctx)
    tasks = state.task_service.list_tasks()
    links = state.task_service.list_links()
    if not tasks:
        state.console.print("[yellow]No tasks available to graph.[/yellow]")
        return
    state.console.print(render_graph(tasks, links))
