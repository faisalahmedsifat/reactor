"""
Bridge between Textual TUI and LangGraph Agent (Simple/ReAct version)
"""

import asyncio
import logging
from typing import Optional, Callable, Any, List
from src.graph import create_shell_agent
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
        self.graph = create_shell_agent()
        self.thread_id = "tui-session"
        self.running = False
        self._message_callback = None  # Callback for event-driven streaming

        if self.debug_mode:
            from src.logger import ConversationLogger

            self.chat_logger = ConversationLogger(log_file="conversation_history.md")
        else:
            from src.logger import ConversationLogger

            self.chat_logger = ConversationLogger(log_file=None)

        self.state = {}  # Initialize empty state for history tracking
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
                    if agent.get("author"):
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
                    if skill.get("author"):
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
                        "stopped": "🛑",
                    }.get(agent["state"], "❓")

                    message += f"{status_emoji} **{agent['name']}** (`{agent['id']}`)\n"
                    message += f"  Status: {agent['state']}\n"
                    message += f"  Task: {agent['task'][:60]}...\n"
                    if agent.get("skills"):
                        message += f"  Skills: {', '.join(agent['skills'])}\n"
                    if agent.get("duration"):
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

    def set_message_callback(self, callback):
        """Register callback for event-driven message streaming"""
        self._message_callback = callback

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

                    # Emit message events for thinking and agent nodes via callback
                    if node_name in ["thinking", "agent"]:
                        if "messages" in node_output and node_output["messages"]:
                            last_msg = node_output["messages"][-1]

                            # Log to conversation history
                            content = (
                                last_msg.content
                                if hasattr(last_msg, "content")
                                else str(last_msg)
                            )
                            if content:
                                if node_name == "thinking":
                                    self.chat_logger.log_turn("thought", content)
                                elif node_name == "agent":
                                    self.chat_logger.log_turn("agent", content)

                            # Emit to TUI
                            if self._message_callback:
                                await self._message_callback(
                                    "main", node_name, last_msg
                                )

                            # For agent node, also emit tool_call events
                            if (
                                node_name == "agent"
                                and hasattr(last_msg, "tool_calls")
                                and last_msg.tool_calls
                            ):
                                for tool_call in last_msg.tool_calls:
                                    if self._message_callback:
                                        await self._message_callback(
                                            "main",
                                            "tool_call",
                                            {
                                                "tool_name": tool_call["name"],
                                                "args": tool_call["args"],
                                                "tool_call_id": tool_call.get("id", ""),
                                            },
                                        )

                    # Emit tool_result events for tools node
                    elif node_name == "tools":
                        if "messages" in node_output:
                            messages = node_output["messages"]
                            if not isinstance(messages, list):
                                messages = [messages]

                            for msg in messages:
                                if (
                                    isinstance(msg, ToolMessage)
                                    and self._message_callback
                                ):
                                    # Robustly extract result (artifact or parsed content)
                                    result_data = msg.artifact

                                    # Fallback: If artifact is missing/string, try parsing content as JSON
                                    if not isinstance(result_data, dict):
                                        try:
                                            import json

                                            # Content might be a JSON string of the result dict
                                            result_data = json.loads(msg.content)
                                        except (json.JSONDecodeError, TypeError):
                                            # If not JSON, use the artifact or content as is
                                            result_data = (
                                                msg.artifact
                                                if msg.artifact is not None
                                                else msg.content
                                            )

                                    await self._message_callback(
                                        "main",
                                        "tool_result",
                                        {
                                            "tool_name": msg.name,
                                            "result": result_data,
                                            "tool_call_id": msg.tool_call_id,
                                        },
                                    )

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

    async def provide_approval(self, approved: bool) -> None:
        """Provide approval decision to agent (Pass-through for interface compatibility)"""
        # Simple graph typically doesn't pause for approval, but we keep this method
        # to avoid crashes if UI calls it.
        pass
