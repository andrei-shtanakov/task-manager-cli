"""Domain models and constants for the task manager CLI."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Iterable


class Status(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"

    @classmethod
    def list(cls) -> list[str]:
        return [status.value for status in cls]


@dataclass(slots=True)
class Tag:
    id: int | None
    name: str
    color: str | None = None


@dataclass(slots=True)
class Task:
    id: int | None
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    tags: list[Tag] = field(default_factory=list)


@dataclass(slots=True)
class TaskLink:
    id: int | None
    from_task_id: int
    to_task_id: int
    type: str = "dependency"


@dataclass(slots=True)
class TaskFilters:
    statuses: list[str] = field(default_factory=list)
    tag_names: list[str] = field(default_factory=list)
    created_after: datetime | None = None
    created_before: datetime | None = None
    updated_after: datetime | None = None
    updated_before: datetime | None = None

    @classmethod
    def from_iterables(
        cls,
        statuses: Iterable[str] | None = None,
        tags: Iterable[str] | None = None,
    ) -> "TaskFilters":
        return cls(
            statuses=list(statuses or []),
            tag_names=list(tags or []),
        )
