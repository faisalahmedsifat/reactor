from typing import TypedDict, Annotated, Optional, List, Sequence, Literal, Dict, Any
from typing import TypedDict, Annotated, Optional, List, Sequence, Literal, Dict, Any
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from src.models import CommandIntent, ExecutionPlan, ExecutionResult


class ShellAgentState(TypedDict, total=False):
    """LangGraph state for shell automation"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_input: str
    system_info: Optional[dict]
    intent: Optional[CommandIntent]
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
    next_step: Optional[str]  # New: next step to execute

    # Enhanced analysis state for multi-file projects
    project_context: Optional[Dict[str, Any]]  # Project structure and metadata
    files_analyzed: List[str]  # Track which files have been analyzed
    analysis_phase: Literal[
        "discovery", "analysis", "synthesis", "complete"
    ]  # Current analysis phase

    # AST-aware fields for intelligent code analysis
    ast_cache: Optional[Dict[str, Any]]  # Parsed ASTs by file
    dependency_graph: Optional[Dict[str, List[str]]]  # File dependencies
    function_index: Optional[Dict[str, List[Dict[str, Any]]]]  # Functions by file
    class_index: Optional[Dict[str, List[Dict[str, Any]]]]  # Classes by file
    import_graph: Optional[Dict[str, List[str]]]  # Import relationships
    ast_analysis_enabled: bool  # Whether AST analysis is available
