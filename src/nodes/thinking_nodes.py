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
    
    messages = state.get("messages", [])
    user_input = state.get("user_input", "")

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
    messages_list = list(messages)
    if should_compact(messages_list, threshold_tokens=50000):
        print("[COMPACTION] Conversation too long, auto-compacting...")
        messages_list = await compact_conversation(messages_list, target_tokens=10000)
        # Note: We don't return here, we just use the compacted messages for context

    # 5. Construct Context Messages
    # We create a fresh list to ensure the system prompt is strictly followed
    context_messages = [SystemMessage(content=prompt)] + messages_list

    # Force Analysis Loop:
    # If the last thing that happened was a Tool Output, we force the Brain to look at it.
    if len(messages_list) > 0 and isinstance(messages_list[-1], ToolMessage):
        context_messages.append(
            SystemMessage(
                content="The tool execution is complete. Analyze the output above. \n"
                        "1. Did it succeed? (If no, perform RCA)\n"
                        "2. What is the logical NEXT step?\n"
                        "Output your decision in the required JSON structure."
            )
        )
    elif len(messages_list) == 1 and isinstance(messages_list[0], HumanMessage):
        # First turn trigger
        context_messages.append(
            SystemMessage(content="Analyze the request. What is the first step? Output in JSON.")
        )

    # 6. Invoke LLM
    try:
        # returns BrainOutput object (not a Message)
        result = await structured_llm.ainvoke(context_messages)
        
        # Handle different return types from structured output
        brain_decision = None
        
        if hasattr(result, 'analysis'):
            # It's already a BrainOutput-like object
            brain_decision = BrainOutput(
                analysis=getattr(result, 'analysis', ''),
                plan=getattr(result, 'plan', ''),
                next_step=getattr(result, 'next_step', ''),
                is_terminal=getattr(result, 'is_terminal', False)
            )
        elif isinstance(result, dict):
            # It's a dict, check if it has the expected fields
            if 'analysis' in result or 'plan' in result or 'next_step' in result:
                brain_decision = BrainOutput(
                    analysis=result.get('analysis', ''),
                    plan=result.get('plan', ''),
                    next_step=result.get('next_step', ''),
                    is_terminal=result.get('is_terminal', False)
                )
            else:
                # Dict but not BrainOutput format - treat as analysis text and continue
                # This handles cases where LLM returns tool results instead of BrainOutput
                brain_decision = BrainOutput(
                    analysis=str(result),
                    plan='Continue with next step',
                    next_step='execute',
                    is_terminal=False
                )
        else:
            # Fallback - treat as analysis text and continue
            brain_decision = BrainOutput(
                analysis=str(result),
                plan='Continue with next step',
                next_step='execute',
                is_terminal=False
            )
    except Exception as e:
        error_msg = str(e)
        print(f"[DEBUG] Thinking Error: {error_msg}")
        
        # Classify error type for better recovery
        if "Resource has been exhausted" in error_msg or "429" in error_msg:
            analysis = "Rate limit exceeded. Waiting before retry."
            next_step = "[WAIT_AND_RETRY]"
        elif "authentication" in error_msg.lower() or "invalid api key" in error_msg.lower():
            analysis = "Authentication failed. Check API credentials."
            next_step = "[STOP_AGENT]"
        elif "connection" in error_msg.lower():
            analysis = "Connection failed. Check network connectivity."
            next_step = "[RETRY_WITH_BACKOFF]"
        else:
            analysis = f"LLM inference error: {error_msg}"
            next_step = "[ERROR_RECOVERY]"
        
        # Fallback for error handling
        return {
            "error": error_msg,
            "next_step": next_step,
            "analysis_data": {
                "latest_analysis": analysis, 
                "latest_plan": "Error recovery"
            }
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
        instruction = "[STOP_AGENT]"
    else:
        next_step_str = brain_decision.next_step
        instruction = brain_decision.next_step
        
        # LOGIC INJECTION: Handshake for Safety Validation
        # If the LAST message was a Tool Message from 'validate_command_safety' AND it was safe,
        # we explicitly tell the Agent that safety is validated.
        # This prevents the "Stateless Agent" from falling into an infinite validation loop.
        if len(messages_list) > 0 and isinstance(messages_list[-1], ToolMessage):
            last_tool = messages_list[-1]
            if last_tool.name == "validate_command_safety":
                # Check content for safety confirmation
                content = last_tool.content
                # Robust check for "is_safe": true in JSON string or artifact
                if '"is_safe": true' in content or "'is_safe': True" in content or (last_tool.artifact and last_tool.artifact.get("is_safe") is True):
                     instruction += " [SAFETY_VALIDATED]"
                     next_step_str += " [SAFETY_VALIDATED]"
        
    # Ensure we don't prematurely end multi-step workflows
    # If the instruction is empty but we are NOT terminal, force a continue
    if not next_step_str or next_step_str.strip() == "":
        if not brain_decision.is_terminal:
            next_step_str = "continue_analysis"
            instruction = "Continue with the next logical step based on the current context."
        else:
             # Should be caught by is_terminal check above, but safe fallback
            next_step_str = "[STOP_AGENT]"
            instruction = "[STOP_AGENT]"

    # Enhanced analysis state management
    current_analysis_phase = state.get("analysis_phase", "discovery")
    files_analyzed = state.get("files_analyzed", [])
    user_input = state.get("user_input", "")
    
    # Determine next analysis phase based on context - ONLY override if brain didn't provide specific instruction
    # AND the instruction is generic
    is_generic_instruction = instruction in ["continue_analysis", "execute", "Continue with the next logical step based on the current context."]
    
    if ("analyze" in user_input.lower() or "project" in user_input.lower()) and is_generic_instruction:
        if current_analysis_phase == "discovery":
            next_phase = "analysis"
            instruction = "Use prioritize_files to identify key files for analysis"
        elif current_analysis_phase == "analysis":
            next_phase = "synthesis" 
            instruction = "Read the prioritized files using read_multiple_files"
        elif current_analysis_phase == "synthesis":
            next_phase = "complete"
            instruction = "Provide comprehensive project analysis summary"
        else:
            next_phase = "discovery"
            instruction = "Start project discovery with analyze_project_structure"
    else:
        next_phase = current_analysis_phase
        # Keep the brain's instruction if it provided one
        pass

    return {
        # Append the structured thought as an AIMessage so history is preserved
        "messages": [AIMessage(content=thought_process_text)],
        
        # Structure for the Executor node to use
        "next_step": instruction,
        
        # Enhanced meta-data for the UI or advanced logic
        "analysis_data": {
            "latest_analysis": brain_decision.analysis,
            "latest_plan": brain_decision.plan,
            "analysis_phase": next_phase,
            "files_analyzed_count": len(files_analyzed)
        },
        
        # Update analysis state
        "analysis_phase": next_phase,
        "files_analyzed": files_analyzed,
        
        # Persist the system info refresh
        "system_info": system_info 
    }