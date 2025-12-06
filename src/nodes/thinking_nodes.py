"""
src/nodes/thinking_nodes.py

Nodes for pure logical reasoning without tool execution.
"""

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from src.state import ShellAgentState
from src.nodes.llm_nodes import get_llm_client

async def thinking_node(state: ShellAgentState) -> ShellAgentState:
    """
    Node: Pure reasoning step.
    
    Analyzes the conversation and decides the next course of action
    WITHOUT calling any tools. Producing text output only.
    """
    llm_client = get_llm_client()
    messages = state["messages"]
    
    # Check if we just came from tools
    last_msg = messages[-1]
    is_after_tool = hasattr(last_msg, "tool_calls") or (isinstance(last_msg, list) and any(m.type == "tool" for m in last_msg))
    
    system_prompt = """You are an intelligent software engineer agent.

CAPABILITIES:
You have FULL ACCESS to the user's local filesystem and shell. You can:
- Run any shell command (ls, grep, find, npx, git, etc.)
- Read, Write, and Edit files.
- Analyze project structure.

YOUR GOAL: Analyze the current situation and decide what to do next.

INSTRUCTIONS:
1. Review the User Request and any Tool Outputs.
2. If the task is complete, answer the user conclusively.
3. **CRITICAL**: Never say you cannot access files. You function as the "Brain" planning the actions for the "Body" (Agent) that has the tools.
4. If you need to use a tool, explicit state: "I need to run [command]..." or "I will read [file]...".
5. DO NOT generate actual tool calls in this step. Just plan them in text.
6. Be concise and professional.

OUTPUT:
- Just a text response explaining your thought process or final answer.
"""
    
    # Inject system info if available
    system_info = state.get("system_info")
    working_dir = system_info.get("working_directory") if system_info else None
    
    prompt = system_prompt
    if working_dir:
        prompt += f"\nCURRENT CONTEXT:\n- Working Directory: {working_dir}\nYou are ALREADY in the correct directory. Do not cd unless asked."
    
    # If this is the start, add system prompt
    if len(messages) == 1 and isinstance(messages[0], HumanMessage):
         messages = [SystemMessage(content=prompt)] + messages
    else:
        # Inject system prompt refresh to keep it focused
        context_messages = [SystemMessage(content=prompt)] + messages
        
        # If the last message was a tool output, force a reaction
        if is_after_tool:
            context_messages.append(HumanMessage(content="The tool execution is complete. analyzing the results above, briefly explain what you need to do next."))
            
        messages = context_messages

    # Call LLM (without tools bound)
    response = await llm_client.ainvoke(messages)
    
    # Ensure it's treated as text (no tool calls allowed here, though LLM shouldn't generate them if not bound)
    return {"messages": [response]}
