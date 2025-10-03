"""Database utilities for the task manager CLI."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Iterable, Sequence

DEFAULT_STATUSES = [
    ("TODO", 1),
    ("IN_PROGRESS", 2),
    ("BLOCKED", 3),
    ("DONE", 4),
]


class Database:
    """Lightweight wrapper around sqlite3 for the application."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON;")
        return self._connection

    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self.connect()
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
        with self.cursor() as cur:
            cur.execute(sql, params or [])

    def executemany(self, sql: str, param_list: Iterable[Sequence[Any]]) -> None:
        with self.cursor() as cur:
            cur.executemany(sql, param_list)

    def query(self, sql: str, params: Sequence[Any] | None = None) -> list[sqlite3.Row]:
        with self.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchall()

    def query_one(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> sqlite3.Row | None:
        with self.cursor() as cur:
            cur.execute(sql, params or [])
            return cur.fetchone()

    def initialize(self) -> None:
        """Create tables and ensure default statuses exist."""
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS task_statuses (
                name TEXT PRIMARY KEY,
                position INTEGER NOT NULL UNIQUE
            );
            """
        )

        self.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT NOT NULL REFERENCES task_statuses(name) ON UPDATE CASCADE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        self.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT DEFAULT NULL
            );
            """
        )

        self.execute(
            """
            CREATE TABLE IF NOT EXISTS task_tags (
                task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (task_id, tag_id)
            );
            """
        )

        self.execute(
            """
            CREATE TABLE IF NOT EXISTS task_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                to_task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                type TEXT NOT NULL DEFAULT 'dependency',
                UNIQUE(from_task_id, to_task_id, type),
                CHECK(from_task_id <> to_task_id)
            );
            """
        )

        existing_statuses = {
            row["name"]
            for row in self.query("SELECT name FROM task_statuses")
        }
        missing = [(name, pos) for name, pos in DEFAULT_STATUSES if name not in existing_statuses]
        if missing:
            self.executemany(
                "INSERT INTO task_statuses(name, position) VALUES (?, ?)", missing
            )


def get_database(path: str | None = None) -> Database:
    """Factory returning an initialised Database instance."""
    db_path = Path(path or "task_manager.db")
    database = Database(db_path)
    database.initialize()
    return database
