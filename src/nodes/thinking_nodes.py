"""
src/nodes/thinking_nodes.py

Nodes for pure logical reasoning without tool execution.
"""

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from src.state import ShellAgentState
from src.nodes.llm_nodes import get_llm_client
from src.tools import shell_tools, file_tools, web_tools, todo_tools


async def thinking_node(state: ShellAgentState) -> ShellAgentState:
    """
    Node: Pure reasoning step.

    Analyzes the conversation and decides the next course of action,
    potentially calling tools directly.
    """
    llm_client = get_llm_client()
    messages = state["messages"]

    # Combine all tools into one list for the thinking node
    all_tools = [
        # System tools
        shell_tools.get_system_info,
        shell_tools.execute_shell_command,
        shell_tools.validate_command_safety,
        # File tools
        file_tools.read_file_content,
        file_tools.write_file,
        file_tools.modify_file,
        file_tools.list_project_files,
        file_tools.search_in_files,
        # Web tools
        web_tools.web_search,
        web_tools.recursive_crawl,
        # TODO tools
        todo_tools.create_todo,
        todo_tools.complete_todo,
        todo_tools.list_todos,
        todo_tools.update_todo,
    ]

    # Bind all tools to the LLM for the thinking node
    llm_with_tools = llm_client.bind_tools(all_tools)

    # Get system info for prompt context
    system_info = state.get("system_info")
    if not system_info:
        system_info = await shell_tools.get_system_info.ainvoke({})
        state["system_info"] = system_info

    # Load prompt from centralized system
    from src.prompts import get_prompt

    prompt = get_prompt(
        "thinking.system",
        os_info=system_info["os_type"],
        shell_info=system_info["shell_type"],
        working_dir=system_info["working_directory"],
    )

    # Auto-compact conversation if too long
    from src.utils.conversation_compactor import should_compact, compact_conversation

    if should_compact(messages, threshold_tokens=50000):
        print("[COMPACTION] Conversation too long, auto-compacting...")
        messages = await compact_conversation(messages, target_tokens=10000)
        state["messages"] = messages

    # If this is the start, add system prompt
    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        context_messages = [SystemMessage(content=prompt)] + messages
    else:
        # Inject system prompt refresh to keep it focused
        context_messages = [SystemMessage(content=prompt)] + messages
    # If the last message was a tool output, force a reaction
    # This part might need adjustment based on how the agent_node is refactored
    # For now, keep it to ensure the LLM reacts to tool outputs
    if len(messages) > 0 and isinstance(messages[-1], ToolMessage):
        context_messages.append(
            HumanMessage(
                content="The tool execution is complete. Analyze the results above and determine the next step. If you have enough information, provide the final answer."
            )
        )
    elif (
        len(messages) > 0
        and isinstance(messages[-1], AIMessage)
        and not messages[-1].tool_calls
    ):
        # If the last message was a text-only AIMessage from a previous thinking step,
        # prompt it to continue thinking or act.
        context_messages.append(
            HumanMessage(
                content="Analyze the current state and determine the next step. If you have enough information, provide the final answer."
            )
        )
    elif len(messages) == 1 and isinstance(messages[0], HumanMessage):
        # Initial prompt for the first turn
        context_messages.append(
            HumanMessage(
                content="Analyze the user's request and determine the initial step. If a tool is needed, call it. If you can answer directly, do so."
            )
        )

    messages = context_messages

    # Call LLM (now with tools bound)
    print(f"\n[DEBUG] Thinking Node Input Messages: {len(messages)}")
    try:
        response = await llm_with_tools.ainvoke(messages)  # Use llm_with_tools
    except Exception as e:
        print(f"[DEBUG] LLM Invoke Error: {e}")
        response = AIMessage(content=f"Error: {e}")

    print(f"[DEBUG] Thinking Node Raw Output: '{response.content}'")
    print(f"[DEBUG] Full Response: {response}")

    if not response.content and not response.tool_calls:
        print(
            "[DEBUG] WARNING: Empty content and no tool calls received. Injecting fallback."
        )
        response.content = (
            "I need to analyze the previous tool output and decide the next step."
        )

    # The thinking node now directly returns the LLM's response, which may contain tool_calls
    return {"messages": [response]}
