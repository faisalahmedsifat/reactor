from dataclasses import dataclass, field
from typing import Optional, List, Set, Literal
from enum import Enum
from pathlib import Path


class AgentState(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class TUIState:
    """Central state data structure"""

    # Active View
    active_tab: str = "agent"
    sidebar_visible: bool = True

    # File System
    current_file: Optional[Path] = None
    project_root: Path = field(default_factory=lambda: Path.cwd())

    # Agent
    agent_status: AgentState = AgentState.IDLE
    execution_mode: Literal["sequential", "parallel"] = (
        "sequential"  # NEW: execution mode toggle
    )

    # Search
    search_query: str = ""
