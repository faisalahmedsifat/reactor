"""
src/graph_simple.py

Simplified LangGraph workflow that mimics Claude Code behavior.
Flow: Thinking (Brain) → Agent (Hands) → Tools → Thinking
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from src.state import ShellAgentState
from src.tools import (
    shell_tools,
    file_tools,
    web_tools,
    todo_tools,
    grep_and_log_tools,
    agent_tools,
)
from langchain_core.messages import HumanMessage
import os

from src.nodes.thinking_nodes import thinking_node
from src.nodes.agent_nodes import agent_node

def create_shell_agent(exclude_agent_tools: bool = False):
    """Build simplified LangGraph similar to Claude Code"""

    workflow = StateGraph(ShellAgentState)

    # ============= TOOLS =============
    base_tools = [
        shell_tools.get_system_info,
        shell_tools.execute_shell_command,
        shell_tools.validate_command_safety,
        file_tools.read_file_content,
        file_tools.write_file,
        file_tools.modify_file,
        file_tools.edit_file,
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

    agent_management_tools = [
        agent_tools.spawn_agent,
        agent_tools.get_agent_result,
        agent_tools.list_available_agents,
        agent_tools.list_running_agents,
        agent_tools.stop_agent,
    ]

    if exclude_agent_tools:
        all_tools = base_tools
    else:
        all_tools = base_tools + agent_management_tools

    # ============= NODES =============
    workflow.add_node("thinking", thinking_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))

    # ============= EDGES =============
    
    # 1. Start with Thinking (Brain)
    workflow.set_entry_point("thinking")

    workflow.add_edge("thinking", "agent")

    # # 2. From Thinking, decide: Stop or Execute?
    # workflow.add_conditional_edges(
    #     "thinking",
    #     route_after_thinking,
    #     {
    #         "execute": "agent",  # Brain has a plan -> Go to Agent
    #         "end": END           # Brain says [STOP_AGENT] -> End
    #     }
    # )

    # 3. From Agent, decide: Tool Call or Text Response?
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools", # Agent called a tool
            "end": END        # Agent replied with text (task done/question asked)
        }
    )

    # 4. From Tools, always go back to Thinking (Analyze result)
    workflow.add_edge("tools", "thinking")


    # ============= COMPILATION =============
    checkpointer = MemorySaver()
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled


# ============= ROUTING LOGIC =============

def route_after_thinking(state: ShellAgentState) -> Literal["execute", "end"]:
    """
    Check the Brain's decision. 
    If next_step is 'stop_agent' (or explicit stop token), we finish.
    Otherwise, we send the instruction to the Agent.
    """
    next_step = state.get("next_step", "")
    
    if next_step == "stop_agent" or "[STOP_AGENT]" in next_step:
        return "end"
    
    # Check for error recovery mode
    if next_step == "[ERROR_RECOVERY]":
        # We could route to a specific recovery node, but for now, 
        # we let the agent try to handle it or just loop.
        return "execute"
        
    return "execute"


def route_after_agent(state: ShellAgentState) -> Literal["tools", "end"]:
    """
    Check if the Agent generated a Tool Call or just a Message.
    """
    next_step = state.get("next_step", "")
    
    if next_step == "stop_agent" or "[STOP_AGENT]" in next_step:
        return "end"
    
    last_message = state["messages"][-1]
    
    if hasattr(last_message, "tool_calls") and len(last_message.tool_calls) > 0:
        return "tools"
    
    # If no tool calls, it's a final response or clarification question
    return "end"


# ============= EXECUTION HELPER =============

async def run_agent(
    user_request: str,
    thread_id: str = "default",
    agent_name: str = None,
    skill_names: list = None,
):
    graph = create_shell_agent()

    initial_state = {
        "messages": [HumanMessage(content=user_request)],
        "user_input": user_request,
        "system_info": None,
        "intent": None,
        "current_command_index": 0,
        "results": [],
        "retry_count": 0,
        "requires_approval": False,
        "approved": False,
        "error": None,
        "execution_mode": "sequential",
        "max_retries": 3,
        "analysis_data": {},
        "active_agent": agent_name,
        "active_skills": skill_names or [],
        "next_step": None 
    }

    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    print(f"🚀 Starting agent for: {user_request}\n")

    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            print(f"\n{'='*60}")
            print(f"[{node_name.upper()}]")
            print("=" * 60)
            
            # Print specific node outputs for debugging
            if node_name == "thinking":
                print(f"🧠 Analysis: {node_output.get('analysis_data', {}).get('latest_analysis', 'N/A')}")
                print(f"👉 Next Step: {node_output.get('next_step')}")
            
            elif "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]
                content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                print(f"🤖 Output: {content}")
                if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                    print(f"🛠️  Tools: {[tc['name'] for tc in last_msg.tool_calls]}")

    print("\n✅ Agent completed successfully")