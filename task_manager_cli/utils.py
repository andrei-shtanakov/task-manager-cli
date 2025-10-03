"""Utility helpers for the task manager CLI."""
from __future__ import annotations

from datetime import datetime

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def utc_now() -> datetime:
    return datetime.utcnow()


def format_ts(value: datetime) -> str:
    return value.strftime(DATETIME_FORMAT)


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FORMAT)
