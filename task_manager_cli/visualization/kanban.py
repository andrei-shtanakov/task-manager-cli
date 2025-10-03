"""Kanban board rendering using rich."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from ..models import Status, Task

STATUS_COLORS = {
    Status.TODO.value: "bright_blue",
    Status.IN_PROGRESS.value: "yellow",
    Status.BLOCKED.value: "red",
    Status.DONE.value: "green",
}


def render_kanban(tasks: Iterable[Task]) -> Columns:
    tasks_by_status: dict[str, list[Task]] = defaultdict(list)
    for task in tasks:
        tasks_by_status[task.status].append(task)

    columns = []
    for status in Status.list():
        column = _build_status_column(status, tasks_by_status.get(status, []))
        columns.append(column)
    return Columns(columns, expand=True)


def _build_status_column(status: str, tasks: list[Task]) -> Panel:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_column("Task", overflow="fold")
    if not tasks:
        table.add_row("[dim italic]No tasks[/dim italic]")
    else:
        for task in sorted(tasks, key=lambda t: t.updated_at, reverse=True):
            tag_text = ", ".join(tag.name for tag in task.tags) if task.tags else ""
            meta = f"[dim]#{task.id}[/dim] {task.title}"
            if tag_text:
                meta += f"\n[green]{tag_text}[/green]"
            table.add_row(meta)
    return Panel(
        table,
        title=f"[bold]{status}[/bold]",
        border_style=STATUS_COLORS.get(status, "white"),
        padding=(1, 1),
    )
