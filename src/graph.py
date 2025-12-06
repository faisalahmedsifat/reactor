"""
src/graph.py

Proper graph compilation with all features
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.nodes.llm_nodes import (
    llm_parse_intent_node,
    llm_generate_plan_node, 
    llm_analyze_error_node,
    llm_reflection_node
)
from src.nodes.communication_nodes import (
    communicate_understanding_node,
    communicate_plan_node,
    stream_progress_node
)
from src.nodes.analysis_nodes import (
    discover_files_node,
    read_relevant_files_node,
    analyze_and_summarize_node
)
from src.nodes.approval_nodes import request_approval_node
from src.nodes.refinement_nodes import refine_command_node
from src.tools import shell_tools
from src.state import ShellAgentState
from src.models import RiskLevel
from langchain_core.messages import HumanMessage, AIMessage


def create_complete_shell_agent():
    """Build complete LangGraph with all features"""
    
    workflow = StateGraph(ShellAgentState)
    
    # ============= NODES =============
    
    # System nodes
    workflow.add_node("gather_system_info", gather_system_info_node)
    
    # LLM reasoning nodes
    workflow.add_node("llm_parse_intent", llm_parse_intent_node)
    workflow.add_node("llm_generate_plan", llm_generate_plan_node)
    workflow.add_node("llm_analyze_error", llm_analyze_error_node)
    workflow.add_node("llm_reflection", llm_reflection_node)
    
    # Communication nodes (NEW: conversational agent)
    workflow.add_node("communicate_understanding", communicate_understanding_node)
    workflow.add_node("communicate_plan", communicate_plan_node)
    workflow.add_node("stream_progress", stream_progress_node)
    
    # Analysis nodes (NEW: analytical workflow)
    workflow.add_node("discover_files", discover_files_node)
    workflow.add_node("read_relevant_files", read_relevant_files_node)
    workflow.add_node("analyze_and_summarize", analyze_and_summarize_node)
    
    # Execution nodes
    workflow.add_node("refine_command", refine_command_node)
    workflow.add_node("validate_safety", validate_safety_node)
    workflow.add_node("request_approval", request_approval_node)
    workflow.add_node("execute_command", execute_command_node)
    workflow.add_node("summarize", summarize_node)
    
    # ============= EDGES =============
    
    workflow.set_entry_point("gather_system_info")
    
    # Linear flow for preparation WITH COMMUNICATION
    workflow.add_edge("gather_system_info", "llm_parse_intent")
    workflow.add_edge("llm_parse_intent", "communicate_understanding")  # NEW: Communicate first!
    
    # ROUTING: Analytical vs Execution flow
    workflow.add_conditional_edges(
        "communicate_understanding",
        route_after_understanding,
        {
            "analytical_flow": "discover_files",  # NEW: Analytical path
            "execution_flow": "llm_generate_plan"  # Original execution path
        }
    )
    
    # === ANALYTICAL FLOW ===
    workflow.add_edge("discover_files", "read_relevant_files")
    workflow.add_edge("read_relevant_files", "analyze_and_summarize")
    workflow.add_edge("analyze_and_summarize", "summarize")  # Skip to final summary
    
    # === EXECUTION FLOW ===
    workflow.add_edge("llm_generate_plan", "communicate_plan")  # NEW: Show plan before execution
    workflow.add_edge("communicate_plan", "refine_command")
    workflow.add_edge("refine_command", "validate_safety")
    
    # Conditional: Safety check
    workflow.add_conditional_edges(
        "validate_safety",
        route_after_validation,
        {
            "request_approval": "request_approval",
            "execute_command": "execute_command"
        }
    )
    
    # After approval, execute
    workflow.add_edge("request_approval", "execute_command")
    
    # NEW: Stream progress after each execution
    workflow.add_edge("execute_command", "stream_progress")
    
    # Conditional: Execution result (FROM stream_progress now)
    workflow.add_conditional_edges(
        "stream_progress",
        route_after_execution,
        {
            "llm_analyze_error": "llm_analyze_error",  # Use LLM analysis!
            "next_command": "refine_command",
            "complete": "llm_reflection"  # Final reflection
        }
    )
    
    # Conditional: Error analysis
    workflow.add_conditional_edges(
        "llm_analyze_error",
        route_after_error_analysis,
        {
            "retry": "execute_command",
            "give_up": "llm_reflection"
        }
    )
    
    # Final summary
    workflow.add_edge("llm_reflection", "summarize")
    workflow.add_edge("summarize", END)
    
    # ============= COMPILATION =============
    
    # Use MemorySaver for simplicity (SQLite needs context manager)
    checkpointer = MemorySaver()
    
    # Compile with interrupts BEFORE specific nodes
    compiled = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["request_approval"],  # Pause before approval
        interrupt_after=[]
    )
    
    # Save the graph as a PNG (optional, don't fail if it doesn't work)
    try:
        image = compiled.get_graph().draw_mermaid_png()
        with open("shell_agent_graph.png", "wb") as f:
            f.write(image)
    except Exception:
        # Silently ignore graph rendering errors (API might be down)
        pass
    
    return compiled


# ============= ROUTING FUNCTIONS =============

def route_after_understanding(state: ShellAgentState) -> Literal["analytical_flow", "execution_flow"]:
    """Route to analytical or execution flow based on intent"""
    intent = state["intent"]
    
    if not intent:
        return "execution_flow"  # Default to execution
    
    # Check if analytical
    if intent.is_analytical or intent.category in ["analysis", "information_gathering", "code_review"]:
        return "analytical_flow"
    
    return "execution_flow"


def route_after_validation(state: ShellAgentState) -> Literal["request_approval", "execute_command"]:
    """Route after safety validation - AUTO-SKIP APPROVAL FOR SAFE COMMANDS"""
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    
    # Check if current command is safe (auto-execute)
    if idx < len(plan.commands):
        current_cmd = plan.commands[idx]
        # Auto-execute if safe risk level
        if hasattr(current_cmd.risk_level, 'value'):
            risk = current_cmd.risk_level.value.lower()
        else:
            risk = str(current_cmd.risk_level).lower()
        
        if risk == "safe":
            return "execute_command"
    
    # Original approval logic for moderate/dangerous commands
    if state["requires_approval"] and not state["approved"]:
        return "request_approval"
    return "execute_command"


def route_after_execution(state: ShellAgentState) -> Literal["llm_analyze_error", "next_command", "complete"]:
    """Route after command execution"""
    last_result = state["results"][-1] if state["results"] else None
    
    if not last_result:
        return "complete"
    
    # Success - check if more commands
    if last_result.success:
        plan = state["execution_plan"]
        idx = state["current_command_index"]
        
        if idx >= len(plan.commands):
            return "complete"
        return "next_command"
    
    # Failure - analyze or give up (use configurable max_retries)
    max_retries = state.get("max_retries", 3)
    if state["retry_count"] >= max_retries:
        return "complete"
    
    return "llm_analyze_error"


def route_after_error_analysis(state: ShellAgentState) -> Literal["retry", "give_up"]:
    """Route after error analysis - use configurable max_retries"""
    max_retries = state.get("max_retries", 3)
    if state["retry_count"] >= max_retries:
        return "give_up"
    
    # Check if LLM suggested a retry
    # (This would be set by llm_analyze_error_node)
    last_message = state["messages"][-1].content if state["messages"] else ""
    
    if "should_retry" in last_message.lower():
        return "retry"
    
    return "give_up"


# ============= EXECUTION HELPERS =============

async def run_agent_interactive(user_request: str, thread_id: str = "default"):
    """Run agent with interactive approval"""
    
    graph = create_complete_shell_agent()
    
    initial_state = {
        "messages": [HumanMessage(content=user_request)],
        "user_input": user_request,
        "system_info": None,
        "intent": None,
        "execution_plan": None,
        "current_command_index": 0,
        "results": [],
        "retry_count": 0,
        "requires_approval": False,
        "approved": False,
        "error": None,
        "execution_mode": "sequential",  # Default to sequential
        "max_retries": 3,  # Default max retries
        "analysis_data": None  # For analytical workflow
    }
    
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50
    }
    
    print(f"🚀 Starting agent for: {user_request}\n")
    
    # Stream execution
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            print(f"\n{'='*60}")
            print(f"[{node_name.upper()}]")
            print('='*60)
            
            if "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]
                print(last_msg.content)
    
    # Check if interrupted
    state = await graph.aget_state(config)
    
    if state.next:
        print("\n⏸️  Execution paused for approval")
        print("Run `resume_agent(thread_id, approval)` to continue")
    else:
        print("\n✅ Agent completed successfully")


async def resume_agent(thread_id: str, approval: bool):
    """Resume interrupted agent execution"""
    
    graph = create_complete_shell_agent()
    config = {"configurable": {"thread_id": thread_id}}
    
    # Update state with approval
    await graph.aupdate_state(
        config,
        {"approved": approval, "requires_approval": False}
    )
    
    # Continue execution
    async for event in graph.astream(None, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            print(f"\n[{node_name}]")
            if "messages" in node_output:
                print(node_output["messages"][-1].content)


# ============= HELPER NODES =============

async def gather_system_info_node(state: ShellAgentState) -> ShellAgentState:
    """Gather system information"""
    info = await shell_tools.get_system_info.ainvoke({})
    state["system_info"] = info
    state["messages"].append(
        AIMessage(content=f"System: {info['os_type']} | Shell: {info['shell_type']} | Dir: {info['working_directory']}")
    )
    return state


async def validate_safety_node(state: ShellAgentState) -> ShellAgentState:
    """Validate command safety"""
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    
    if idx >= len(plan.commands):
        return state
    
    current_cmd = plan.commands[idx]
    
    safety = await shell_tools.validate_command_safety.ainvoke({
        "command": current_cmd.cmd
    })
    
    state["requires_approval"] = safety["requires_approval"]
    
    if safety["warnings"]:
        state["messages"].append(
            AIMessage(content=f"⚠️  Safety warnings: {', '.join(safety['warnings'])}")
        )
    
    return state


async def execute_command_node(state: ShellAgentState) -> ShellAgentState:
    """Execute shell command"""
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    system_info = state["system_info"]
    
    if idx >= len(plan.commands):
        return state
    
    current_cmd = plan.commands[idx]
    
    result = await shell_tools.execute_shell_command.ainvoke({
        "command": current_cmd.cmd,
        "working_directory": system_info["working_directory"],
        "timeout": 30,
        "dry_run": False
    })
    
    from src.models import ExecutionResult
    from datetime import datetime
    
    exec_result = ExecutionResult(
        command=current_cmd.cmd,
        success=result["success"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        timestamp=datetime.now()
    )
    
    state["results"].append(exec_result)
    
    if result["success"]:
        state["messages"].append(
            AIMessage(content=f"✅ Success: {current_cmd.cmd}\n{result['stdout'][:300]}")
        )
        state["current_command_index"] += 1
        state["retry_count"] = 0
    else:
        state["error"] = result["stderr"]
        state["messages"].append(
            AIMessage(content=f"❌ Failed: {current_cmd.cmd}\n{result['stderr'][:300]}")
        )
    
    return state


async def summarize_node(state: ShellAgentState) -> ShellAgentState:
    """Final summary"""
    results = state["results"]
    total = len(results)
    successful = sum(1 for r in results if r.success)
    
    if total == 0:
        summary = "\nEXECUTION SUMMARY\n" + "="*60 + "\nNo commands were executed.\n"
    else:
        cmd_list = "\n".join([f"  {'[OK]' if r.success else '[FAIL]'} {r.command}" for r in results])
        summary = f"""
EXECUTION SUMMARY
{'='*60}
Total Commands: {total}
Successful: {successful}
Failed: {total - successful}
Success Rate: {successful/total*100:.1f}%

Commands Executed:
{cmd_list}
"""
    
    state["messages"].append(AIMessage(content=summary))
    return state


# Usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        await run_agent_interactive(
            "Create a Python project with venv and install pytest"
        )
    
    asyncio.run(main())