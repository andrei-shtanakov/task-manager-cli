# Task Tracker CLI Application - Development Instructions

## Project Overview
Build a Python CLI application for task tracking with kanban board and graph visualization capabilities using SQLite database.

## Environment Setup
- Python version: 3.11.13
- Package manager: `uv` (already installed)
- Virtual environment: already activated
- Use `uv add <package>` for installing dependencies

## Core Requirements

### Database
- Use SQLite for data persistence
- Design schema to support:
  - Tasks with properties: id, title, description, status, created_at, updated_at
  - Tags with properties: id, name, color/metadata
  - Task-tag relationships (many-to-many)
  - Task-task relationships for dependencies/links
  - Status tracking (e.g., TODO, IN_PROGRESS, DONE, BLOCKED)

### Application Structure
Organize the project with clear separation of concerns:
- Database models and schema
- CLI interface layer
- Business logic layer
- Visualization modules
- Utility functions

### CLI Commands Structure
Implement comprehensive command-line interface using a library like `typer` or `click`:

**Task Management:**
- Add new tasks with title, description, status, tags
- Update existing tasks (any field)
- Delete tasks with confirmation
- Change task status
- Link/unlink tasks to create dependencies

**Tag Management:**
- Create tags
- Update tag properties
- Delete tags (handle orphaned task associations)
- Assign tags to tasks
- Remove tags from tasks

**Viewing & Filtering:**
- Display tasks as kanban board (columns by status)
- Display tasks as dependency graph
- Filter by single or multiple tags
- Filter by date range (created/updated)
- Filter by status
- Combine multiple filters

### Visualization Requirements

**Kanban Board View:**
- Column-based layout grouped by status
- Display task ID, title, tags
- Use colors/formatting for visual distinction
- Handle terminal width gracefully

**Graph View:**
- Visualize task dependencies as directed graph
- Show task relationships clearly
- Use ASCII art or library like `graphviz` or `networkx` with matplotlib
- Include task IDs and titles in nodes
- Distinguish different relationship types if applicable

### Technical Considerations
- Input validation for all user inputs
- Proper error handling and user-friendly messages
- Confirmation prompts for destructive operations
- Support for interactive and non-interactive modes
- Use rich/colorful terminal output (consider libraries like `rich` or `colorama`)
- Implement proper database connection management
- Handle edge cases (circular dependencies, orphaned records)

### Data Integrity
- Ensure referential integrity in database
- Cascade deletions appropriately
- Validate status values
- Prevent duplicate tags
- Handle concurrent access if needed

### User Experience
- Clear, intuitive command syntax
- Helpful error messages
- Progress indicators for long operations
- Confirmation before destructive actions
- Support for both short and long command flags
- Include `--help` documentation for all commands

## Suggested Package Dependencies
Consider adding these packages via `uv add`:
- CLI framework (typer/click)
- Terminal formatting (rich/colorama)
- Database ORM or query builder (optional: sqlalchemy, or use sqlite3 directly)
- Graph visualization (networkx, graphviz, or ascii-based alternatives)
- Date handling (python-dateutil if needed)

## Development Approach
1. Start with database schema design and migrations
2. Implement core task CRUD operations
3. Add tag management functionality
4. Build relationship/dependency system
5. Implement filtering logic
6. Create kanban board visualization
7. Create graph visualization
8. Polish CLI interface and add help documentation
9. Add comprehensive error handling
10. Test edge cases and refine user experience

## Quality Standards
- Write clean, readable, well-documented code
- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Include docstrings for functions and classes
- Handle exceptions gracefully
- Validate all user inputs
- Ensure database queries are efficient

## Testing Considerations
- Test all CRUD operations
- Verify filter combinations work correctly
- Test visualization rendering with various data sets
- Validate edge cases (empty database, circular dependencies)
- Test database integrity constraints

## Deliverables
- Fully functional CLI application
- SQLite database with proper schema
- Clear command structure with help documentation
- Both kanban and graph visualization modes
- Comprehensive filtering capabilities
- Tag management system
- Task relationship/dependency system
