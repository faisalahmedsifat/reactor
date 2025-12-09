"""
src/tools/agent_tools.py

Agent tools for spawning and managing parallel agent instances.
"""

from langchain_core.tools import tool
from typing import Dict, Any, Optional, List


# Global agent manager instance
_agent_manager = None


def get_agent_manager():
    """Get or create global AgentManager instance"""
    global _agent_manager
    if _agent_manager is None:
        from src.agents.manager import AgentManager
        _agent_manager = AgentManager()
    return _agent_manager


@tool
async def spawn_agent(
    agent_name: str,
    task: str
) -> Dict[str, Any]:
    """
    Spawn a specialized agent to handle a specific task in parallel.
    
    The agent automatically loads its required skills from its definition.
    Each agent runs independently with its own conversation thread.
    
    Use this when:
    - Task requires specialized expertise (web research, code review, data analysis)
    - Task can be delegated while you work on other things
    - You want multiple perspectives on a problem
    - Long-running task that can happen in background
    
    Args:
        agent_name: Name of agent to spawn (e.g., "web-researcher", "code-reviewer")
        task: Specific task description for the agent
        
    Returns:
        Dict with:
        - instance_id: Unique ID to track this agent
        - status: "spawned" or "error"
        - skills_loaded: List of skills auto-loaded for this agent
        - message: Human-readable status message
    
    Example:
        # Spawn web researcher
        result = spawn_agent(
            agent_name="web-researcher",
            task="Find 10 smartphones with 8GB RAM under 15k BDT"
        )
        
        # Agent runs in background, check later with:
        # get_agent_result(result["instance_id"])
    """
    manager = get_agent_manager()
    
    try:
        # Load agent configuration to get its required skills
        from src.agents.loader import AgentLoader
        agent_config = AgentLoader.load_agent(agent_name)
        
        # Spawn agent with auto-loaded skills
        instance_id = await manager.spawn_agent(
            agent_name=agent_name,
            task=task,
            skill_names=agent_config.required_skills
        )
        
        skills_msg = ", ".join(agent_config.required_skills) if agent_config.required_skills else "none"
        
        return {
            "instance_id": instance_id,
            "status": "spawned",
            "agent_name": agent_name,
            "task": task,
            "skills_loaded": agent_config.required_skills,
            "message": f"✅ Agent '{agent_name}' spawned successfully\nID: {instance_id}\nSkills: {skills_msg}\n\nAgent is running in background. Use get_agent_result('{instance_id}') to check status."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Failed to spawn agent: {str(e)}"
        }


@tool
async def get_agent_result(instance_id: str) -> Dict[str, Any]:
    """
    Get the current result/status of a running agent.
    
    Use this to check on agents you've spawned with spawn_agent.
    
    Args:
        instance_id: ID returned from spawn_agent
        
    Returns:
        Dict with:
        - status: "running", "completed", "error", "initializing"
        - output: Agent's final output (if completed)
        - progress: Current progress message (if running)
        - duration: Time elapsed (if completed)
        
    Example:
        result = get_agent_result("web-researcher-a1b2c3d4")
        if result["status"] == "completed":
            print(result["output"])
    """
    manager = get_agent_manager()
    
    try:
        agent = manager.get_agent(instance_id)
        
        base_result = {
            "instance_id": instance_id,
            "agent_name": agent.agent_name,
            "task": agent.task,
            "status": agent.state,
            "skills": agent.skill_names
        }
        
        if agent.state == "completed":
            duration = (agent.completed_at - agent.created_at).total_seconds()
            return {
                **base_result,
                "output": agent.get_final_output(),
                "duration_seconds": duration,
                "message": f"✅ Agent completed in {duration:.1f}s"
            }
        
        elif agent.state == "error":
            return {
                **base_result,
                "error": agent.error,
                "message": f"❌ Agent encountered an error: {agent.error}"
            }
        
        elif agent.state == "running":
            return {
                **base_result,
                "progress": agent.get_latest_progress(),
                "outputs_so_far": len(agent.outputs),
                "message": f"🏃 Agent is running...\n{agent.get_latest_progress()}"
            }
        
        else:  # initializing
            return {
                **base_result,
                "message": "🔄 Agent is initializing..."
            }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error getting agent result: {str(e)}"
        }


@tool
def list_available_agents() -> Dict[str, Any]:
    """
    List all available agents that can be spawned.
    
    Shows what specialized agents are available in your .reactor/agents/ directory.
    
    Returns:
        Dict with list of agents and their descriptions
        
    Example:
        agents = list_available_agents()
        for agent in agents["agents"]:
            print(f"{agent['name']}: {agent['description']}")
    """
    from src.agents.loader import AgentLoader
    
    try:
        agents = AgentLoader.list_agents()
        
        message = "📋 Available Agents:\n\n"
        for agent in agents:
            message += f"• {agent['name']} (v{agent['version']})\n"
            message += f"  {agent['description']}\n\n"
        
        return {
            "agents": agents,
            "count": len(agents),
            "message": message
        }
    except Exception as e:
        return {
            "agents": [],
            "count": 0,
            "message": f"❌ Error listing agents: {str(e)}"
        }


@tool
def list_running_agents() -> Dict[str, Any]:
    """
    List all currently running agent instances.
    
    Shows all agents you've spawned that are still active.
    
    Returns:
        Dict with list of running agents and their status
        
    Example:
        running = list_running_agents()
        for agent in running["running_agents"]:
            print(f"{agent['name']} is {agent['state']}")
    """
    manager = get_agent_manager()
    
    try:
        running = manager.list_agents()
        
        if not running:
            return {
                "running_agents": [],
                "count": 0,
                "message": "No agents currently running"
            }
        
        message = "🤖 Running Agents:\n\n"
        for agent in running:
            status_emoji = {
                "running": "🏃",
                "completed": "✅",
                "error": "❌",
                "initializing": "🔄"
            }.get(agent["state"], "❓")
            
            message += f"{status_emoji} {agent['name']} ({agent['id']})\n"
            message += f"  Status: {agent['state']}\n"
            message += f"  Task: {agent['task'][:60]}...\n"
            if agent['skills']:
                message += f"  Skills: {', '.join(agent['skills'])}\n"
            message += "\n"
        
        stats = manager.get_stats()
        message += f"\nTotal: {stats['total_active']} agents\n"
        message += f"By state: {stats['by_state']}"
        
        return {
            "running_agents": running,
            "count": len(running),
            "stats": stats,
            "message": message
        }
    except Exception as e:
        return {
            "running_agents": [],
            "count": 0,
            "message": f"❌ Error listing running agents: {str(e)}"
        }


@tool
async def stop_agent(instance_id: str) -> Dict[str, Any]:
    """
    Stop a running agent.
    
    Useful if an agent is taking too long or you no longer need its results.
    
    Args:
        instance_id: ID of agent to stop
        
    Returns:
        Dict with status message
        
    Example:
        stop_agent("web-researcher-a1b2c3d4")
    """
    manager = get_agent_manager()
    
    try:
        await manager.stop_agent(instance_id)
        return {
            "status": "stopped",
            "message": f"✅ Agent {instance_id} stopped successfully"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error stopping agent: {str(e)}"
        }
