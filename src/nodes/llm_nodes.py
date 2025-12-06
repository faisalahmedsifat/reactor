"""
src/nodes/llm_nodes.py

LLM reasoning nodes - FIXED to use create_chat_model()
"""

from typing import Dict, Any
from functools import lru_cache
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from src.state import ShellAgentState
from src.models import CommandIntent, ExecutionPlan, Command, RiskLevel
from src.utils import extract_json_from_text
import json
import os


@lru_cache(maxsize=1)
def get_llm_client() -> BaseChatModel:
    """
    Lazy load LLM client - cached for performance.
    Returns raw BaseChatModel for LangGraph.
    """
    from src.llm.factory import LLMFactory
    
    provider = os.getenv("LLM_PROVIDER", "anthropic")
    model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
    
    # Now returns BaseChatModel directly, not ToolEnabledLLMClient
    return LLMFactory.create_chat_model(provider, model)


async def llm_parse_intent_node(state: ShellAgentState) -> ShellAgentState:
    """Node: Use LLM to parse user intent"""
    from src.prompts import get_prompt
    
    llm_client = get_llm_client()
    system_info = state["system_info"]
    user_input = state["user_input"]
    
    system_prompt = get_prompt("llm.parse_intent")

    user_prompt = f"""Request: "{user_input}"

Context:
- Directory: {system_info['working_directory']}
- Shell: {system_info['shell_type']}
- OS: {system_info['os_type']}

Analyze and output JSON:"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Invoke LLM
    response = await llm_client.ainvoke(messages)
    
    # Parse JSON from response with robust utility
    try:
        intent_data = extract_json_from_text(response.content)
        
        # Validate with Pydantic
        state["intent"] = CommandIntent(**intent_data)
        
        state["messages"].append(
            AIMessage(content=f"✓ Understood: {intent_data['task_description']}\nCategory: {intent_data['category']}")
        )
    except (json.JSONDecodeError, IndexError, KeyError, Exception) as e:
        # Fallback: create a generic intent
        state["intent"] = CommandIntent(
            task_description=user_input,
            category="other",
            key_entities=[],
            constraints=[],
            user_intent_confidence=0.5
        )
        state["messages"].append(
            AIMessage(content=f"⚠️ Could not parse intent (error: {type(e).__name__}). Using fallback interpretation.")
        )
    
    return state


async def llm_generate_plan_node(state: ShellAgentState) -> ShellAgentState:
    """Node: Use LLM to generate execution plan"""
    from src.prompts import get_prompt
    
    llm_client = get_llm_client()
    intent = state["intent"]
    system_info = state["system_info"]
    
    system_prompt = get_prompt("llm.generate_plan")

    user_prompt = f"""Task: {intent.task_description}
Category: {intent.category}
Entities: {intent.key_entities}
Constraints: {intent.constraints}

Context:
- Directory: {system_info['working_directory']}
- Shell: {system_info['shell_type']}
- OS: {system_info['os_type']}

Generate execution plan as JSON:"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Invoke LLM
    response = await llm_client.ainvoke(messages)
    
    # Parse JSON with error handling using robust utility
    try:
        plan_data = extract_json_from_text(response.content)
        
        # Validate with Pydantic
        state["execution_plan"] = ExecutionPlan(**plan_data)
        state["current_command_index"] = 0
        
        # Show plan
        plan_summary = "\n".join([
            f"{i+1}. [{cmd['risk_level']}] {cmd['description']}: `{cmd['cmd']}`" 
            for i, cmd in enumerate(plan_data["commands"])
        ])
        
        state["messages"].append(
            AIMessage(content=f"📋 Execution Plan:\n{plan_summary}\n\nStrategy: {plan_data['overall_strategy']}")
        )
    except (json.JSONDecodeError, IndexError, KeyError, Exception) as e:
        # Fallback: create a simple echo command plan
        state["messages"].append(
            AIMessage(content=f"❌ Could not generate execution plan (error: {type(e).__name__}).\nLLM Response: {response.content[:200]}")
        )
        # Create a minimal plan that just reports the error
        state["execution_plan"] = ExecutionPlan(
            commands=[],
            overall_strategy="Failed to generate plan",
            potential_issues=["LLM did not return valid JSON"],
            estimated_duration_seconds=0
        )
        state["current_command_index"] = 999  # Skip execution
    
    return state


async def llm_analyze_error_node(state: ShellAgentState) -> ShellAgentState:
    """Node: Use LLM to analyze errors and suggest fixes"""
    from src.prompts import get_prompt
    
    llm_client = get_llm_client()
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    current_cmd = plan.commands[idx]
    last_result = state["results"][-1]
    
    system_prompt = get_prompt("llm.analyze_error")

    user_prompt = f"""Task: {plan.overall_strategy}
Failed Command: {current_cmd.cmd}
Description: {current_cmd.description}

Error Output:
{last_result.stderr}

Exit Code: {last_result.exit_code}

Analyze and suggest fix as JSON:"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = await llm_client.ainvoke(messages)
    
    # Parse JSON with robust error handling using utility
    try:
        analysis = extract_json_from_text(response.content)
        
        state["messages"].append(
            AIMessage(content=f"""🔍 Error Analysis:
Root Cause: {analysis.get('root_cause', 'Unknown')}
Suggested Fix: {analysis.get('suggested_fix', 'None provided')}
""")
        )
        
        # Update command if should retry
        if analysis.get("should_retry") and analysis.get("modified_command"):
            # Modify the command in the plan
            state["execution_plan"].commands[idx].cmd = analysis["modified_command"]
            state["retry_count"] += 1
        else:
            state["retry_count"] = 999  # Force stop
            
    except (json.JSONDecodeError, IndexError, AttributeError, KeyError) as e:
        # LLM didn't return valid JSON - graceful degradation
        state["messages"].append(
            AIMessage(content=f"""🔍 Error Analysis (fallback):
LLM Response: {response.content[:300]}
Note: Could not parse structured analysis (error: {type(e).__name__})
""")
        )
        state["retry_count"] = 999  # Force stop - don't retry if analysis failed
    
    return state


async def llm_reflection_node(state: ShellAgentState) -> ShellAgentState:
    """Node: LLM reflects on execution and provides insights"""
    from src.prompts import get_prompt
    
    llm_client = get_llm_client()
    results = state["results"]
    plan = state["execution_plan"]
    
    system_prompt = get_prompt("llm.reflection")

    execution_summary = "\n".join([
        f"{'✓' if r.success else '✗'} {r.command}: {r.stdout[:500] if r.success else r.stderr[:500]}"
        for r in results
    ])
    
    user_prompt = f"""Original Request: {plan.overall_strategy}

Execution Output:
{execution_summary}

Provide the final answer and reflection:"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = await llm_client.ainvoke(messages)
    
    state["messages"].append(
        AIMessage(content=f"💭 Reflection:\n{response.content}")
    )
    
    return state