"""
src/nodes/communication_nodes.py

Communication nodes for conversational agent workflow.
These nodes handle upfront communication with users before execution.
"""

from src.state import ShellAgentState
from langchain_core.messages import AIMessage


async def communicate_understanding_node(state: ShellAgentState) -> ShellAgentState:
    """
    Communicate what the agent understood from the user's request.
    This happens BEFORE planning and execution.
    """
    intent = state["intent"]
    
    if not intent:
        # Fallback if intent parsing failed
        understanding_msg = f"💡 **Understanding Your Request**\n\nI'll help you with: {state['user_input']}\n\nLet me create a plan..."
    else:
        # Format a friendly message explaining what we understood
        entities_text = ", ".join(intent.key_entities) if intent.key_entities else "no specific items"
        constraints_text = "\n- ".join(intent.constraints) if intent.constraints else "None"
        
        understanding_msg = f"""💡 **Understanding Your Request**

**Task**: {intent.task_description}
**Category**: {intent.category.replace('_', ' ').title()}
**Key Items**: {entities_text}
**Constraints**:
- {constraints_text}

**Confidence**: {intent.user_intent_confidence * 100:.0f}%

Let me create an execution plan for you..."""

    state["messages"].append(AIMessage(content=understanding_msg))
    return state


async def communicate_plan_node(state: ShellAgentState) -> ShellAgentState:
    """
    Present the execution plan to the user BEFORE execution.
    Shows strategy, commands, and risk levels.
    """
    plan = state["execution_plan"]
    
    if not plan or not plan.commands:
        # No commands to execute
        no_plan_msg = """📋 **Execution Plan**

No commands needed for this task."""
        state["messages"].append(AIMessage(content=no_plan_msg))
        return state
    
    # Format risk level with emoji
    def format_risk(risk_level: str) -> str:
        risk_emoji = {
            "safe": "✅",
            "moderate": "⚠️",
            "dangerous": "🔴"
        }
        return f"{risk_emoji.get(risk_level.lower(), '❓')} {risk_level.upper()}"
    
    # Build command list
    cmd_lines = []
    for i, cmd in enumerate(plan.commands, 1):
        risk_indicator = format_risk(cmd.risk_level.value if hasattr(cmd.risk_level, 'value') else str(cmd.risk_level))
        reversible_indicator = "↩️" if cmd.reversible else "⚡"
        cmd_lines.append(
            f"{i}. {risk_indicator} {reversible_indicator} **{cmd.description}**\n"
            f"   ```bash\n   {cmd.cmd}\n   ```\n"
            f"   *Reason*: {cmd.reasoning}"
        )
    
    commands_text = "\n\n".join(cmd_lines)
    
    # Potential issues
    issues_text = "\n- ".join(plan.potential_issues) if plan.potential_issues else "None identified"
    
    # Estimated time
    duration_text = f"{plan.estimated_duration_seconds}s" if plan.estimated_duration_seconds < 60 else f"{plan.estimated_duration_seconds // 60}m {plan.estimated_duration_seconds % 60}s"
    
    plan_msg = f"""📋 **Execution Plan**

**Strategy**: {plan.overall_strategy}

**Commands to Execute** ({len(plan.commands)} total):

{commands_text}

**⚠️ Potential Issues**:
- {issues_text}

**⏱️ Estimated Duration**: {duration_text}

Starting execution..."""

    state["messages"].append(AIMessage(content=plan_msg))
    return state


async def stream_progress_node(state: ShellAgentState) -> ShellAgentState:
    """
    Stream execution progress after each command.
    Shows immediate results and retry information if applicable.
    """
    results = state["results"]
    
    if not results:
        return state
    
    # Get last result
    last_result = results[-1]
    retry_count = state.get("retry_count", 0)
    
    # Format status
    if last_result.success:
        status_emoji = "✅"
        status_text = "SUCCESS"
    else:
        status_emoji = "❌"
        status_text = "FAILED"
    
    # Retry indicator
    retry_text = f" (Retry {retry_count}/3)" if retry_count > 0 else ""
    
    # Truncate output for readability
    stdout_preview = last_result.stdout[:500] if last_result.stdout else ""
    stderr_preview = last_result.stderr[:500] if last_result.stderr else ""
    
    # Build progress message
    if last_result.success:
        output_section = f"**Output**:\n```\n{stdout_preview}\n```" if stdout_preview else "*No output*"
    else:
        output_section = f"**Error**:\n```\n{stderr_preview}\n```" if stderr_preview else "*No error message*"
    
    progress_msg = f"""⚡ **Command Progress** {retry_text}

{status_emoji} **Status**: {status_text}
**Command**: `{last_result.command}`
**Duration**: {last_result.duration_ms}ms
**Exit Code**: {last_result.exit_code}

{output_section}"""

    state["messages"].append(AIMessage(content=progress_msg))
    return state
