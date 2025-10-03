"""Business logic for managing tasks, tags, and relationships."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable

from .db import Database
from .models import Tag, Task, TaskFilters, TaskLink
from .repositories import StatusRepository, TagRepository, TaskLinkRepository, TaskRepository


@dataclass(slots=True)
class ServiceContext:
    tasks: TaskRepository
    tags: TagRepository
    statuses: StatusRepository
    links: TaskLinkRepository


class TagService:
    def __init__(self, ctx: ServiceContext) -> None:
        self.ctx = ctx

    def create(self, name: str, color: str | None = None) -> Tag:
        try:
            return self.ctx.tags.create(name, color)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Tag '{name}' already exists") from exc

    def update(self, tag_id: int, name: str | None = None, color: str | None = None) -> Tag:
        try:
            return self.ctx.tags.update(tag_id, name, color)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Tag name already exists") from exc

    def delete(self, tag_id: int) -> None:
        self.ctx.tags.delete(tag_id)

    def assign_to_task(self, task_id: int, tag_name: str) -> Task:
        tag = self.ensure_tag(tag_name)
        if tag.id is None:
            raise RuntimeError("Tag ID missing after creation")
        self.ctx.tags.assign_to_task(task_id, tag.id)
        task = self.ctx.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return task

    def remove_from_task(self, task_id: int, tag_name: str) -> Task:
        tag = self.ctx.tags.get_by_name(tag_name)
        if tag is None:
            raise ValueError(f"Unknown tag '{tag_name}'")
        if tag.id is None:
            raise RuntimeError("Tag ID missing")
        self.ctx.tags.remove_from_task(task_id, tag.id)
        task = self.ctx.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return task

    def ensure_tag(self, name: str, color: str | None = None) -> Tag:
        existing = self.ctx.tags.get_by_name(name)
        if existing:
            return existing
        return self.create(name, color=color)

    def list_tags(self) -> list[Tag]:
        return self.ctx.tags.list()


class TaskService:
    def __init__(self, ctx: ServiceContext, tag_service: TagService | None = None) -> None:
        self.ctx = ctx
        self.tag_service = tag_service or TagService(ctx)

    def create_task(
        self,
        title: str,
        description: str,
        status: str,
        tag_names: Iterable[str] | None = None,
    ) -> Task:
        self._validate_status(status)
        tag_ids = []
        for name in tag_names or []:
            tag = self.tag_service.ensure_tag(name)
            if tag.id is None:
                raise RuntimeError("Tag ID missing after creation")
            tag_ids.append(tag.id)
        return self.ctx.tasks.create(title, description, status, tag_ids)

    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        tag_names: Iterable[str] | None = None,
    ) -> Task:
        if status is not None:
            self._validate_status(status)
        task = self.ctx.tasks.update(task_id, title, description, status)
        if tag_names is not None:
            tag_ids = []
            for name in tag_names:
                tag = self.tag_service.ensure_tag(name)
                if tag.id is None:
                    raise RuntimeError("Tag ID missing after creation")
                tag_ids.append(tag.id)
            self.ctx.tasks.set_tags(task_id, tag_ids)
            task = self.ctx.tasks.get(task_id)
        return task

    def delete_task(self, task_id: int) -> None:
        self.ctx.tasks.delete(task_id)

    def change_status(self, task_id: int, status: str) -> Task:
        self._validate_status(status)
        return self.ctx.tasks.update(task_id, status=status)

    def get_task(self, task_id: int) -> Task:
        task = self.ctx.tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return task

    def list_tasks(self, filters: TaskFilters | None = None) -> list[Task]:
        return self.ctx.tasks.list(filters)

    def list_links(self) -> list[TaskLink]:
        return self.ctx.links.list()

    def link_tasks(self, from_task_id: int, to_task_id: int, link_type: str = "dependency") -> TaskLink:
        if from_task_id == to_task_id:
            raise ValueError("Cannot link a task to itself")
        self.ensure_tasks_exist([from_task_id, to_task_id])
        if self._creates_cycle(from_task_id, to_task_id):
            raise ValueError("Link would create a circular dependency")
        try:
            return self.ctx.links.create(from_task_id, to_task_id, link_type)
        except sqlite3.IntegrityError as exc:
            raise ValueError("Link already exists") from exc

    def unlink_tasks(self, from_task_id: int, to_task_id: int, link_type: str = "dependency") -> None:
        self.ctx.links.delete(from_task_id, to_task_id, link_type)

    def ensure_tasks_exist(self, task_ids: Iterable[int]) -> None:
        missing = [task_id for task_id in task_ids if self.ctx.tasks.get(task_id) is None]
        if missing:
            raise ValueError(f"Unknown task(s): {', '.join(map(str, missing))}")

    def _validate_status(self, status: str) -> None:
        if not self.ctx.statuses.exists(status):
            valid = ", ".join(self.ctx.statuses.list())
            raise ValueError(f"Invalid status '{status}'. Valid statuses: {valid}")

    def _creates_cycle(self, from_task_id: int, to_task_id: int) -> bool:
        # Depth-first search from the destination towards its dependents.
        stack = [to_task_id]
        visited: set[int] = set()
        while stack:
            current = stack.pop()
            if current == from_task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(self.ctx.links.dependents_of(current))
        return False


def build_services(database: Database) -> tuple[TaskService, TagService]:
    status_repo = StatusRepository(database)
    tag_repo = TagRepository(database)
    task_repo = TaskRepository(database)
    link_repo = TaskLinkRepository(database)
    ctx = ServiceContext(tasks=task_repo, tags=tag_repo, statuses=status_repo, links=link_repo)
    tag_service = TagService(ctx)
    task_service = TaskService(ctx, tag_service=tag_service)
    return task_service, tag_service
