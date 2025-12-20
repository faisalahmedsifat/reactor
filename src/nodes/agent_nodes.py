"""
src/nodes/agent_nodes.py

Agent node for the Simplified Reactive Graph.
The 'Hands' of the operation - converts Brain Plans to Tool Calls.
"""

from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import ShellAgentState
from src.tools import (
    shell_tools,
    file_tools,
    web_tools,
    todo_tools,
    grep_and_log_tools,
    agent_tools,
)
from src.llm.client import get_llm_client
from src.prompts import get_prompt, compose_prompt


async def agent_node(state: ShellAgentState) -> Dict[str, Any]:
    """
    Node: Execution step (The Hands).

    1. Receives the specific 'next_step' instruction from the Thinking Node.
    2. Binds ALL available tools.
    3. Invokes LLM to generate Tool Calls or Final Response.
    """
    llm_client = get_llm_client()

    # 1. Define All Available Tools
    all_tools = [
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
        agent_tools.spawn_agent,
        agent_tools.list_available_agents,
        agent_tools.get_agent_result,
        agent_tools.list_running_agents,
        agent_tools.stop_agent,
    ]

    # 2. Bind Tools
    llm_with_tools = llm_client.bind_tools(all_tools)

    # 3. Context & Prompt
    messages = state.get("messages", [])
    system_info = state.get("system_info")
    if not system_info:
        # Fallback safety
        system_info = await shell_tools.get_system_info.ainvoke({})

    base_system_prompt = get_prompt(
        "agent.system",
        os_type=system_info["os_type"],
        shell_type=system_info["shell_type"],
        working_directory=system_info["working_directory"],
    )

    system_prompt_content = compose_prompt(
        base_system_prompt,
        agent_name=state.get("active_agent"),
        skill_names=state.get("active_skills", []),
    )

    # 4. Inject the Specific Instruction
    # This is crucial: we tell the Agent EXACTLY what the Brain wants done right now.
    current_instruction = state.get("next_step", "Review history and proceed.")

    # Handle special instructions
    if current_instruction == "[STOP_AGENT]":
        # Return a final message instead of trying to execute tools
        from langchain_core.messages import AIMessage

        updates: Dict[str, Any] = {
            "messages": [AIMessage(content="Task completed successfully.")],
            "next_step": "[STOP_AGENT]",
        }
        if not state.get("system_info"):
            updates["system_info"] = system_info
        return updates

    instruction_message = SystemMessage(
        content=f"## IMMEDIATE INSTRUCTION\nThe Brain has analyzed the situation and ordered you to:\n>>> {current_instruction}\n\nExecute this EXACTLY. Do not deviate. If this is a summary/respond instruction, provide a text response. Otherwise, use tools."
    )

    # Construct the message stack
    # REFINEMENT: Sliding Window Context
    # We include the last 10 messages to provide immediate context (e.g., "I just ran ls, here is the output").
    # This solves the "stuck" issue where the Agent forgets recent tool results.
    # The Brain handles the global history/strategy, but the Hands need local context to act intelligently.

    combined_system_content = f"{system_prompt_content}"

    context_messages = [SystemMessage(content=combined_system_content)]

    # Get last 10 messages for local context
    recent_messages = messages[-10:] if messages else []
    context_messages.extend(recent_messages)

    # 5. Invoke
    # Fix for Gemini 400 Error: Ensure proper message structure.
    # 1. Prune leading ToolMessages (Orphaned Results)
    # 2. Prune trailing AIMessages with tool_calls (Hanging Calls)
    # 3. Merge consecutive HumanMessages (User -> User violation)

    from langchain_core.messages import ToolMessage, AIMessage

    # 1. Prune leading ToolMessages
    while recent_messages and isinstance(recent_messages[0], ToolMessage):
        recent_messages.pop(0)

    # 2. Prune trailing hanging Tool Calls
    # If the last message is an AI message that wanted to call a tool, but we are appending a Human message,
    # we break the Call->Result chain. We must remove the incomplete call.
    while recent_messages and isinstance(recent_messages[-1], AIMessage) and getattr(recent_messages[-1], "tool_calls", None):
        recent_messages.pop()

    # Add sanitized history
    context_messages.extend(recent_messages)

    # 3. Merge User Messages or Append
    if context_messages and isinstance(context_messages[-1], HumanMessage):
        # Merge to avoid User -> User
        last_human = context_messages.pop()
        new_content = f"{last_human.content}\n\n--- INSTRUCTION ---\n{current_instruction}"
        context_messages.append(HumanMessage(content=new_content))
    else:
        # Safe to append
        context_messages.append(
            HumanMessage(content=f"Execute this instruction:\n\n{current_instruction}")
        )

    # 5. Invoke
    response = await llm_with_tools.ainvoke(context_messages)

    # 6. Return Update
    updates: Dict[str, Any] = {"messages": [response]}
    if not state.get("system_info"):
        updates["system_info"] = system_info

    return updates
