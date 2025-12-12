"""
src/graph_simple.py

Simplified LangGraph workflow that mimics Claude Code behavior.
Flow: Thinking (Brain) → Agent (Hands) → Tools → Thinking
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig

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
        file_tools.read_multiple_files,
        file_tools.prioritize_files,
        file_tools.analyze_project_structure,
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

    # 2. From Thinking, decide: Stop or Execute?
    workflow.add_conditional_edges(
        "thinking",
        route_after_thinking,
        {
            "execute": "agent",  # Brain has a plan -> Go to Agent
            "end": END           # Brain says [STOP_AGENT] -> End
        }
    )

    # 3. From Agent, decide: Tool Call, looping back to thinking, or ending?
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",  # Agent called a tool
            "thinking": "thinking",  # Agent replied with text, go back to brain
            "end": END,  # Agent was told to stop
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
    
    # Check for explicit stop conditions
    if next_step == "stop_agent" or (next_step and "[STOP_AGENT]" in next_step):
        return "end"
    
    # Check for error recovery mode
    if next_step == "[ERROR_RECOVERY]" or next_step == "[RETRY_WITH_BACKOFF]" or next_step == "[WAIT_AND_RETRY]":
        # Route to agent for error handling
        return "execute"
    
    # Check for valid next step - if empty or None, we DEFAULT to execute to let the agent/brain try again
    # rather than failing silently. The brain usually provides "continue_analysis" or similar if unsure.
    if not next_step or next_step.strip() == "":
        # Log warning if possible, but keep going to avoid premature stops
        return "execute"
        
    return "execute"


def route_after_agent(state: ShellAgentState) -> Literal["tools", "thinking", "end"]:
    """
    Check if the Agent generated a Tool Call, a Message, or if it was told to stop.
    """
    next_step = state.get("next_step", "")

    # If the brain ordered a stop, the agent just passes that along.
    if next_step == "[STOP_AGENT]" or (next_step and "[STOP_AGENT]" in next_step):
        return "end"

    messages = state.get("messages", [])
    if not messages:
        return "thinking"  # Safeguard, loop back to brain

    last_message = messages[-1]

    # Check message type to determine if tools were called
    from langchain_core.messages import AIMessage
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls'):
        tool_calls = getattr(last_message, 'tool_calls', [])
        if tool_calls:
            # If the agent wants to use a tool, we go to the tool node
            return "tools"

    # If no tool calls, it's a text response. Loop back to the brain for analysis.
    return "thinking"


# ============= EXECUTION HELPER =============

async def run_agent(
    user_request: str,
    thread_id: str = "default",
    agent_name: str | None = None,
    skill_names: list | None = None,
):
    graph = create_shell_agent()

    initial_state: ShellAgentState = {
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
        "next_step": "" 
    }

    from langchain_core.runnables import RunnableConfig
    
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}, "recursion_limit": 150}
    print(f"🚀 Starting agent for: {user_request}\n")

    async for event in graph.astream(initial_state, config, stream_mode="updates"):
        for node_name, node_output in event.items():
            # Cleaner output for headless mode
            if node_name == "thinking":
                analysis = node_output.get('analysis_data', {}).get('latest_analysis', 'N/A')
                next_step = node_output.get('next_step', 'N/A')
                if next_step and next_step not in ['[STOP_AGENT]', '[ERROR_RECOVERY]']:
                    print(f"🧠 {analysis[:100]}{'...' if len(analysis) > 100 else ''}")
            
            elif "messages" in node_output and node_output["messages"]:
                last_msg = node_output["messages"][-1]
                # Simple check for tool calls - skip for now to focus on other fixes
                # TODO: Fix tool_calls detection properly
                if False:  # Temporarily disable tool_calls check
                    tool_names = [tc['name'] for tc in last_msg.tool_calls]
                    print(f"🔧 Executing: {', '.join(tool_names)}")
                elif hasattr(last_msg, 'content'):
                    content = last_msg.content
                    # Handle list content (common in multimodal or structured outputs)
                    if isinstance(content, list):
                        # Join text blocks or extract meaningful part
                        content = " ".join([str(c) for c in content if isinstance(c, str) or (isinstance(c, dict) and 'text' in c)])
                    
                    if isinstance(content, str):
                        content = content.strip()
                        if content and not content.startswith('**Analysis:**'):
                            print(f"💬 {content}")

    print("\n✅ Task completed")