"""Database repositories encapsulating CRUD operations."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from .db import Database
from .models import Status, Tag, Task, TaskFilters, TaskLink
from .utils import format_ts, parse_ts, utc_now


class StatusRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def list(self) -> list[str]:
        rows = self.db.query("SELECT name FROM task_statuses ORDER BY position ASC")
        return [row["name"] for row in rows]

    def exists(self, name: str) -> bool:
        row = self.db.query_one(
            "SELECT 1 FROM task_statuses WHERE name = ?",
            (name,),
        )
        return row is not None


class TagRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, name: str, color: str | None) -> Tag:
        self.db.execute(
            "INSERT INTO tags(name, color) VALUES(?, ?)",
            (name.strip(), color),
        )
        row = self.db.query_one("SELECT id, name, color FROM tags WHERE name = ?", (name.strip(),))
        return Tag(id=row["id"], name=row["name"], color=row["color"])

    def update(self, tag_id: int, name: str | None = None, color: str | None = None) -> Tag:
        updates = []
        params: list = []
        if name is not None:
            updates.append("name = ?")
            params.append(name.strip())
        if color is not None:
            updates.append("color = ?")
            params.append(color)
        if not updates:
            row = self.db.query_one("SELECT id, name, color FROM tags WHERE id = ?", (tag_id,))
            if row is None:
                raise ValueError(f"Tag {tag_id} not found")
            return Tag(id=row["id"], name=row["name"], color=row["color"])
        params.append(tag_id)
        self.db.execute(
            f"UPDATE tags SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        row = self.db.query_one("SELECT id, name, color FROM tags WHERE id = ?", (tag_id,))
        if row is None:
            raise ValueError(f"Tag {tag_id} not found")
        return Tag(id=row["id"], name=row["name"], color=row["color"])

    def delete(self, tag_id: int) -> None:
        self.db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))

    def assign_to_task(self, task_id: int, tag_id: int) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO task_tags(task_id, tag_id) VALUES(?, ?)",
            (task_id, tag_id),
        )

    def remove_from_task(self, task_id: int, tag_id: int) -> None:
        self.db.execute(
            "DELETE FROM task_tags WHERE task_id = ? AND tag_id = ?",
            (task_id, tag_id),
        )

    def get_by_name(self, name: str) -> Tag | None:
        row = self.db.query_one("SELECT id, name, color FROM tags WHERE name = ?", (name.strip(),))
        if row is None:
            return None
        return Tag(id=row["id"], name=row["name"], color=row["color"])

    def list(self) -> list[Tag]:
        rows = self.db.query("SELECT id, name, color FROM tags ORDER BY name ASC")
        return [Tag(id=row["id"], name=row["name"], color=row["color"]) for row in rows]


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        title: str,
        description: str,
        status: str,
        tag_ids: Iterable[int] | None = None,
    ) -> Task:
        now = utc_now()
        created = format_ts(now)
        self.db.execute(
            """
            INSERT INTO tasks(title, description, status, created_at, updated_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (title.strip(), description.strip(), status, created, created),
        )
        row = self.db.query_one(
            "SELECT id, title, description, status, created_at, updated_at FROM tasks WHERE rowid = last_insert_rowid()"
        )
        if row is None:
            raise RuntimeError("Failed to create task")
        task_id = row["id"]
        for tag_id in tag_ids or []:
            self.db.execute(
                "INSERT OR IGNORE INTO task_tags(task_id, tag_id) VALUES(?, ?)",
                (task_id, tag_id),
            )
        return self._row_to_task(row, self._tags_for_task_ids([task_id]).get(task_id, []))

    def update(
        self,
        task_id: int,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
    ) -> Task:
        updates = []
        params: list = []
        if title is not None:
            updates.append("title = ?")
            params.append(title.strip())
        if description is not None:
            updates.append("description = ?")
            params.append(description.strip())
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if not updates:
            row = self.get_row(task_id)
            if row is None:
                raise ValueError(f"Task {task_id} not found")
            return self._row_to_task(row, self._tags_for_task_ids([task_id]).get(task_id, []))
        updates.append("updated_at = ?")
        params.append(format_ts(utc_now()))
        params.append(task_id)
        self.db.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        row = self.get_row(task_id)
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        return self._row_to_task(row, self._tags_for_task_ids([task_id]).get(task_id, []))

    def delete(self, task_id: int) -> None:
        self.db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def get(self, task_id: int) -> Task | None:
        row = self.get_row(task_id)
        if row is None:
            return None
        tags = self._tags_for_task_ids([task_id]).get(task_id, [])
        return self._row_to_task(row, tags)

    def list(self, filters: TaskFilters | None = None) -> list[Task]:
        filters = filters or TaskFilters()
        where_clauses: list[str] = []
        params: list = []

        if filters.statuses:
            placeholders = ",".join("?" for _ in filters.statuses)
            where_clauses.append(f"t.status IN ({placeholders})")
            params.extend(filters.statuses)

        if filters.created_after:
            where_clauses.append("t.created_at >= ?")
            params.append(format_ts(filters.created_after))
        if filters.created_before:
            where_clauses.append("t.created_at <= ?")
            params.append(format_ts(filters.created_before))
        if filters.updated_after:
            where_clauses.append("t.updated_at >= ?")
            params.append(format_ts(filters.updated_after))
        if filters.updated_before:
            where_clauses.append("t.updated_at <= ?")
            params.append(format_ts(filters.updated_before))

        if filters.tag_names:
            placeholders = ",".join("?" for _ in filters.tag_names)
            where_clauses.append(
                (
                    "t.id IN ("
                    "    SELECT task_id FROM task_tags tt"
                    "    JOIN tags tg ON tg.id = tt.tag_id"
                    "    WHERE tg.name IN ({})"
                    "    GROUP BY task_id"
                    "    HAVING COUNT(DISTINCT tg.name) = ?"
                    ")"
                ).format(placeholders)
            )
            params.extend(filters.tag_names)
            params.append(len(filters.tag_names))

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
            SELECT t.id, t.title, t.description, t.status, t.created_at, t.updated_at
            FROM tasks t
            {where_sql}
            ORDER BY t.updated_at DESC
        """
        rows = self.db.query(query, params)
        task_ids = [row["id"] for row in rows]
        tags_map = self._tags_for_task_ids(task_ids)
        return [self._row_to_task(row, tags_map.get(row["id"], [])) for row in rows]

    def set_tags(self, task_id: int, tag_ids: Sequence[int]) -> None:
        self.db.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
        for tag_id in tag_ids:
            self.db.execute(
                "INSERT OR IGNORE INTO task_tags(task_id, tag_id) VALUES(?, ?)",
                (task_id, tag_id),
            )

    def _tags_for_task_ids(self, task_ids: Iterable[int]) -> dict[int, list[Tag]]:
        ids = list(task_ids)
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        rows = self.db.query(
            f"""
            SELECT t.id as task_id, tg.id as tag_id, tg.name, tg.color
            FROM tasks t
            JOIN task_tags tt ON tt.task_id = t.id
            JOIN tags tg ON tg.id = tt.tag_id
            WHERE t.id IN ({placeholders})
            ORDER BY tg.name ASC
            """,
            ids,
        )
        tags_map: dict[int, list[Tag]] = defaultdict(list)
        for row in rows:
            tags_map[row["task_id"]].append(
                Tag(id=row["tag_id"], name=row["name"], color=row["color"])
            )
        return tags_map

    def get_row(self, task_id: int):
        return self.db.query_one(
            "SELECT id, title, description, status, created_at, updated_at FROM tasks WHERE id = ?",
            (task_id,),
        )

    @staticmethod
    def _row_to_task(row, tags: list[Tag]) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            created_at=parse_ts(row["created_at"]),
            updated_at=parse_ts(row["updated_at"]),
            tags=tags,
        )


class TaskLinkRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, from_task_id: int, to_task_id: int, link_type: str = "dependency") -> TaskLink:
        self.db.execute(
            """
            INSERT INTO task_links(from_task_id, to_task_id, type)
            VALUES(?, ?, ?)
            """,
            (from_task_id, to_task_id, link_type),
        )
        row = self.db.query_one(
            """
            SELECT id, from_task_id, to_task_id, type
            FROM task_links
            WHERE rowid = last_insert_rowid()
            """
        )
        if row is None:
            raise RuntimeError("Failed to create link")
        return TaskLink(
            id=row["id"],
            from_task_id=row["from_task_id"],
            to_task_id=row["to_task_id"],
            type=row["type"],
        )

    def delete(self, from_task_id: int, to_task_id: int, link_type: str = "dependency") -> None:
        self.db.execute(
            "DELETE FROM task_links WHERE from_task_id = ? AND to_task_id = ? AND type = ?",
            (from_task_id, to_task_id, link_type),
        )

    def list(self, task_ids: Iterable[int] | None = None) -> list[TaskLink]:
        params: list = []
        where_sql = ""
        if task_ids:
            ids = list(task_ids)
            placeholders = ",".join("?" for _ in ids)
            where_sql = f"WHERE from_task_id IN ({placeholders}) OR to_task_id IN ({placeholders})"
            params.extend(ids)
            params.extend(ids)
        rows = self.db.query(
            f"SELECT id, from_task_id, to_task_id, type FROM task_links {where_sql}",
            params,
        )
        return [
            TaskLink(
                id=row["id"],
                from_task_id=row["from_task_id"],
                to_task_id=row["to_task_id"],
                type=row["type"],
            )
            for row in rows
        ]

    def dependents_of(self, task_id: int) -> list[int]:
        rows = self.db.query(
            "SELECT to_task_id FROM task_links WHERE from_task_id = ?",
            (task_id,),
        )
        return [row["to_task_id"] for row in rows]

    def dependencies_of(self, task_id: int) -> list[int]:
        rows = self.db.query(
            "SELECT from_task_id FROM task_links WHERE to_task_id = ?",
            (task_id,),
        )
        return [row["from_task_id"] for row in rows]
