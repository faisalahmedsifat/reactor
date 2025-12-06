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
from src.tools import shell_tools, file_tools
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import os


from src.nodes.thinking_nodes import thinking_node

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
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
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

async def agent_node(state: ShellAgentState) -> ShellAgentState:
    """Main agent node - uses LLM with tools"""
    from src.nodes.llm_nodes import get_llm_client
    
    llm_client = get_llm_client()
    
    # Bind all tools to LLM
    all_tools = [
        shell_tools.get_system_info,
        shell_tools.execute_shell_command,
        shell_tools.validate_command_safety,
        file_tools.read_file_content,
        file_tools.write_file,
        file_tools.modify_file,
        file_tools.list_project_files,
        file_tools.search_in_files,  # grep-like search
    ]
    
    llm_with_tools = llm_client.bind_tools(all_tools)
    
    # Add system message if first interaction
    messages = state["messages"]
    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
        system_info = state.get("system_info")
        if not system_info:
            # Get system info first
            system_info = await shell_tools.get_system_info.ainvoke({})
            state["system_info"] = system_info
        
        system_message = AIMessage(content=f"""You are an intelligent shell assistant with access to powerful tools.

Current context:
- OS: {system_info['os_type']}
- Shell: {system_info['shell_type']}
- Directory: {system_info['working_directory']}

Available Tools:
1. **Shell Commands**: execute_shell_command - Run any shell command
2. **File Reading**: read_file_content - Read file contents
3. **File Writing**: write_file - Create or modify files
4. **File Editing**: modify_file - Search and replace within files
5. **File Search**: search_in_files - Find text in files (grep-like, case-insensitive)
6. **Project Analysis**: list_project_files

How to handle requests:
- "where is X defined" or "find X" → use search_in_files
- "read X" or "show X" → use read_file_content
- "create X" or "write X" → use write_file
- "implement X" or "add feature X" → read existing files, then write_file or modify_file
- "initialize X project" → execute_shell_command (e.g., npx create-next-app)
- "what's my IP" → execute_shell_command (ipconfig or curl)

Be direct, helpful, and proactive. Use tools to accomplish tasks.""")
        
        messages = [system_message] + messages
    
    # Invoke LLM
    response = await llm_with_tools.ainvoke(messages)
    
    # Add response to messages
    state["messages"].append(response)
    
    return state


def should_continue(state: ShellAgentState) -> Literal["tools", "end"]:
    """Determine if we should continue to tools or end"""
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, continue to tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, end
    return "end"


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
        "analysis_data": None
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
                print(last_msg.content if hasattr(last_msg, 'content') else str(last_msg))
    
    print("\n✅ Agent completed successfully")


# Usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        await run_simple_agent("where have I defined the graph for this project?")
    
    asyncio.run(main())
