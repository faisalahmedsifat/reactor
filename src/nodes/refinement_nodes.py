"""
src/nodes/refinement_nodes.py

Nodes for dynamic plan refinement
"""

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.state import ShellAgentState
from src.nodes.llm_nodes import get_llm_client
import json
import re

async def refine_command_node(state: ShellAgentState) -> ShellAgentState:
    """
    Node: Refine the next command just-in-time.
    
    Checks if the current command has placeholders or if previous results
    provide context that should alter the command.
    """
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    
    if idx >= len(plan.commands):
        return state
        
    current_cmd = plan.commands[idx]
    results = state["results"]
    
    # Skip if no previous results (nothing to refine with)
    if not results:
        return state
        
    # Heuristic: Check for placeholders like <...> or [...]
    has_placeholder = bool(re.search(r'<[^>]+>|\[[^\]]+\]', current_cmd.cmd))
    
    # Heuristic: Check if previous command was a "discovery" command
    last_result = results[-1]
    is_discovery = any(x in last_result.command.lower() for x in ['ls', 'dir', 'get-childitem', 'find', 'grep', 'locate'])
    
    # If no obvious need for refinement, skip to save latency/tokens
    # (You can make this more aggressive if needed)
    if not has_placeholder and not is_discovery:
        return state
        
    # --- Perform Refinement ---
    
    llm_client = get_llm_client()
    
    system_prompt = """You are a smart shell agent.
    
    Your job is to REFINE the next command in an execution plan based on the output of previous commands.
    
    Specific tasks:
    1. Replace placeholders (e.g., <filename>) with actual values found in previous output.
    2. Fix paths or arguments based on discovery results.
    3. If the command is already correct, keep it as is.
    
    Output ONLY valid JSON:
    {
      "needs_refinement": true/false,
      "refined_command": "the actual command to run",
      "reason": "why you changed it"
    }"""
    
    # Context from previous execution
    context_str = f"Previous Command: {last_result.command}\n"
    context_str += f"Output:\n{last_result.stdout[:1000]}\n" # Truncate to avoid context limit
    
    user_prompt = f"""Current Plan Step {idx+1}:
    Command: {current_cmd.cmd}
    Description: {current_cmd.description}
    
    Context from previous step:
    {context_str}
    
    Refine the command if needed (especially if it has placeholders like <...>).
    JSON Output:"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = await llm_client.ainvoke(messages)
    
    # Parse JSON
    try:
        json_str = response.content
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
            
        data = json.loads(json_str.strip())
        
        if data.get("needs_refinement"):
            new_cmd = data["refined_command"]
            reason = data.get("reason", "Refined based on context")
            
            # Update the plan
            state["execution_plan"].commands[idx].cmd = new_cmd
            
            state["messages"].append(
                AIMessage(content=f"🔧 Refined command: `{new_cmd}`\nReason: {reason}")
            )
            
    except Exception as e:
        # If refinement fails, just proceed with original (fail safe)
        print(f"Refinement failed: {e}")
        
    return state
