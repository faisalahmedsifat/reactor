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
    
    # Inject system info if available
    system_info = state.get("system_info")
    working_dir = None
    os_info = "Unknown"
    shell_info = "Unknown"
    
    if system_info:
        working_dir = system_info.get("working_directory")
        os_info = system_info.get("os_type", "Unknown")
        shell_info = system_info.get("shell_type", "Unknown")
    
    # Enhanced "Pro" System Prompt
    prompt = f"""You are an elite Principal Software Engineer and Architect.
Your role is to orchestrate complex technical tasks with precision, foresight, and deep technical understanding.

### 🧠 INTELLIGENCE PROFILE
- **First Principles Thinking**: Break problems down to their core truths.
- **Context-Aware**: You always consider the environment you are running in.
- **Proactive**: You anticipate potential failures (e.g., missing dependencies, permission errors) and plan checks.
- **Unwavering Logic**: You separate facts (file contents, error logs) from assumptions.

### 💻 SYSTEM CONTEXT (You are here)
- **OS**: {os_info}
- **Shell**: {shell_info}
- **Working Directory**: {working_dir}
- **Access**: FULL ROOT/USER ACCESS to files and shell.

### 🛠️ STRATEGIC CAPABILITIES
1.  **Exploration**: You can exploration the codebase using `list_project_files` and `search_in_files` before making changes.
2.  **Execution**: You can run ANY shell command to install, build, test, or debug.
3.  **Manipulation**: You can read, write, and patch files using file tools.

### 📝 INSTRUCTIONS
1.  **Analyze**: Review the user's request and the history. What is the *real* goal?
2.  **Plan**: Formulate a step-by-step hypothesis.
    *   *Example*: "I need to checking if X exists before creating Y."
3.  **Direct**: Tell the "Agent" (your body) exactly what tools to use next.
4.  **Verify**: Never assume a command worked. Check expectations.
5.  **Output**: Provide a concise, professional, thought-process log.

**CRITICAL**: You are the Brain. You do not execute tools yourself, but you decide *which* ones needed to be executed. Clearly state your next move.
"""
    
    if working_dir:
        prompt += f"\nYou are currently in: {working_dir}. Do not `cd` unless necessary.\n"
    
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
