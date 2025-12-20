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
        shell_tools.run_interactive_command,
        shell_tools.send_shell_input,
        shell_tools.get_shell_session_output,
        shell_tools.terminate_shell_session,
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
            "end": END,  # Brain says [STOP_AGENT] -> End
        },
    )

    # 3. From Agent, decide: Tool Call, looping back to thinking, or ending?
    workflow.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",  # Agent called a tool
            "thinking": "thinking",  # Agent replied with text, go back to brain
            "end": END,  # Agent was told to stop
        },
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
    if (
        next_step == "[ERROR_RECOVERY]"
        or next_step == "[RETRY_WITH_BACKOFF]"
        or next_step == "[WAIT_AND_RETRY]"
    ):
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

    if isinstance(last_message, AIMessage) and hasattr(last_message, "tool_calls"):
        tool_calls = getattr(last_message, "tool_calls", [])
        if tool_calls:
            # If the agent wants to use a tool, we go to the tool node
            return "tools"

    # If no tool calls, it's a text response. Loop back to the brain for analysis.
    return "thinking"


# ============= EXECUTION HELPER =============

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import ast
import json

console = Console()

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
        "next_step": "",
    }

    from langchain_core.runnables import RunnableConfig

    config: RunnableConfig = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 150,
    }

    # Setup sub-agent monitoring for headless mode
    from src.agents.manager import AgentManager

    async def headless_agent_callback(agent_id, node_name, message):
        """Callback to print sub-agent activity in headless mode"""
        content = ""
        if node_name:
            console.print(f"[bold cyan]🤖 Sub-Agent {agent_id[:8]} ({node_name}):[/] {content.strip()}")
        else:
            console.print(f"[bold cyan]🤖 Sub-Agent {agent_id[:8]}:[/] {content.strip()}")

    manager = AgentManager()
    manager.set_tui_callback(headless_agent_callback)

    console.print(f"[bold green]🚀 Starting ReACTOR Agent for:[/] {user_request}\n")

    try:
        async for event in graph.astream(initial_state, config, stream_mode="updates"):
            for node_name, node_output in event.items():
                if node_name == "thinking":
                    analysis = node_output.get("analysis_data", {}).get(
                        "latest_analysis", "N/A"
                    )
                    next_step = node_output.get("next_step", "N/A")
                    
                    console.print(f"[bold magenta]🧠 Brain:[/bold magenta] [italic]{analysis}[/italic]")
                    if next_step:
                        console.print(f"[bold magenta]👉 Next Step:[/bold magenta] {next_step}")
                    print() # Spacer

                elif "messages" in node_output and node_output["messages"]:
                    last_msg = node_output["messages"][-1]
                    
                    # Tool Calls
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        for tc in last_msg.tool_calls:
                            args_str = str(tc["args"])
                            if len(args_str) > 100:
                                args_str = args_str[:97] + "..."
                            console.print(f"[bold yellow]🔧 Tool Call:[/] {tc['name']} {args_str}")
                    
                    # Tool Outputs (ToolMessage)
                    elif hasattr(last_msg, "type") and last_msg.type == "tool":
                        content = str(last_msg.content)
                        display_content = content[:300] + "..." if len(content) > 300 else content
                        console.print(f"[bold green]✅ Tool Output:[/] {display_content}")

                    # Text Content (AIMessage)
                    elif hasattr(last_msg, "content"):
                        content = last_msg.content
                        # Handle list content
                        if isinstance(content, list):
                            content = " ".join(
                                [
                                    str(c)
                                    for c in content
                                    if isinstance(c, str)
                                    or (isinstance(c, dict) and "text" in c)
                                ]
                            )

                        if isinstance(content, str):
                            content = content.strip()
                            
                            # Clean up the specific dictionary-like string format
                            # This handles the case where content is "{'type': 'text', 'text': '...'}"
                            try:
                                if content.startswith("{") and "text" in content:
                                    import ast
                                    # Use safe evaluation to parse the string to a dict
                                    data = ast.literal_eval(content)
                                    if isinstance(data, dict):
                                        if "text" in data:
                                            content = data["text"]
                                        # Handle case where it might be nested or different key
                                        elif "content" in data:
                                            content = data["content"]
                            except (ValueError, SyntaxError):
                                # If it fails to parse (e.g. valid text starting with {), just use original
                                pass

                            if content and not content.startswith("**Analysis:**"):
                                console.print("[bold blue]💬 Agent Response:[/]")
                                console.print(Markdown(content))
                                print() # Spacer
    finally:
        pass

    console.print("\n[bold green]✅ Task Completed[/]")
