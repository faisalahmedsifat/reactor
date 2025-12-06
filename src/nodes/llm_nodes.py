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
    
    llm_client = get_llm_client()
    system_info = state["system_info"]
    user_input = state["user_input"]
    
    system_prompt = """You are an expert shell command interpreter.
    
    Analyze user requests to understand their goals. Extract:
    - Core task description
    - Operation category
    - Relevant entities (files, packages, directories)
    - Constraints or safety requirements
    - Your confidence level (0-1)
    
    Output ONLY valid JSON matching this schema:
    {
      "task_description": "clear description of what user wants",
      "category": "file_operation|environment_setup|package_management|git_operation|system_info|process_management|network_operation|other",
      "key_entities": ["list", "of", "relevant", "items"],
      "constraints": ["any", "safety", "or", "requirement", "constraints"],
      "user_intent_confidence": 0.9
    }"""

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
    
    llm_client = get_llm_client()
    intent = state["intent"]
    system_info = state["system_info"]
    
    system_prompt = """You are an expert systems administrator.

    Generate safe, efficient shell commands. Rules:
    1. NEVER risk data loss without confirmation
    2. Check tool/file existence first
    3. Prefer non-destructive operations
    4. Backup before modifying critical files
    5. Explain every command clearly
    
    Output ONLY valid JSON matching this schema:
    {
      "commands": [
        {
          "cmd": "actual shell command",
          "description": "what this does",
          "reasoning": "why this approach",
          "risk_level": "safe|moderate|dangerous",
          "reversible": true,
          "dependencies": [0, 1]
        }
      ],
      "overall_strategy": "high-level approach",
      "potential_issues": ["possible", "problems"],
      "estimated_duration_seconds": 10
    }"""

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
    
    llm_client = get_llm_client()
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    current_cmd = plan.commands[idx]
    last_result = state["results"][-1]
    
    system_prompt = """You are an expert debugger.

    Analyze command failures and provide:
    - Root cause analysis
    - Suggested fix (new command or approach)
    - Whether to retry automatically
    
    Output ONLY valid JSON:
    {
      "root_cause": "detailed explanation",
      "suggested_fix": "corrected command or approach",
      "should_retry": true,
      "modified_command": "fixed command string"
    }"""

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
    
    llm_client = get_llm_client()
    results = state["results"]
    plan = state["execution_plan"]
    
    system_prompt = """Review command execution results and provide a Final Response to the user.
    
    CRITICAL: Your primary goal is to ANSWER the user's original request based on the command outputs.
    
    Structure your response as follows:
    
    ## 📝 Answer
    [Direct, comprehensive answer to the user's question. Focus on the results found.]
    
    ## 💭 Expert Critique & Improvements
    [Critically analyze the process. Identify inefficiencies, missing checks, or better "Power-User" approaches. Suggest concrete architectural or command improvements. Be technical and harsh if necessary to improve quality.]"""

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