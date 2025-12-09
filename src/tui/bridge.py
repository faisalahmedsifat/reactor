"""
Bridge between Textual TUI and LangGraph Agent (Simple/ReAct version)
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from src.graph import create_simple_shell_agent
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.state import ShellAgentState
from src.models import ExecutionResult



class AgentBridge:
    """Bridge to connect TUI with LangGraph Agent (Simple/ReAct version)"""

    def __init__(self, tui_app: Any, debug_mode: bool = False):
        """Initialize bridge with reference to TUI app"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("AgentBridge initializing")
        
        self.tui_app = tui_app
        self.debug_mode = debug_mode
        self.graph = create_simple_shell_agent()
        self.thread_id = "tui-session"
        self.running = False

        if self.debug_mode:
            from src.logger import ConversationLogger
            self.chat_logger = ConversationLogger(log_file="conversation_history.md")
        else:
            from src.logger import ConversationLogger
            self.chat_logger = ConversationLogger(log_file=None)

        self.state = {} # Initialize empty state for history tracking
        self.logger.info("AgentBridge initialized")

    async def handle_slash_command(self, command: str) -> Optional[str]:
        """
        Handle TUI slash commands for agents and skills.
        
        Returns:
            Formatted message to display in TUI, or None if not a slash command
        """
        command = command.strip()
        
        if not command.startswith("/"):
            return None
        
        # /agents or /agent - List available agents
        if command in ["/agents", "/agent"]:
            from src.agents.loader import AgentLoader
            
            try:
                agents = AgentLoader.list_agents()
                
                if not agents:
                    return "## 📋 Available Agents\n\nNo agents found in `.reactor/agents/`"
                
                message = "## 📋 Available Agents\n\n"
                for agent in agents:
                    message += f"**{agent['name']}** (v{agent['version']})\n"
                    message += f"  {agent['description']}\n"
                    if agent.get('author'):
                        message += f"  *by {agent['author']}*\n"
                    message += "\n"
                
                message += "\n*Use `spawn_agent` tool to activate an agent*"
                return message
            except Exception as e:
                return f"❌ Error listing agents: {str(e)}"
        
        # /skills or /skill - List available skills
        elif command in ["/skills", "/skill"]:
            from src.skills.loader import SkillLoader
            
            try:
                skills = SkillLoader.list_skills()
                
                if not skills:
                    return "## 🎯 Available Skills\n\nNo skills found in `.reactor/skills/`"
                
                message = "## 🎯 Available Skills\n\n"
                for skill in skills:
                    message += f"**{skill['name']}** (v{skill['version']})\n"
                    message += f"  {skill['description']}\n"
                    if skill.get('author'):
                        message += f"  *by {skill['author']}*\n"
                    message += "\n"
                
                message += "\n*Skills are loaded automatically by agents*"
                return message
            except Exception as e:
                return f"❌ Error listing skills: {str(e)}"
        
        # /running - List running agents
        elif command == "/running":
            from src.tools.agent_tools import get_agent_manager
            
            try:
                manager = get_agent_manager()
                running = manager.list_agents()
                
                if not running:
                    return "## 🤖 Running Agents\n\nNo agents currently running"
                
                message = "## 🤖 Running Agents\n\n"
                for agent in running:
                    status_emoji = {
                        "running": "🏃",
                        "completed": "✅",
                        "error": "❌",
                        "initializing": "🔄",
                        "stopped": "🛑"
                    }.get(agent["state"], "❓")
                    
                    message += f"{status_emoji} **{agent['name']}** (`{agent['id']}`)\n"
                    message += f"  Status: {agent['state']}\n"
                    message += f"  Task: {agent['task'][:60]}...\n"
                    if agent.get('skills'):
                        message += f"  Skills: {', '.join(agent['skills'])}\n"
                    if agent.get('duration'):
                        message += f"  Duration: {agent['duration']:.1f}s\n"
                    message += "\n"
                
                stats = manager.get_stats()
                message += f"\n**Total:** {stats['total_active']} agents\n"
                message += f"**By State:** {stats['by_state']}\n\n"
                message += "*Use `/result <agent-id>` to get specific agent output*"
                
                return message
            except Exception as e:
                return f"❌ Error listing running agents: {str(e)}"
        
        # /result <agent-id> - Get specific agent result
        elif command.startswith("/result"):
            parts = command.split(maxsplit=1)
            if len(parts) < 2:
                return "**Usage:** `/result <agent-id>`\n\nExample: `/result web-researcher-a1b2c3d4`"
            
            instance_id = parts[1].strip()
            
            from src.tools.agent_tools import get_agent_manager
            
            try:
                manager = get_agent_manager()
                agent = manager.get_agent(instance_id)
                
                message = f"## 🤖 Agent Result: {agent.agent_name}\n\n"
                message += f"**ID:** `{agent.instance_id}`\n"
                message += f"**Status:** {agent.state}\n"
                message += f"**Task:** {agent.task}\n\n"
                
                if agent.state == "completed":
                    duration = (agent.completed_at - agent.created_at).total_seconds()
                    message += f"**Duration:** {duration:.1f}s\n\n"
                    message += "**Output:**\n\n"
                    message += agent.get_final_output()
                elif agent.state == "running":
                    message += "**Progress:**\n\n"
                    message += agent.get_latest_progress()
                    message += f"\n\n*Check again later for final result*"
                elif agent.state == "error":
                    message += f"**Error:**\n\n{agent.error}"
                else:
                    message += "*Agent is initializing...*"
                
                return message
            except Exception as e:
                return f"❌ Error getting agent result: {str(e)}"
        
        # /new-agent - Create new agent (triggers modal)
        elif command == "/new-agent":
            return "MODAL:new-agent"  # Special marker for TUI to open modal
        
        # /edit-agent <name> - Edit existing agent
        elif command.startswith("/edit-agent"):
            parts = command.split(maxsplit=1)
            if len(parts) < 2:
                return "**Usage:** `/edit-agent <agent-name>`\n\nExample: `/edit-agent web-researcher`"
            
            agent_name = parts[1].strip()
            return f"MODAL:edit-agent:{agent_name}"
        
        # /view-agent <name> - View agent details
        elif command.startswith("/view-agent"):
            parts = command.split(maxsplit=1)
            if len(parts) < 2:
                return "**Usage:** `/view-agent <agent-name>`\n\nExample: `/view-agent web-researcher`"
            
            agent_name = parts[1].strip()
            return f"MODAL:view-agent:{agent_name}"
        
        # /delete-agent <name> - Delete agent
        elif command.startswith("/delete-agent"):
            parts = command.split(maxsplit=1)
            if len(parts) < 2:
                return "**Usage:** `/delete-agent <agent-name>`\n\nExample: `/delete-agent my-agent`"
            
            agent_name = parts[1].strip()
            
            try:
                # Find agent file
                from pathlib import Path
                project_agent = Path.cwd() / ".reactor" / "agents" / f"{agent_name}.md"
                user_agent = Path.home() / ".reactor" / "agents" / f"{agent_name}.md"
                
                if project_agent.exists():
                    project_agent.unlink()
                    location = "project"
                elif user_agent.exists():
                    user_agent.unlink()
                    location = "user"
                else:
                    return f"❌ Agent '{agent_name}' not found"
                
                # Reload agents
                from src.agents.loader import AgentLoader
                AgentLoader.discover_agents(force_refresh=True)
                
                return f"✅ Agent '{agent_name}' deleted from {location} directory"
            except Exception as e:
                return f"❌ Error deleting agent: {str(e)}"
        
        # Unknown command
        else:
            return None

    async def process_request(
        self, user_request: str, execution_mode: str = "sequential"
    ) -> None:
        """Process user request through agent"""
        self.logger.info(f"Bridge.process_request called with: '{user_request}'")
        self.chat_logger.log_turn("user", user_request)
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
            "analysis_data": None,
        }

        config = {"configurable": {"thread_id": self.thread_id}, "recursion_limit": 200}
        
        # Notify TUI that processing started
        await self.tui_app.on_agent_start()

        try:
            # Stream execution
            event_count = 0
            async for event in self.graph.astream(
                initial_state, config, stream_mode="updates", recursion_limit=200
            ):
                event_count += 1
                for node_name, node_output in event.items():
                    self.logger.info(f"Processing node: {node_name}")

                    if node_name == "thinking":
                        await self.handle_thinking_node(node_output)
                    elif node_name == "agent":
                        await self.handle_agent_node(node_output)
                    elif node_name == "tools":
                        await self.handle_tools_node(node_output)

                    # Always call the standard handler too for generic updates
                    await self.tui_app.on_node_update(node_name, node_output)

            self.logger.info("Agent execution completed")

            # Fetch final state to pass to on_agent_complete
            final_snapshot = await self.graph.aget_state(config)
            self.state = final_snapshot.values
            await self.tui_app.on_agent_complete(self.state)

        except Exception as e:
            import traceback

            error_msg = f"{str(e)}\\n{traceback.format_exc()}"
            self.logger.error(f"Exception in bridge: {error_msg}")
            await self.tui_app.on_agent_error(error_msg)
        finally:
            self.running = False
            self.logger.info("Bridge processing complete")

    async def handle_thinking_node(self, node_output: dict) -> None:
        """Handle output from difference thinking node"""
        # Debug trace
        if self.debug_mode:
            with open("debug_thoughts.log", "a") as f:
                f.write(f"Thinking node RAW: {str(node_output)}\n")

        if "messages" in node_output and node_output["messages"]:
            last_msg = node_output["messages"][-1]
            
            # Extract content robustly (handle object or dict)
            content_text = ""
            msg_type = type(last_msg)
            
            # Case 1: Object (serialized)
            if hasattr(last_msg, "content"):
                if isinstance(last_msg.content, str):
                    content_text = last_msg.content
                elif isinstance(last_msg.content, list):
                    for block in last_msg.content:
                         if isinstance(block, dict) and "text" in block:
                             content_text += block["text"]
                         # object block access usually block.text if object
            
            # Case 2: Dictionary (json)
            elif isinstance(last_msg, dict):
                content_text = last_msg.get("content", "")
            
            if self.debug_mode:
                with open("debug_thoughts.log", "a") as f:
                    f.write(f"Parsed Content ({msg_type}): {content_text[:50]}...\n")

            if content_text.strip():
                dashboard = self.tui_app.query_one("AgentDashboard")
                log_viewer = dashboard.query_one("#log-viewer")
                log_viewer.add_log(content_text, "thought")
                self.chat_logger.log_turn("agent", f"Thinking: {content_text}")

    async def handle_agent_node(self, node_output: dict) -> None:
        """Handle output from the Agent (Tool Selector) node"""
        if "messages" in node_output and node_output["messages"]:
            last_msg = node_output["messages"][-1]
            if isinstance(last_msg, AIMessage):
                # We primarily expect Tool Calls here, but final answer might be here too.

                # Extract text content (for final answer)
                content_text = ""
                if isinstance(last_msg.content, str):
                    content_text = last_msg.content
                elif isinstance(last_msg.content, list):
                    for block in last_msg.content:
                        if isinstance(block, dict) and "text" in block:
                            content_text += block["text"]
                        elif hasattr(block, "text"):
                            content_text += block.text
                        elif isinstance(block, str):
                            content_text += block

                # Log text ONLY if it is NOT just a tool call preamble/empty
                # Since ThinkingNode already outputted the thought, we might get duplicate text if we are not careful.
                # Usually standard ReAct prompt makes LLM output "Thought: ... Tool: ..."
                # With our split, ThinkingNode did "Thought". AgentNode does "Tool".
                # But AgentNode might still output some text.
                # Let's log it if it's substantial, otherwise assume it's covered by Thinking.
                if content_text.strip():
                    dashboard = self.tui_app.query_one("AgentDashboard")
                    log_viewer = dashboard.query_one("#log-viewer")
                    log_viewer.add_log(content_text, "agent")
                    self.chat_logger.log_turn("agent", content_text)

                # Check for tool calls (The main purpose of this node now)
                if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                    for tool_call in last_msg.tool_calls:
                        tool_name = tool_call["name"]
                        args = tool_call["args"]
                        # Log this as a "Plan" or "Intent"
                        dashboard = self.tui_app.query_one("AgentDashboard")
                        log_viewer = dashboard.query_one("#log-viewer")

                        # Use special formatting for different tools
                        # Use special formatting for different tools
                        if tool_name == "execute_shell_command":
                            cmd = args.get("command", "unknown")
                            log_viewer.add_log(
                                f"🛠️ Executing: `{cmd}`", "info", is_thought=False
                            )
                            # IMMEDIATE FEEDBACK: Start Live Monitoring
                            try:
                                live_panel = self.tui_app.query_one(
                                    "LiveExecutionPanel"
                                )
                                live_panel.start_monitoring(cmd)
                            except Exception as e:
                                self.logger.error(f"Failed to set live panel: {e}")
                        elif tool_name in ["write_file", "modify_file", "read_file_content"]:
                            fpath = (
                                args.get("target_file")
                                or args.get("file_path")
                                or "unknown"
                            )
                            basename = fpath.split("/")[-1] if fpath else "unknown"
                            log_viewer.add_log(
                                f"🛠️ File Op ({tool_name}): `{basename}`",
                                "info",
                                is_thought=False,
                            )
                            pass # CodeViewer update removed
                            log_viewer.add_log(
                                f"🛠️ Using tool: {tool_name}", "info", is_thought=False
                            )

        # Force a refresh of the Todo panel at the end of processing any tool
        # This catches cases where the agent did multiple ops or finished a task
        try:
            from src.tools.todo_tools import get_todos_for_ui

            todo_panel = self.tui_app.query_one("TODOPanel")
            todos = get_todos_for_ui()
            todo_panel.update_todos(todos)
        except Exception:
            pass

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
                self.logger.info(f"Processing ToolMessage: {msg.name} id={msg.tool_call_id}")
                await self.process_tool_result(msg)

    async def process_tool_result(self, tool_msg: ToolMessage) -> None:
        """Process a single tool result for UI updates"""
        tool_name = tool_msg.name
        self.logger.info(f"Bridge processing tool result for: {tool_name}")

        # We primarily care about execution results for the specialized UI panels
        if tool_name == "execute_shell_command":
            # The artifact should be the dict returned by the tool
            result_data = tool_msg.artifact

            # If artifact is string (sometimes happens with simple tools), try to parse or log warning
            if isinstance(result_data, str):
                self.logger.warning(f"Tool artifact is string: {result_data}")
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
                    self.logger.error(f"Failed to update LiveExecutionPanel: {e}")

                # 2. Results List
                try:
                    results_panel = self.tui_app.query_one("ResultsPanel")
                    # Append using the app's shared list
                    self.tui_app.execution_results.append(exec_result)
                    results_panel.update_results(self.tui_app.execution_results)
                except Exception as e:
                    self.logger.error(f"Failed to update ResultsPanel: {e}")

        elif tool_name in ["create_todo", "complete_todo", "update_todo", "list_todos"]:
            # Update TODO Panel
            try:
                from src.tools.todo_tools import get_todos_for_ui

                todo_panel = self.tui_app.query_one("TODOPanel")
                # accessing .todos directly or via updating method if it exists
                # The widget has update_todos method
                todos = get_todos_for_ui()
                self.logger.info(f"Updating TODOPanel with {len(todos)} items")
                todo_panel.update_todos(todos)
            except Exception as e:
                self.logger.error(f"Failed to update TODOPanel: {e}")

    async def provide_approval(self, approved: bool) -> None:
        """Provide approval decision to agent (Pass-through for interface compatibility)"""
        # Simple graph typically doesn't pause for approval, but we keep this method
        # to avoid crashes if UI calls it.
        pass
