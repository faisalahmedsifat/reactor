"""
src/graph_simple.py

Simplified LangGraph workflow that mimics Claude Code behavior.
Simple flow: Understand → Use Tools → Respond
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.state import ShellAgentState
from src.tools import shell_tools, file_tools, web_tools, todo_tools, grep_and_log_tools, agent_tools
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
import os


from src.nodes.thinking_nodes import thinking_node
from src.nodes.agent_nodes import agent_node


def create_simple_shell_agent(exclude_agent_tools: bool = False):
    """Build simplified LangGraph similar to Claude Code
    
    Args:
        exclude_agent_tools: If True, excludes agent management tools (spawn_agent, etc.).
                            Set to True for sub-agents to prevent recursive spawning.
    """

    workflow = StateGraph(ShellAgentState)

    # ============= TOOLS =============
    # Base tools available to all agents
    base_tools = [
        shell_tools.get_system_info,
        shell_tools.execute_shell_command,
        shell_tools.validate_command_safety,
        file_tools.read_file_content,
        file_tools.write_file,
        file_tools.modify_file,
        file_tools.apply_multiple_edits,
        file_tools.list_project_files,
        file_tools.search_in_files,
        web_tools.web_search,
        web_tools.recursive_crawl,
        todo_tools.create_todo,
        todo_tools.complete_todo,
        todo_tools.list_todos,
        todo_tools.update_todo,
        grep_and_log_tools.grep_advanced,
        grep_and_log_tools.tail_file,
        grep_and_log_tools.parse_log_file,
        grep_and_log_tools.extract_json_fields,
        grep_and_log_tools.filter_command_output,
        grep_and_log_tools.analyze_error_logs,
    ]
    
    # Agent management tools - only for main agent, not sub-agents
    agent_management_tools = [
        agent_tools.spawn_agent,
        agent_tools.get_agent_result,
        agent_tools.list_available_agents,
        agent_tools.list_running_agents,
        agent_tools.stop_agent,
    ]
    
    # Build final tool list based on context
    if exclude_agent_tools:
        all_tools = base_tools  # Sub-agents: no delegation capability
    else:
        all_tools = base_tools + agent_management_tools  # Main agent: full capabilities

    # ============= NODES =============

    workflow.add_node("thinking", thinking_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))

    # ============= EDGES =============

    # Start with thinking
    workflow.set_entry_point("thinking")

    # After thinking, let agent select tools
    workflow.add_edge("thinking", "agent")

    # Conditional: After agent, either use tools or finish
    workflow.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "thinking": "thinking", "end": END}
    )

    # After using tools, check if we should end immediately (e.g., spawn_agent) or continue thinking
    workflow.add_conditional_edges(
        "tools", should_continue_after_tools, {"thinking": "thinking", "end": END}
    )

    # ============= COMPILATION =============

    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)


    return compiled


# ============= NODE FUNCTIONS =============





def should_continue_after_tools(state: ShellAgentState) -> Literal["thinking", "end"]:
    """
    Determine routing after tools execute.
    
    CRITICAL: If spawn_agent was just called, END immediately without thinking.
    This prevents the infinite analysis loop.
    """
    messages = state["messages"]
    
    # Check the last few messages for spawn_agent tool calls
    for msg in reversed(messages[-5:]):  # Check last 5 messages
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                # Tool calls can be dicts or objects
                tool_name = tool_call.get("name") if isinstance(tool_call, dict) else getattr(tool_call, "name", None)
                if tool_name == "spawn_agent":
                    # spawn_agent was just called - terminate immediately
                    print("[DEBUG] Detected spawn_agent in history, ending immediately")
                    return "end"
    
    # Default: continue to thinking for analysis
    return "thinking"


def should_continue(state: ShellAgentState) -> Literal["tools", "end"]:
    """Determine if we should continue to tools or end"""
    messages = state["messages"]
    last_message = messages[-1]

    # If the last message has tool calls, continue to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    # If the agent explicitly indicates completion, end
    content = getattr(last_message, "content", "") or ""
    
    # Handle list content (common with some providers or multimodal)
    if isinstance(content, list):
        text_content = ""
        for block in content:
            if isinstance(block, dict):
                text_content += block.get("text", "")
            elif isinstance(block, str):
                text_content += block
            elif hasattr(block, "text"):
                text_content += block.text
        content = text_content
    
    # If the agent returned content (text) without tools, we consider the turn complete
    # This avoids infinite loops like "Hi" -> "Thinking" -> "Hi"
    if content and str(content).strip():
        return "end"

    # Fallback: If no tools and no content (or just whitespace), END to prevent infinite loop
    # The agent might have nothing to say or is confused. Better to stop than loop.
    return "end"


# ============= EXECUTION HELPER =============


async def run_simple_agent(
    user_request: str, 
    thread_id: str = "default",
    agent_name: str = None,
    skill_names: list = None
):
    """
    Run simplified agent with optional agent and skills.
    
    Args:
        user_request: User's request
        thread_id: Thread ID for conversation tracking
        agent_name: Optional agent name to use
        skill_names: Optional list of skill names
    """

    graph = create_simple_shell_agent()

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
        "execution_mode": "sequential",
        "max_retries": 3,
        "analysis_data": None,
        "active_agent": agent_name,  # New: agent name
        "active_skills": skill_names or [],  # New: skill names
    }

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    print(f"🚀 Starting agent for: {user_request}\n")

    # Stream execution
    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            print(f"\n{'='*60}")
            print(f"[{node_name.upper()}]")
            print("=" * 60)

            if "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]
                print(
                    last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                )

    print("\n✅ Agent completed successfully")


# Usage
if __name__ == "__main__":
    import asyncio

    async def main():
        await run_simple_agent("What is the current weather in London?")

    asyncio.run(main())
