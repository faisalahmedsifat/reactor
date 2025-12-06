from typing import TypedDict, Annotated, Optional, List, Sequence
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
