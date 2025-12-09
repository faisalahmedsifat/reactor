from typing import TypedDict, Annotated, Optional, List, Sequence, Literal, Dict, Any
from typing import TypedDict, Annotated, Optional, List, Sequence, Literal, Dict, Any
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from src.models import CommandIntent, ExecutionPlan, ExecutionResult


class ShellAgentState(TypedDict):
    """LangGraph state for shell automation"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_input: str
    system_info: Optional[dict]
    intent: Optional[CommandIntent]
    execution_plan: Optional[ExecutionPlan]
    current_command_index: int
    results: List[ExecutionResult]
    retry_count: int
    requires_approval: bool
    approved: bool
    error: Optional[str]
    execution_mode: Literal["sequential", "parallel"]  # New: execution mode toggle
    max_retries: int  # New: configurable retry limit
    analysis_data: Optional[Dict[str, Any]]  # New: for analytical workflow
    active_agent: Optional[str]  # New: current agent name
    active_skills: List[str]  # New: active skill names
