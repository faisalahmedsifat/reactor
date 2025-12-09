"""
src/agents/instance.py

Represents a single running instance of an agent.
Manages its own LangGraph workflow and state.
"""

import asyncio
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

# Import the graph creator from our existing implementation
# ensuring we use the EXACT same logic as the main shell
from src.graph import create_simple_shell_agent

logger = logging.getLogger("reactor.agent_instance")

class AgentInstance:
    """
    A standalone instance of an agent running in a background task.
    Wraps the LangGraph workflow and manages lifecycle/state.
    """
    
    def __init__(
        self, 
        agent_name: str, 
        task: str, 
        skill_names: List[str] = None
    ):
        self.id = str(uuid.uuid4())
        self.agent_name = agent_name
        self.task = task
        self.skill_names = skill_names or []
        
        # Lifecycle state
        self.state = "initializing"  # initializing, running, completed, error, stopped
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        
        # Execution artifacts
        self.outputs: List[str] = []
        self.error: Optional[str] = None
        self._task_handle: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        # Event callbacks for real-time streaming
        self._message_callbacks = []  # List of async callbacks: (agent_id, node_name, message)
        
        # Graph internals
        self.graph = create_simple_shell_agent()
        self.checkpointer = MemorySaver()
        self.config = {"configurable": {"thread_id": self.id}, "recursion_limit": 50}
        
    async def start(self):
        """Start the agent loop in a background task"""
        if self.state != "initializing":
            logger.warning(f"Agent {self.id} already started")
            return

        self.started_at = datetime.now()
        self.state = "running"
        self._task_handle = asyncio.create_task(self._run_loop())
        logger.info(f"Agent {self.id} ({self.agent_name}) started")

    async def stop(self):
        """Request the agent to stop"""
        if self.state in ["completed", "error", "stopped"]:
            return
            
        self._stop_event.set()
        if self._task_handle:
            self._task_handle.cancel()
            try:
                await self._task_handle
            except asyncio.CancelledError:
                pass
        
        self.state = "stopped"
        self.completed_at = datetime.now()
        logger.info(f"Agent {self.id} stopped manually")
    
    def on_message(self, callback):
        """Register a callback for new messages (for TUI streaming)"""
        self._message_callbacks.append(callback)
    
    async def _emit_message(self, node_name: str, message):
        """Notify all subscribers of a new message"""
        for callback in self._message_callbacks:
            try:
                await callback(self.id, node_name, message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")

    async def _run_loop(self):
        """Internal execution loop using LangGraph"""
        try:
            # Initialize state similar to run_simple_agent in graph.py
            initial_state = {
                "messages": [HumanMessage(content=self.task)],
                "user_input": self.task,
                "system_info": None,
                "intent": None,
                "execution_plan": None,
                "current_command_index": 0,
                "results": [],
                "retry_count": 0,
                "requires_approval": False, # Agents auto-approve for now
                "approved": True,           # Auto-approval enabled for autonomous agents
                "error": None,
                "execution_mode": "autonomous", # Special mode for agents
                "max_retries": 3,
                "analysis_data": None,
                "active_agent": self.agent_name,
                "active_skills": self.skill_names,
            }

            # Run the graph stream
            async for event in self.graph.astream(initial_state, self.config, stream_mode="updates"):
                if self._stop_event.is_set():
                    break
                    
                # Capture outputs for progress monitoring
                for node_name, node_output in event.items():
                    if "messages" in node_output and node_output["messages"]:
                        last_msg = node_output["messages"][-1]
                        content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                        
                        # Store only meaningful updates (skipping tool calls for brevity in summary)
                        if node_name == "agent" and content:
                            self.outputs.append(content)
                        
                        # Emit event for real-time streaming to TUI
                        if content and node_name in ["thinking", "agent"]:
                            await self._emit_message(node_name, last_msg)

            self.state = "completed"
            
        except asyncio.CancelledError:
            self.state = "stopped"
        except Exception as e:
            logger.error(f"Agent {self.id} failed: {e}", exc_info=True)
            self.state = "error"
            self.error = str(e)
        finally:
            self.completed_at = datetime.now()

    def get_latest_progress(self) -> str:
        """Get the last output from the agent"""
        if not self.outputs:
            return "Starting..."
        return self.outputs[-1][:200] + "..." if len(self.outputs[-1]) > 200 else self.outputs[-1]

    async def get_full_history(self) -> List[Any]:
        """
        Get the full LangGraph message history for UI rendering.
        Returns list of BaseMessage objects.
        """
        try:
            # Fetch latest state snapshot
            snapshot = await self.graph.aget_state(self.config)
            if snapshot and snapshot.values:
                return snapshot.values.get("messages", [])
            return []
        except Exception as e:
            logger.error(f"Failed to get history for {self.id}: {e}")
            return []

    def get_final_output(self) -> str:
        """Get the full final response"""
        if not self.outputs:
            return "No output produced"
        return self.outputs[-1]
