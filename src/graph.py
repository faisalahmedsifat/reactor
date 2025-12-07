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
from src.tools import shell_tools, file_tools, web_tools, todo_tools, grep_and_log_tools, git_tools
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
import os


from src.nodes.thinking_nodes import thinking_node
from src.nodes.agent_nodes import agent_node


def create_simple_shell_agent():
    """Build simplified LangGraph similar to Claude Code"""

    workflow = StateGraph(ShellAgentState)

    # ============= TOOLS =============
    # Combine all tools into one list
    all_tools = [
        shell_tools.get_system_info,
        shell_tools.execute_shell_command,
        shell_tools.validate_command_safety,
        file_tools.read_file_content,
        file_tools.write_file,
        file_tools.modify_file,
        file_tools.list_project_files,
        file_tools.search_in_files,  # grep-like search
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
        # Git Tools
        git_tools.git_status,
        git_tools.git_log,
        git_tools.git_diff,
        git_tools.git_branch_list,
        git_tools.git_checkout,
        git_tools.git_commit,
        git_tools.git_show,
    ]

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

    # After using tools, go back to thinking to analyze results
    workflow.add_edge("tools", "thinking")

    # ============= COMPILATION =============

    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)

    # Save graph
    try:
        image = compiled.get_graph().draw_mermaid_png()
        with open("shell_agent_graph_simple.png", "wb") as f:
            f.write(image)
    except Exception:
        pass

    return compiled


# ============= NODE FUNCTIONS =============





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

    # Fallback: If no tools and no content, maybe force thinking?
    return "thinking"


# ============= EXECUTION HELPER =============


async def run_simple_agent(user_request: str, thread_id: str = "default"):
    """Run simplified agent"""

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
