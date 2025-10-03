"""ASCII graph rendering for task dependencies."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

from ..models import Task, TaskLink


def render_graph(tasks: Iterable[Task], links: Iterable[TaskLink]) -> Panel:
    task_map = {task.id: task for task in tasks if task.id is not None}
    children: dict[int, list[int]] = defaultdict(list)
    parents: dict[int, set[int]] = defaultdict(set)

    for link in links:
        if link.from_task_id in task_map and link.to_task_id in task_map:
            children[link.from_task_id].append(link.to_task_id)
            parents[link.to_task_id].add(link.from_task_id)

    roots = [task_id for task_id in task_map if task_id not in parents]
    if not roots:
        # Fallback to all tasks to avoid an empty tree (should only happen if no links)
        roots = list(task_map.keys())

    tree = Tree("[bold]Task Dependencies[/bold]")
    visited_global: set[int] = set()

    for root_id in sorted(roots):
        _build_tree(tree, root_id, task_map, children, visited_global, set())

    # Include tasks that might be disconnected or already visited via other branches
    remaining = [task_id for task_id in task_map if task_id not in visited_global]
    for task_id in sorted(remaining):
        label = _format_task_label(task_map[task_id])
        tree.add(label)
        visited_global.add(task_id)

    return Panel(tree, border_style="cyan", padding=(1, 1))


def _build_tree(
    tree: Tree,
    task_id: int,
    task_map: dict[int, Task],
    children: dict[int, list[int]],
    visited_global: set[int],
    path: set[int],
) -> None:
    label = _format_task_label(task_map[task_id])
    branch = tree.add(label)
    if task_id in path:
        branch.add(Text("Cycle detected", style="red"))
        return

    visited_global.add(task_id)
    path.add(task_id)
    for child_id in sorted(children.get(task_id, [])):
        if child_id in path:
            branch.add(Text("Cycle detected", style="red"))
            continue
        if child_id not in task_map:
            branch.add(Text(f"Missing task {child_id}", style="yellow"))
            continue
        _build_tree(branch, child_id, task_map, children, visited_global, set(path))


def _format_task_label(task: Task) -> str:
    tag_text = ", ".join(tag.name for tag in task.tags) if task.tags else ""
    label = f"[bold]{task.id}[/bold]: {task.title} [dim]({task.status})[/dim]"
    if tag_text:
        label += f"\n[green]{tag_text}[/green]"
    return label
