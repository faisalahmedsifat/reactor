"""
src/agents/manager.py

Singleton manager for handling parallel agent instances.
"""

import asyncio
from typing import Dict, List, Optional, Any
from src.agents.instance import AgentInstance

class AgentManager:
    """
    Singleton manager for spawning, tracking, and stopping parallel agent instances.
    """
    
    _instance = None
    _agents: Dict[str, AgentInstance] = {}
    _tui_callback = None  # Callback for real-time message streaming
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._agents = {}
        return cls._instance

    async def spawn_agent(
        self, 
        agent_name: str, 
        task: str, 
        skill_names: List[str] = None
    ) -> str:
        """
        Create and start a new agent instance.
        
        Args:
            agent_name: Name of the agent config to load
            task: Task description
            skill_names: Optional list of skills
            
        Returns:
            instance_id: Unique ID for the spawned agent
        """
        # Create instance
        instance = AgentInstance(agent_name, task, skill_names)
        
        # Register TUI callback if available
        if self._tui_callback:
            instance.on_message(self._tui_callback)
        
        # Store in registry
        self._agents[instance.id] = instance
        
        # Start execution
        await instance.start()
        
        return instance.id
    
    def set_tui_callback(self, callback):
        """Set callback for real-time message streaming to TUI"""
        self._tui_callback = callback

    def get_agent(self, instance_id: str) -> AgentInstance:
        """
        Get an agent instance by ID.
        
        Raises:
            ValueError: If agent not found
        """
        if instance_id not in self._agents:
            # Check if it's an alias/short ID (first 8 chars)
            matches = [aid for aid in self._agents if aid.startswith(instance_id)]
            if len(matches) == 1:
                instance_id = matches[0]
            else:
                raise ValueError(f"Agent instance '{instance_id}' not found")
                
        return self._agents[instance_id]

    async def get_agent_history(self, instance_id: str) -> List[Any]:
        """Get the full message history for an agent instance."""
        try:
            agent = self.get_agent(instance_id)
            return await agent.get_full_history()
        except Exception:
            return []

    async def stop_agent(self, instance_id: str):
        """Stop a running agent instance"""
        agent = self.get_agent(instance_id)
        await agent.stop()

    async def send_message(self, instance_id: str, message: str):
        """Send a message to a specific agent instance"""
        agent = self.get_agent(instance_id)
        await agent.send_message(message)

    def list_agents(self) -> List[Dict[str, str]]:
        """List all managed agents and their statuses"""
        listing = []
        for aid, agent in self._agents.items():
            listing.append({
                "id": aid,
                "name": agent.agent_name,
                "task": agent.task,
                "state": agent.state,
                "skills": agent.skill_names,
                "created_at": agent.created_at.isoformat(),
                "started_at": agent.started_at.isoformat() if agent.started_at else None,
                "completed_at": agent.completed_at.isoformat() if agent.completed_at else None,
            })
        return listing

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics"""
        total = len(self._agents)
        by_state = {}
        for agent in self._agents.values():
            state = agent.state
            by_state[state] = by_state.get(state, 0) + 1
            
        return {
            "total_active": total,
            "by_state": by_state
        }

    async def shutdown(self):
        """Stop all agents (e.g. on app exit)"""
        tasks = []
        for agent in self._agents.values():
            if agent.state == "running":
                tasks.append(agent.stop())
        
        if tasks:
            await asyncio.gather(*tasks)
