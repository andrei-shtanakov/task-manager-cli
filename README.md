# Task Manager CLI

Command line tool for tracking tasks with Kanban and dependency graph visualisations backed by SQLite.

## Quick start

```bash
uv sync
python main.py --help
```

A database file (`task_manager.db`) is created automatically on first use. Pass `--db-path` to use a custom location.

## Core commands

```bash
python main.py task add "Write docs" --description "Fill out README" --status TODO --tag docs
python main.py task update 1 --status IN_PROGRESS
python main.py task list --status IN_PROGRESS --tag docs
python main.py task delete 1 --yes
```

Tag helpers:

```bash
python main.py tag create backend --color blue
python main.py tag list
python main.py tag assign 2 urgent
python main.py tag remove 2 urgent
```

Link tasks to model dependencies:

```bash
python main.py task link 3 1
python main.py task unlink 3 1
```

## Visualisations

- `python main.py view kanban` renders a colourised Kanban board grouped by status.
- `python main.py view graph` shows task dependencies as an ASCII graph.

Both views honour `--status` and `--tag` filters where applicable.

## Status values

The default workflow includes `TODO`, `IN_PROGRESS`, `BLOCKED`, and `DONE`. Additional statuses can be added directly in the `task_statuses` table if needed.

## Data integrity and safety

- Foreign keys and cascading rules keep task-tag links consistent.
- Circular dependencies are prevented when linking tasks.
- Destructive commands require confirmation unless `--yes` is supplied.

## Development notes

- Python 3.11+
- Dependencies managed with `uv`
- Uses [Typer](https://typer.tiangolo.com) and [Rich](https://rich.readthedocs.io) for the CLI experience.

Run `uv run python main.py ...` if you prefer to execute commands through `uv`.
