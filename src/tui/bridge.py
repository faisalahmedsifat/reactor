"""
Bridge between Textual TUI and LangGraph Agent (Simple/ReAct version)
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from src.graph_simple import create_simple_shell_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.state import ShellAgentState
from src.models import ExecutionResult

# Setup logging
logger = logging.getLogger(__name__)

class AgentBridge:
    """Bridge to connect TUI with LangGraph Agent (Simple/ReAct version)"""
    
    def __init__(self, tui_app: Any):
        """Initialize bridge with reference to TUI app"""
        logger.info("AgentBridge initializing")
        self.tui_app = tui_app
        self.graph = create_simple_shell_agent()
        self.thread_id = "tui-session"
        self.running = False
        logger.info("AgentBridge initialized")
        
    async def process_request(self, user_request: str, execution_mode: str = "sequential") -> None:
        """Process user request through agent"""
        logger.info(f"Bridge.process_request called with: '{user_request}'")
        self.running = True
        
        # Initialize state compatibly with simple graph
        initial_state = {
            "messages": [HumanMessage(content=user_request)],
            "user_input": user_request,
            "system_info": None,
            "results": [],
            # Keep other keys for potential compatibility
            "intent": None,
            "execution_plan": None,
            "current_command_index": 0,
            "retry_count": 0,
            "requires_approval": False,
            "approved": False,
            "error": None,
            "execution_mode": execution_mode,
            "max_retries": 3,
            "analysis_data": None
        }
        
        config = {
            "configurable": {"thread_id": self.thread_id},
            "recursion_limit": 50
        }
        
        # Notify TUI that processing started
        await self.tui_app.on_agent_start()
        
        try:
            # Stream execution
            event_count = 0
            async for event in self.graph.astream(initial_state, config, stream_mode="updates"):
                event_count += 1
                for node_name, node_output in event.items():
                    logger.info(f"Processing node: {node_name}")
                    
                    if node_name == "agent":
                        await self.handle_agent_node(node_output)
                    elif node_name == "tools":
                        await self.handle_tools_node(node_output)
                    
                    # Always call the standard handler too for generic updates
                    await self.tui_app.on_node_update(node_name, node_output)
            
            logger.info("Agent execution completed")
            
            # Fetch final state to pass to on_agent_complete
            state = await self.graph.aget_state(config)
            await self.tui_app.on_agent_complete(state.values)
                
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\\n{traceback.format_exc()}"
            logger.error(f"Exception in bridge: {error_msg}")
            await self.tui_app.on_agent_error(error_msg)
        finally:
            self.running = False
            logger.info("Bridge processing complete")
    
    async def handle_agent_node(self, node_output: dict) -> None:
        """Handle output from the Agent (LLM) node"""
        if "messages" in node_output and node_output["messages"]:
            last_msg = node_output["messages"][-1]
            if isinstance(last_msg, AIMessage):
                # Extract text content
                content_text = ""
                if isinstance(last_msg.content, str):
                    content_text = last_msg.content
                elif isinstance(last_msg.content, list):
                    # Handle list of content blocks (e.g. from Anthropic/Google)
                    for block in last_msg.content:
                        if isinstance(block, dict) and "text" in block:
                            content_text += block["text"]
                        elif hasattr(block, "text"): # Object with text attr
                            content_text += block.text
                        elif isinstance(block, str):
                            content_text += block
                
                # Log thought process / response if there is text
                if content_text.strip():
                    dashboard = self.tui_app.query_one("AgentDashboard")
                    log_viewer = dashboard.query_one("#log-viewer")
                    log_viewer.add_log(content_text, "agent")
                
                # Check for tool calls to display intent
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tool_call in last_msg.tool_calls:
                        tool_name = tool_call["name"]
                        args = tool_call["args"]
                        # Log this as a "Plan" or "Intent"
                        dashboard = self.tui_app.query_one("AgentDashboard")
                        log_viewer = dashboard.query_one("#log-viewer")
                        
                        # Use special formatting for different tools
                        if tool_name == "execute_shell_command":
                            cmd = args.get("command", "unknown")
                            log_viewer.add_log(f"🛠️ Executing: `{cmd}`", "info", is_thought=True)
                        else:
                            log_viewer.add_log(f"🛠️ Using tool: {tool_name}", "info", is_thought=True)

    async def handle_tools_node(self, node_output: dict) -> None:
        """Handle output from the Tools node"""
        if "messages" not in node_output:
            return
            
        messages = node_output["messages"]
        # In 'updates' mode, this usually contains just the new messages from the node
        # But 'tools' node can return multiple messages if multiple tools ran in parallel
        
        # Ensure messages is a list
        if not isinstance(messages, list):
            messages = [messages]
            
        for msg in messages:
            if isinstance(msg, ToolMessage):
                await self.process_tool_result(msg)

    async def process_tool_result(self, tool_msg: ToolMessage) -> None:
        """Process a single tool result for UI updates"""
        tool_name = tool_msg.name
        
        # We primarily care about execution results for the specialized UI panels
        if tool_name == "execute_shell_command":
            # The artifact should be the dict returned by the tool
            result_data = tool_msg.artifact
            
            # If artifact is string (sometimes happens with simple tools), try to parse or log warning
            if isinstance(result_data, str):
                logger.warning(f"Tool artifact is string: {result_data}")
                return

            if isinstance(result_data, dict):
                # Create ExecutionResult object
                exec_result = ExecutionResult(
                    command=result_data.get("command", "[Unknown Command]"),
                    success=result_data.get("success", False),
                    stdout=str(result_data.get("stdout", "")),
                    stderr=str(result_data.get("stderr", "")),
                    exit_code=result_data.get("exit_code", 0),
                    duration_ms=result_data.get("duration_ms", 0.0),
                    # timestamp is auto-filled
                )
                
                # Update UI
                # 1. Live Panel
                try:
                    live_panel = self.tui_app.query_one("LiveExecutionPanel")
                    live_panel.set_content(exec_result)
                    live_panel.remove_class("-hidden")
                    # Force visibility via style if class removal isn't enough
                    live_panel.styles.display = "block" 
                except Exception as e:
                    logger.error(f"Failed to update LiveExecutionPanel: {e}")
                
                # 2. Results List
                try:
                    results_panel = self.tui_app.query_one("ResultsPanel")
                    # Append using the app's shared list
                    self.tui_app.execution_results.append(exec_result)
                    results_panel.update_results(self.tui_app.execution_results)
                except Exception as e:
                    logger.error(f"Failed to update ResultsPanel: {e}")

    async def provide_approval(self, approved: bool) -> None:
        """Provide approval decision to agent (Pass-through for interface compatibility)"""
        # Simple graph typically doesn't pause for approval, but we keep this method
        # to avoid crashes if UI calls it.
        pass
