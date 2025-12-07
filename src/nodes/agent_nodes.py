"""
src/nodes/agent_nodes.py

Agent node for the Simplified Reactive Graph.
Uses the LLM to select tools based on Thinking node input.
"""

from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, AIMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.prebuilt import ToolNode

from src.state import ShellAgentState
from src.tools import shell_tools, file_tools, web_tools, todo_tools, grep_and_log_tools
from src.llm.client import get_llm_client
from src.prompts import get_prompt
import os


async def agent_node(state: ShellAgentState) -> Dict:
    """
    Main agent node - uses LLM with tools.
    
    This node:
    1. Binds all available tools to the LLM
    2. Constructs the context-aware system prompt
    3. Invokes the LLM to either call a tool or provide a final answer
    """
    llm_client = get_llm_client()

    # Define all available tools
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
    ]

    # Bind tools to the LLM client
    llm_with_tools = llm_client.bind_tools(all_tools)

    # Get conversation history
    messages = state["messages"]

    # Gather System Info if missing (lazy loading)
    system_info = state.get("system_info")
    if not system_info:
        # If we barely started and don't have sys info, fetch it
        # In a real tool node we'd call the tool, here we cheat a bit for speed or invoke it directly
        system_info = await shell_tools.get_system_info.ainvoke({})
        # Note: We'll return this update to state at the end

    # Retrieve specific system prompt for the Agent role
    system_prompt_content = get_prompt(
        "agent.system",
        os_type=system_info["os_type"],
        shell_type=system_info["shell_type"],
        working_directory=system_info["working_directory"],
    )

    system_message = SystemMessage(content=system_prompt_content)

    # Prepend system message to history for this specific inference call
    # This ensures the LLM knows its role without permanently cluttering the message history
    messages_for_llm = [system_message] + messages

    # Invoke LLM
    response = await llm_with_tools.ainvoke(messages_for_llm)

    # Prepare state updates
    updates = {"messages": [response]}
    
    # If we fetched system_info for the first time, save it to state
    if not state.get("system_info") and system_info:
        updates["system_info"] = system_info

    return updates
