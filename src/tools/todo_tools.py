"""
TODO tool for task tracking and management.
Agent can create, update, and complete tasks.
"""

from langchain_core.tools import tool
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

# Global todo state (in memory for now)
_todos: Dict[str, dict] = {}
_todo_counter = 0

TODO_DIR = Path.home() / ".reactor"
TODO_FILE = TODO_DIR / "todo_state.json"


def _load_todos():
    """Load todos from file"""
    global _todos, _todo_counter
    if TODO_FILE.exists():
        with open(TODO_FILE) as f:
            data = json.load(f)
            _todos = data.get("todos", {})
            _todo_counter = data.get("counter", 0)


def _save_todos():
    """Save todos to file"""
    # Ensure directory exists
    if not TODO_DIR.exists():
        TODO_DIR.mkdir(parents=True, exist_ok=True)

    with open(TODO_FILE, "w") as f:
        json.dump({"todos": _todos, "counter": _todo_counter}, f, indent=2)


# Load todos on import
_load_todos()


@tool
async def create_todo(title: str, description: str = "") -> Dict:
    """
    Create a new TODO task.

    Use this to track planned tasks before executing them.

    Args:
        title: Short title for the task
        description: Optional detailed description

    Returns:
        Dictionary with task details including task_id
    """
    global _todo_counter
    _todo_counter += 1
    task_id = f"task_{_todo_counter}"

    _todos[task_id] = {
        "id": task_id,
        "title": title,
        "description": description,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }

    _save_todos()

    return {
        "success": True,
        "task_id": task_id,
        "title": title,
        "message": f"Created task: {title}",
    }


@tool
async def complete_todo(task_id: str) -> Dict:
    """
    Mark a TODO task as completed.

    Args:
        task_id: ID of the task to complete

    Returns:
        Dictionary with operation status
    """
    if task_id not in _todos:
        return {
            "success": False,
            "error": f"Task {task_id} not found",
            "available_tasks": list(_todos.keys()),
        }

    _todos[task_id]["status"] = "completed"
    _todos[task_id]["completed_at"] = datetime.now().isoformat()

    _save_todos()

    return {
        "success": True,
        "task_id": task_id,
        "title": _todos[task_id]["title"],
        "message": f"Completed: {_todos[task_id]['title']}",
    }


@tool
async def list_todos(status: str = "all") -> Dict:
    """
    List all TODO tasks.

    Args:
        status: Filter by status - "all", "pending", or "completed"

    Returns:
        Dictionary with list of tasks
    """
    if status == "all":
        tasks = list(_todos.values())
    else:
        tasks = [t for t in _todos.values() if t["status"] == status]

    # Sort by creation time
    tasks.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "total_tasks": len(tasks),
        "pending": len([t for t in _todos.values() if t["status"] == "pending"]),
        "completed": len([t for t in _todos.values() if t["status"] == "completed"]),
        "tasks": tasks,
    }


@tool
async def update_todo(
    task_id: str, title: Optional[str] = None, description: Optional[str] = None
) -> Dict:
    """
    Update a TODO task's details.

    Args:
        task_id: ID of the task to update
        title: New title (optional)
        description: New description (optional)

    Returns:
        Dictionary with operation status
    """
    if task_id not in _todos:
        return {"success": False, "error": f"Task {task_id} not found"}

    if title:
        _todos[task_id]["title"] = title
    if description:
        _todos[task_id]["description"] = description

    _save_todos()

    return {
        "success": True,
        "task_id": task_id,
        "message": f"Updated task: {_todos[task_id]['title']}",
    }


def get_todos_for_ui() -> List[dict]:
    """Get todos formatted for UI display (reloads from disk to ensure sync)"""
    _load_todos()
    return list(_todos.values())


def clear_completed_todos():
    """Clear all completed todos"""
    global _todos
    _todos = {k: v for k, v in _todos.items() if v["status"] != "completed"}
    _save_todos()


def reset_todos():
    """Reset all todos (memory and disk)"""
    global _todos, _todo_counter
    _todos = {}
    _todo_counter = 0
    if TODO_FILE.exists():
        try:
            TODO_FILE.unlink()
        except:
            pass
