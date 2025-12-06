"""Execution and utility nodes"""

from langchain_core.messages import AIMessage
from src.state import ShellAgentState
from src.tools import shell_tools
from src.models import ExecutionResult
from datetime import datetime

async def gather_system_info_node(state: ShellAgentState) -> ShellAgentState:
    """Gather system information"""
    info = await shell_tools.get_system_info.ainvoke({})
    state["system_info"] = info
    state["messages"].append(
        AIMessage(content=f"System: {info['os_type']} | Shell: {info['shell_type']} | Dir: {info['working_directory']}")
    )
    return state

async def validate_safety_node(state: ShellAgentState) -> ShellAgentState:
    """Validate command safety"""
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    
    if idx >= len(plan.commands):
        return state
    
    current_cmd = plan.commands[idx]
    
    safety = await shell_tools.validate_command_safety.ainvoke({
        "command": current_cmd.cmd
    })
    
    state["requires_approval"] = safety["requires_approval"]
    
    if safety["warnings"]:
        state["messages"].append(
            AIMessage(content=f"⚠️  Safety warnings: {', '.join(safety['warnings'])}")
        )
    
    return state

async def execute_command_node(state: ShellAgentState) -> ShellAgentState:
    """Execute shell command"""
    plan = state["execution_plan"]
    idx = state["current_command_index"]
    system_info = state["system_info"]
    
    if idx >= len(plan.commands):
        return state
    
    current_cmd = plan.commands[idx]
    
    result = await shell_tools.execute_shell_command.ainvoke({
        "command": current_cmd.cmd,
        "working_directory": system_info["working_directory"],
        "timeout": 30,
        "dry_run": False
    })
    
    exec_result = ExecutionResult(
        command=current_cmd.cmd,
        success=result["success"],
        stdout=result["stdout"],
        stderr=result["stderr"],
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        timestamp=datetime.now()
    )
    
    state["results"].append(exec_result)
    
    if result["success"]:
        state["messages"].append(
            AIMessage(content=f"✅ Success: {current_cmd.cmd}\n{result['stdout'][:300]}")
        )
        state["current_command_index"] += 1
        state["retry_count"] = 0
    else:
        state["error"] = result["stderr"]
        state["messages"].append(
            AIMessage(content=f"❌ Failed: {current_cmd.cmd}\n{result['stderr'][:300]}")
        )
    
    return state

async def summarize_node(state: ShellAgentState) -> ShellAgentState:
    """Final summary"""
    results = state["results"]
    total = len(results)
    successful = sum(1 for r in results if r.success)
    
    if total == 0:
        summary = "No commands were executed."
    else:
        summary = f"""
📊 EXECUTION SUMMARY
{'='*60}
Total Commands: {total}
Successful: {successful}
Failed: {total - successful}
Success Rate: {successful/total*100:.1f}%

Commands Executed:
{chr(10).join([f"  {'✓' if r.success else '✗'} {r.command}" for r in results])}
"""
    
    state["messages"].append(AIMessage(content=summary))
    return state