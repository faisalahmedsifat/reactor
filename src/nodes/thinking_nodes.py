"""
src/nodes/thinking_nodes.py

Nodes for pure logical reasoning without tool execution.
The 'Brain' of the operation.
"""

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from src.state import ShellAgentState
from src.llm.client import get_llm_client
from src.tools import shell_tools
from src.prompts import get_prompt, compose_prompt
from src.utils.conversation_compactor import should_compact, compact_conversation

# Note: We do NOT import other tools here because the Brain doesn't execute them.

class BrainOutput(BaseModel):
    """Structured output for the Brain agent."""
    analysis: str = Field(description="RCA-focused analysis of current state and tool outputs. Why did the last command succeed or fail?")
    plan: str = Field(description="High-level view of the workflow to fix or advance. If >2 steps, plan to use create_todo.")
    next_step: str = Field(description="Specific, executable instruction for the Agent (e.g., 'Run ls -la', 'Read src/main.py').")
    is_terminal: bool = Field(default=False, description="True if the user's objective is fully met.")

async def thinking_node(state: ShellAgentState) -> dict:
    """
    Node: Pure reasoning step (The Brain).

    1. Analyzes the current state/history.
    2. Decides the NEXT immediate step using structured output.
    3. Returns updated state with analysis data and the next step string.
    """
    llm_client = get_llm_client()
    
    # 1. Bind LLM to Structured Output
    # This forces the LLM to return the BrainOutput Pydantic object
    structured_llm = llm_client.with_structured_output(BrainOutput)
    
    messages = state["messages"]

    # 2. Refresh Context
    # Always refresh system info to ensure Thinking node has latest context (CWD, etc)
    system_info = await shell_tools.get_system_info.ainvoke({})
    # Update the state immediately with fresh info so prompt generation uses it
    state["system_info"] = system_info

    # 3. Prepare Prompt
    base_prompt = get_prompt(
        "thinking.system",
        os_info=system_info["os_type"],
        shell_info=system_info["shell_type"],
        working_dir=system_info["working_directory"],
        git_info=system_info.get("git_info", "Unknown"),
        python_info=system_info.get("python_version", "Unknown"),
    )

    # Add Identity/Capability Constraints
    execution_mode = state.get("execution_mode", "sequential")
    
    if execution_mode == "autonomous":
        base_prompt += "\n\n## CONSTRAINT: You are a Sub-Agent. `spawn_agent` is DISABLED. Solve tasks directly."
    else:
        base_prompt += "\n\n## CAPABILITY: You are the Main Architect. Use `spawn_agent` for complex sub-tasks."

    # Compose with active persona
    prompt = compose_prompt(
        base_prompt,
        agent_name=state.get("active_agent"),
        skill_names=state.get("active_skills", []),
    )

    # 4. Message Management (Compaction)
    if should_compact(messages, threshold_tokens=50000):
        print("[COMPACTION] Conversation too long, auto-compacting...")
        messages = await compact_conversation(messages, target_tokens=10000)
        # Note: We don't return here, we just use the compacted messages for context

    # 5. Construct Context Messages
    # We create a fresh list to ensure the system prompt is strictly followed
    context_messages = [SystemMessage(content=prompt)] + messages

    # Force Analysis Loop:
    # If the last thing that happened was a Tool Output, we force the Brain to look at it.
    if len(messages) > 0 and isinstance(messages[-1], ToolMessage):
        context_messages.append(
            HumanMessage(
                content="The tool execution is complete. Analyze the output above. \n"
                        "1. Did it succeed? (If no, perform RCA)\n"
                        "2. What is the logical NEXT step?\n"
                        "Output your decision in the required JSON structure."
            )
        )
    elif len(messages) == 1 and isinstance(messages[0], HumanMessage):
        # First turn trigger
        context_messages.append(
            HumanMessage(content="Analyze the request. What is the first step? Output in JSON.")
        )

    # 6. Invoke LLM
    try:
        # returns BrainOutput object (not a Message)
        brain_decision: BrainOutput = await structured_llm.ainvoke(context_messages)
    except Exception as e:
        print(f"[DEBUG] Thinking Error: {e}")
        # Fallback for error handling
        return {
            "error": str(e),
            "next_step": "[ERROR_RECOVERY]", # Special token for router to handle
            "analysis_data": {"latest_analysis": "Error during LLM inference", "latest_plan": "Retry"}
        }

    # 7. Synthesize History & State Updates
    
    # We create a readable string for the chat history so the user/next-turns can see what happened
    thought_process_text = (
        f"**Analysis:** {brain_decision.analysis}\n"
        f"**Plan:** {brain_decision.plan}\n"
        f"**Next Step:** {brain_decision.next_step}"
    )
    
    # Determine next step string
    if brain_decision.is_terminal:
        next_step_str = "[STOP_AGENT]"
    else:
        next_step_str = brain_decision.next_step

    return {
        # Append the structured thought as an AIMessage so history is preserved
        "messages": [AIMessage(content=thought_process_text)],
        
        # Structure for the Executor node to use
        "next_step": next_step_str,
        
        # Meta-data for the UI or advanced logic
        "analysis_data": {
            "latest_analysis": brain_decision.analysis,
            "latest_plan": brain_decision.plan
        },
        
        # Persist the system info refresh
        "system_info": system_info 
    }