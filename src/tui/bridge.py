"""
Bridge between Textual TUI and LangGraph Agent
"""

import asyncio
import logging
from typing import Optional, Callable, Any
from src.graph import create_complete_shell_agent
from langchain_core.messages import HumanMessage
from src.state import ShellAgentState

# Setup logging
logger = logging.getLogger(__name__)

# Communication nodes that should be displayed prominently
COMMUNICATION_NODES = ["communicate_understanding", "communicate_plan", "stream_progress"]


class AgentBridge:
    """Bridge to connect TUI with LangGraph agent"""
    
    def __init__(self, tui_app: Any):
        """Initialize bridge with reference to TUI app"""
        logger.info("AgentBridge initializing")
        self.tui_app = tui_app
        self.graph = create_complete_shell_agent()
        self.thread_id = "tui-session"
        self.running = False
        logger.info("AgentBridge initialized")
        
    async def process_request(self, user_request: str, execution_mode: str = "sequential") -> None:
        """Process user request through agent"""
        logger.info(f"Bridge.process_request called with: '{user_request}', mode: {execution_mode}")
        self.running = True
        
        initial_state = {
            "messages": [HumanMessage(content=user_request)],
            "user_input": user_request,
            "system_info": None,
            "intent": None,
            "execution_plan": None,
            "current_command_index": 0,
            "results": [],
            "retry_count": 0,
            "requires_approval": False,
            "approved": False,
            "error": None,
            "execution_mode": execution_mode,
            "max_retries": 3
        }
        
        config = {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": 50
        }
        
        # Notify TUI that processing started
        logger.info("Calling on_agent_start")
        await self.tui_app.on_agent_start()
        
        logger.info("Starting agent stream")
        
        try:
            # Stream execution
            event_count = 0
            async for event in self.graph.astream(initial_state, config, stream_mode="updates"):
                event_count += 1
                logger.info(f"Event #{event_count}: {list(event.keys())}")
                for node_name, node_output in event.items():
                    logger.info(f"Processing node: {node_name}")
                    
                    # Handle communication nodes specially
                    if node_name in COMMUNICATION_NODES:
                        await self.handle_communication_node(node_name, node_output)
                    elif node_name == "llm_analyze_error":
                        await self.handle_retry_analysis(node_output)
                    
                    # Always call the standard handler too
                    await self.tui_app.on_node_update(node_name, node_output)
            
            logger.info(f"Streamed {event_count} events total")
            
            # Check if interrupted for approval
            state = await self.graph.aget_state(config)
            
            logger.info(f"Final state - next nodes: {state.next}")
            
            if state.next and "request_approval" in state.next:
                # Agent is waiting for approval
                logger.info("Calling on_approval_required")
                await self.tui_app.on_approval_required(state.values)
            else:
                # Agent completed
                logger.info("Calling on_agent_complete")
                await self.tui_app.on_agent_complete(state.values)
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\\n{traceback.format_exc()}"
            logger.error(f"Exception in bridge: {error_msg}")
            await self.tui_app.on_agent_error(error_msg)
        finally:
            self.running = False
            logger.info("Bridge processing complete")
    
    async def handle_communication_node(self, node_name: str, node_output: dict) -> None:
        """Special handling for communication nodes"""
        dashboard = self.tui_app.query_one("AgentDashboard")
        log_viewer = dashboard.query_one("#log-viewer")
        
        if "messages" in node_output and node_output["messages"]:
            message = node_output["messages"][-1].content
            # Messages already have emoji prefixes from communication_nodes.py
            log_viewer.add_log(message, "info")
    
    async def handle_retry_analysis(self, node_output: dict) -> None:
        """Special handling for retry/error analysis"""
        dashboard = self.tui_app.query_one("AgentDashboard")
        log_viewer = dashboard.query_one("#log-viewer")
        
        retry_count = node_output.get("retry_count", 0)
        max_retries = node_output.get("max_retries", 3)
        log_viewer.add_log(f"🔄 Analyzing error (Retry {retry_count}/{max_retries})...", "warning")
    
    async def provide_approval(self, approved: bool) -> None:
        """Provide approval decision to agent"""
        config = {"configurable": {"thread_id": self.thread_id}}
        
        # Update state with approval
        await self.graph.aupdate_state(
            config,
            {"approved": approved, "requires_approval": False}
        )
        
        # Continue execution if approved
        if approved:
            try:
                async for event in self.graph.astream(None, config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_name in COMMUNICATION_NODES:
                            await self.handle_communication_node(node_name, node_output)
                        await self.tui_app.on_node_update(node_name, node_output)
                
                # Check final state
                state = await self.graph.aget_state(config)
                await self.tui_app.on_agent_complete(state.values)
                
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\\n{traceback.format_exc()}"
                await self.tui_app.on_agent_error(error_msg)
        else:
            await self.tui_app.on_approval_rejected()
