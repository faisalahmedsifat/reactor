"""
Powerhouse TUI Application for ReACTOR
"""

import logging
import time
import sys
from typing import List
from textual.app import App, ComposeResult
from textual import work, on
from textual.containers import Container, Vertical
from textual.widgets import Header, Input, Static
from textual.binding import Binding
from textual.reactive import reactive
from pathlib import Path

from src.tui.state import TUIState, AgentState
from src.tui.widgets import (
    FileExplorer,
    CodeViewer,
    AgentDashboard,
    StatusBar,
)
from src.tui.screens.fuzzy_finder_modal import FuzzyFinder
from src.tui.screens.command_palette_modal import CommandPalette
from textual.widgets import (
    Header,
    Footer,
    Static,
    Input,
    Button,
    Label,
    Markdown,
    TabbedContent,
    TabPane,
    Log,
    DirectoryTree,
)
from src.tui.screens.file_reference_modal import FileReferenceModal
from src.tui.widgets.todo_panel import TODOPanel
from src.tui.widgets.agent_ui import (
    StateIndicator,
    InteractiveShellPanel,
    ChatInput,
)
from src.tui.widgets.active_agents import ActiveAgents
from src.tui.bridge import AgentBridge
from src.models import ExecutionResult, ExecutionPlan

# Reuse the StatusBar from the old widgets if possible, or redefine it here/in widgets
# I'll quickly redefine a compatible StatusBar for the footer
from textual.widgets import Static


class ShellAgentTUI(App):
    """Powerhouse TUI for ReACTOR"""

    CSS_PATH = "styles/app.tcss"
    TITLE = "ReACTOR IDE"

    BINDINGS = [
        Binding("ctrl+c", "request_quit", "Quit", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+backslash", "toggle_context", "Context Panel"),
        Binding("ctrl+p", "fuzzy_find", "Find File"),
        Binding("ctrl+shift+p", "command_palette", "Command Palette"),
        Binding("escape", "cancel_agent", "Cancel Agent"),
    ]

    # Global Reactive State
    show_sidebar = reactive(True)
    show_context = reactive(True)

    def __init__(self, debug_mode: bool = False):
        super().__init__()
        self.debug_mode = debug_mode
        self.bridge = AgentBridge(self)
        self.state = TUIState()
        self.execution_results: List[ExecutionResult] = []
        self.agent_worker = None  # Track running agent worker
        self.last_quit_time = 0.0
        self.current_agent_id = "main"  # Track which agent thread is being viewed

        # Conditional logging setup
        if self.debug_mode:
            logging.basicConfig(
                level=logging.DEBUG, filename="debug_tui.log", filemode="w"
            )
        else:
            # Configure a NullHandler to suppress all logs when not debugging
            # This prevents unwanted log files (like reactor.log) and console output
            logging.basicConfig(
                level=logging.CRITICAL, handlers=[logging.NullHandler()]
            )
        self.logger = logging.getLogger(__name__)

    def action_request_quit(self) -> None:
        """Handle quit request with double-press confirmation"""
        current_time = time.time()
        if current_time - self.last_quit_time < 2.0:
            self.exit()
        else:
            self.last_quit_time = current_time
            self.notify(
                "Press Ctrl+C again to quit", title="Quit", severity="information"
            )

    def copy_to_clipboard(self, text: str) -> None:
        """Override clipboard copy to use pyperclip"""
        try:
            import pyperclip

            pyperclip.copy(text)
            self.logger.info("Copied to clipboard via pyperclip")
        except Exception as e:
            self.logger.warning(f"Pyperclip copy failed: {e}")
            # Fallback to Textual's default (OSC 52)
            super().copy_to_clipboard(text)

    def compose(self) -> ComposeResult:
        """Create the Cyberpunk IDE layout"""
        yield Header()

        # Main Gradient/Neon Layout
        with Container(id="main-layout"):
            # Col 1: Files
            with Vertical(id="col-files"):
                yield Static("Project Structure", classes="panel-header")
                yield FileExplorer("./", id="file-explorer")
                yield ActiveAgents(id="active-agents")

            # Col 2: Agent
            with Vertical(id="col-agent"):
                yield Static(
                    "ReACTOR AGENT", classes="panel-header panel-header-purple"
                )
                yield AgentDashboard(id="agent-dashboard")

            # Col 3: Context
            with Vertical(id="col-context"):
                yield Static("TODO TASKS", classes="panel-header")
                yield TODOPanel(id="todo-panel")
                yield Static("LIVE OUTPUT", classes="panel-header")
                yield InteractiveShellPanel(classes="-hidden", id="live-execution")

        # Footer
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Initialize"""
        self.logger.info("TUI Mounted")

        # Register callback for real-time agent streaming
        from src.agents.manager import AgentManager

        manager = AgentManager()
        manager.set_tui_callback(self.on_agent_message)

        # Register callback for main thread streaming
        self.bridge.set_message_callback(self.on_agent_message)

        # Fresh Session: Clear Todo State
        try:
            from src.tools.todo_tools import reset_todos

            reset_todos()
            self.logger.info("Cleared session todos")
        except Exception as e:
            self.logger.error(f"Failed to reset todos: {e}")

        # Clear Live Log
        import tempfile

        live_log = Path(tempfile.gettempdir()) / "reactor_live_output.log"
        if live_log.exists():
            try:
                live_log.unlink()
            except:
                pass

    def action_toggle_sidebar(self) -> None:
        """Show/Hide Sidebar"""
        self.show_sidebar = not self.show_sidebar
        sidebar = self.query_one("#col-files")
        agent = self.query_one("#col-agent")

        if self.show_sidebar:
            sidebar.remove_class("-hidden")
            # Restore margins if both panels visible, or just remove left margin if context hidden
            if self.show_context:
                agent.styles.margin = (0, 1, 0, 0)
            else:
                agent.styles.margin = (0, 0, 0, 0)
        else:
            sidebar.add_class("-hidden")
            # Remove left spacing, keep or remove right margin based on context visibility
            if self.show_context:
                agent.styles.margin = (0, 1, 0, 0)
            else:
                agent.styles.margin = (0, 0, 0, 0)

    def action_toggle_context(self) -> None:
        """Show/Hide Context Panel"""
        self.show_context = not self.show_context
        context = self.query_one("#col-context")
        agent = self.query_one("#col-agent")

        if self.show_context:
            context.remove_class("-hidden")
            agent.styles.margin = (0, 1, 0, 0)  # Restore right margin
        else:
            context.add_class("-hidden")
            agent.styles.margin = (0, 0, 0, 0)  # Remove right margin for expansion

    def action_fuzzy_find(self) -> None:
        """Open Fuzzy Finder"""
        self.push_screen(FuzzyFinder())

    def action_command_palette(self) -> None:
        """Open Command Palette"""
        self.push_screen(CommandPalette())

    def action_cancel_agent(self) -> None:
        """Cancel running agent execution"""
        if (
            hasattr(self, "agent_worker")
            and self.agent_worker
            and self.agent_worker.is_running
        ):
            self.agent_worker.cancel()
            dashboard = self.query_one(AgentDashboard)
            dashboard.query_one("#log-viewer").add_log(
                "⚠️ Agent execution cancelled by user", "warning"
            )
            self.query_one(StatusBar).agent_state = "idle"
            dashboard.query_one(StateIndicator).state = "complete"
            # LiveExecutionPanel removed
        pass

    def action_clear_logs(self) -> None:
        """Clear the agent log viewer"""
        log_viewer = self.query_one(AgentDashboard).query_one("#log-viewer")
        log_viewer.clear()
        log_viewer.add_log("Logs cleared.", "info")

    def on_fuzzy_finder_selected(self, event: FuzzyFinder.Selected) -> None:
        """Handle file selection from fuzzy finder"""
        path = event.path
        if path.is_file():
            # Load file in CodeViewer
            code_viewer = self.query_one(CodeViewer)
            code_viewer.load_file(path)

            # Switch to Code tab
            self.logger.info(f"Opened file via fuzzy finder: {path}")

    def on_command_palette_selected(self, event: CommandPalette.Selected) -> None:
        """Handle command selection from command palette"""
        action_name = f"action_{event.action}"
        if hasattr(self, action_name):
            getattr(self, action_name)()
        elif event.action == "quit":
            self.exit()
        else:
            self.logger.warning(f"Unknown command palette action: {event.action}")

    # --- File Reference Modal Handlers ---
    # NOTE: Disabled in favor of Tab-based autocomplete
    # The ChatInput widget now handles @ file autocomplete via Tab key

    # def on_input_changed(self, event: Input.Changed) -> None:
    #     """Detect @ and open file reference modal"""
    #     if event.input.id == "agent-input" and event.value.endswith("@"):
    #         self.push_screen(FileReferenceModal())

    def on_file_reference_modal_file_selected(
        self, message: FileReferenceModal.FileSelected
    ) -> None:
        """Insert selected file path into input"""
        agent_input = self.query_one("#agent-input", Input)
        current = agent_input.value
        # Replace trailing @ with @filepath
        agent_input.value = current[:-1] + f"@{message.path} "
        agent_input.focus()

    # --- Agent Bridge Handlers ---

    async def _handle_slash_command(self, command: str) -> None:
        """Handle slash commands like /clear, /help, /compact, /agents, /skills, /running"""
        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")

        # Try agent-related commands first (delegated to bridge)
        agent_response = await self.bridge.handle_slash_command(command)
        if agent_response:
            # Check for modal triggers
            if agent_response.startswith("MODAL:"):
                await self._handle_modal_command(agent_response, log_viewer)
                return

            # Bridge handled it - display the response
            log_viewer.add_log(agent_response, "info")
            return

        # Handle TUI-specific commands
        if command == "/clear":
            # Clear the log viewer by removing all children
            for child in log_viewer.query("*"):
                child.remove()
            log_viewer.add_log("🧹 Conversation cleared", "info")

            # Reset execution results
            self.execution_results = []

            # Clear conversation in bridge (reset agent state)
            if hasattr(self.bridge, "reset_conversation"):
                self.bridge.reset_conversation()

        elif command == "/compact":
            # Compact current conversation
            log_viewer.add_log("🗜️ Compacting conversation...", "info")
            self.query_one(StatusBar).agent_state = "compacting"

            # Trigger compaction via bridge
            import asyncio

            asyncio.create_task(self._compact_conversation_async(log_viewer))

        elif command == "/help":
            help_text = """**Available Commands:**

**General:**
- `/clear` - Clear conversation history
- `/compact` - Summarize and compact conversation
- `/help` - Show this help message
- `@filename` - Reference a file in your message

**Agents & Skills:**
- `/agents` or `/agent` - List available agents
- `/skills` or `/skill` - List available skills
- `/running` - Show running agent instances
- `/result <agent-id>` - Get specific agent output

**Agent Management:**
- `/new-agent` - Create a new agent
- `/edit-agent <name>` - Edit an agent
- `/view-agent <name>` - View agent details
- `/delete-agent <name>` - Delete an agent

**Tips:**
- Press **Tab** to autocomplete `/commands` and `@file` paths
- Press Tab multiple times to cycle through matches
- Type `/` and press Tab to see all commands
- Type `@` and press Tab to see available files"""
            log_viewer.add_log(help_text, "info")
        else:
            log_viewer.add_log(
                f"⚠️ Unknown command: {command}. Type /help for available commands.",
                "warning",
            )

    async def _handle_modal_command(self, modal_command: str, log_viewer) -> None:
        """Handle modal-triggering commands"""
        from src.tui.screens.agent_editor_modal import (
            AgentEditorModal,
            AgentDetailModal,
        )

        if modal_command == "MODAL:new-agent":
            # Open agent creation modal
            result = await self.push_screen_wait(AgentEditorModal())
            if result:
                log_viewer.add_log(
                    f"✅ Agent '{result['name']}' {result['action']} successfully\nFile: `{result['file']}`",
                    "info",
                )

        elif modal_command.startswith("MODAL:edit-agent:"):
            agent_name = modal_command.split(":", 2)[2]
            # Open agent editor in edit mode
            result = await self.push_screen_wait(
                AgentEditorModal(agent_name=agent_name, edit_mode=True)
            )
            if result:
                log_viewer.add_log(
                    f"✅ Agent '{result['name']}' {result['action']} successfully",
                    "info",
                )

        elif modal_command.startswith("MODAL:view-agent:"):
            agent_name = modal_command.split(":", 2)[2]
            # Open agent detail modal
            result = await self.push_screen_wait(
                AgentDetailModal(agent_name=agent_name)
            )
            if result and result.get("action") == "edit":
                # User clicked Edit button - open editor
                edit_result = await self.push_screen_wait(
                    AgentEditorModal(agent_name=result["agent_name"], edit_mode=True)
                )
                if edit_result:
                    log_viewer.add_log(
                        f"✅ Agent '{edit_result['name']}' {edit_result['action']} successfully",
                        "info",
                    )

    @on(DirectoryTree.FileSelected)
    async def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection from FileExplorer"""
        self.logger.info(f"App received file selection: {event.path}")
        event.stop()
        filepath = str(event.path)

        # Determine language for syntax highlighting
        try:
            # Simple check for binary or too large?
            # Textual's DirectoryTree doesn't handle reading, just paths.
            # We'll try to read it.
            if event.path.stat().st_size > 1_000_000:  # 1MB limit
                self.query_one(AgentDashboard).query_one("#log-viewer").add_log(
                    f"⚠️ File too large to open: {event.path.name}", "warning"
                )
                return

            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Guess language
            ext = event.path.suffix.lower()
            lang_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".json": "json",
                ".md": "markdown",
                ".css": "css",
                ".html": "html",
                ".sh": "bash",
                ".yaml": "yaml",
                ".yml": "yaml",
            }
            language = lang_map.get(ext, "text")

            # Show in CodeViewer (Disabled)
            # code_viewer = self.query_one("#code-viewer")
            # code_viewer.show_file(event.path.name, content, language)

            # Log action
            self.logger.info(f"File selected: {event.path.name} (CodeViewer disabled)")
            self.query_one(AgentDashboard).query_one("#log-viewer").add_log(
                f"📂 Selected: {event.path.name}", "info"
            )

        except UnicodeDecodeError:
            self.query_one(AgentDashboard).query_one("#log-viewer").add_log(
                f"⚠️ Cannot open binary file: {event.path.name}", "warning"
            )
        except Exception as e:
            self.logger.error(f"Failed to open file {filepath}: {e}")
            self.query_one(AgentDashboard).query_one("#log-viewer").add_log(
                f"❌ Error opening file: {e}", "error"
            )

    async def on_chat_input_submitted(self, event: ChatInput.Submitted) -> None:
        """Handle input from AgentDashboard"""
        # ChatInput clears itself on submit, so we just processing the value
        command = event.value.strip()
        if not command:
            return

        # Handle slash commands (now async)
        if command.startswith("/"):
            await self._handle_slash_command(command)
            return

        # Extract @ file references
        import re

        file_refs = re.findall(r"@([^\s]+)", command)

        # If file references exist, prepend instruction to read them first
        if file_refs:
            files_str = ", ".join([f'"{ref}"' for ref in file_refs])
            command = f"Before proceeding, use read_file_content tool to read these files: {files_str}. Then: {command}"

        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")

        # Reset UI elements for new run
        self.execution_results = []

        # Prepare Live Execution Panel - Reset if needed
        # InteractiveShellPanel handles its own state on start_monitoring
        pass

        # Input cleared by widget action

        # Show user message (original, before modification)
        log_viewer.add_log(f"💬 You: {event.value.strip()}", "info")
        self.query_one(StatusBar).agent_state = "thinking"
        dashboard.query_one(StateIndicator).state = "thinking"

        # Route based on current agent
        if self.current_agent_id == "main":
            # Send to main agent via bridge
            execution_mode = self.query_one(AgentDashboard).execution_mode
            self.agent_worker = self.run_worker(
                self.bridge.process_request(command, execution_mode), exclusive=True
            )
        else:
            # Send to sub-agent via AgentManager
            from src.tools.agent_tools import get_agent_manager

            manager = get_agent_manager()
            self.agent_worker = self.run_worker(
                manager.send_message(self.current_agent_id, command), exclusive=True
            )

    async def on_interactive_shell_panel_shell_input_submitted(
        self, event: InteractiveShellPanel.ShellInputSubmitted
    ) -> None:
        """Handle input from interactive shell panel"""
        session_id = event.session_id
        value = event.value
        
        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")
        
        from src.tools.shell_tools import send_shell_input
        
        # Execute the tool
        try:
             # Append newline as usually expected in terminals
             await send_shell_input.ainvoke({"session_id": session_id, "input_text": value + "\n", "wait_ms": 500})
        except Exception as e:
             self.logger.error(f"Failed to send input: {e}")
             log_viewer.add_log(f"❌ Failed to send input: {e}", "error")

    async def on_agent_message(self, agent_id: str, event_type: str, data) -> None:
        """Unified event handler for all agent events with enhanced feedback"""
        # Only update if we're currently viewing this agent
        if agent_id != self.current_agent_id:
            return

        try:
            dashboard = self.query_one(AgentDashboard)
            log_viewer = dashboard.query_one("#log-viewer")

            # Handle message events (thinking/agent nodes)
            if event_type in ["thinking", "agent"]:
                self.query_one(StatusBar).agent_state = "thinking"
                content = data.content if hasattr(data, "content") else str(data)
                log_type = "thought" if event_type == "thinking" else "agent"
                if content and content.strip():
                    log_viewer.add_log(content, log_type)

            # Handle tool_call events
            elif event_type == "tool_call":
                self.query_one(StatusBar).agent_state = "executing"
                tool_name = data["tool_name"]
                args = data["args"]

                if tool_name == "execute_shell_command":
                    cmd = args.get("command", "unknown")
                    log_viewer.add_log(f"🛠️ Executing: `{cmd}`", "info")
                    try:
                        import tempfile
                        from pathlib import Path
                        log_path = str(Path(tempfile.gettempdir()) / "reactor_live_output.log")
                        self.query_one(InteractiveShellPanel).start_monitoring("CMD_EXEC", log_path)
                    except Exception as e:
                        self.logger.error(f"Failed to start live monitoring: {e}")
                
                elif tool_name == "search_in_files":
                    pattern = args.get("pattern", "unknown")
                    directory = args.get("directory", ".")
                    log_viewer.add_log(f"🔍 Searching: \"{pattern}\" in `{directory}`", "info")
                
                elif tool_name == "search_web":
                    query = args.get("query", "unknown")
                    log_viewer.add_log(f"🌐 Web Search: \"{query}\"", "info")
                
                elif tool_name == "read_url_content":
                    url = args.get("url", "unknown")
                    log_viewer.add_log(f"🔗 Reading: {url}", "info")
                
                elif tool_name == "spawn_agent":
                    agent_name = args.get("name", "unknown")
                    task = args.get("task", "unknown")
                    log_viewer.add_log(f"🤖 Spawning Agent: **{agent_name}**\nTask: {task}", "info")

                elif tool_name == "write_file":
                    fpath = args.get("target_file", "unknown")
                    mode = args.get("mode", "create")
                    basename = fpath.split("/")[-1]
                    if mode == "write":
                       log_viewer.add_log(f"⚠️ Overwriting File: `{basename}`", "warning")
                    else:
                       log_viewer.add_log(f"📝 Writing File: `{basename}`", "info")

                elif tool_name in ["modify_file", "read_file_content"]:
                    fpath = (
                        args.get("target_file") or args.get("file_path") or "unknown"
                    )
                    basename = fpath.split("/")[-1] if fpath else "unknown"
                    log_viewer.add_log(f"🛠️ File Op ({tool_name}): `{basename}`", "info")
                
                else:
                    log_viewer.add_log(f"🛠️ Using tool: {tool_name}", "info")

            # Handle tool_result events
            elif event_type == "tool_result":
                tool_name = data["tool_name"]
                result = data["result"]

                # Check for generic error in result (common pattern in tool implementations)
                is_error = isinstance(result, dict) and ("error" in result)
                if is_error:
                    error_msg = result.get("error", "Unknown error")
                    if (
                        tool_name != "execute_shell_command"
                    ):  # Shell command handles errors differently (stderr)
                        log_viewer.add_log(
                            f"❌ Tool '{tool_name}' failed: {error_msg}", "error"
                        )

                if tool_name == "execute_shell_command" and isinstance(result, dict):
                    exec_result = ExecutionResult(
                        command=result.get("command", "[Unknown]"),
                        success=result.get("success", False),
                        stdout=str(result.get("stdout", "")),
                        stderr=str(result.get("stderr", "")),
                        exit_code=result.get("exit_code", 0),
                        duration_ms=result.get("duration_ms", 0.0),
                    )

                    try:
                        self.execution_results.append(exec_result)
                    except Exception as e:
                        self.logger.error(f"Failed to update results: {e}")
                
                elif tool_name == "run_interactive_command" and not is_error:
                    session_id = result.get("session_id")
                    log_file = result.get("log_file")
                    if session_id and log_file:
                        try:
                            self.query_one(InteractiveShellPanel).start_monitoring(session_id, log_file)
                        except Exception as e:
                            self.logger.error(f"Failed to attach panel: {e}")

                elif tool_name == "terminate_shell_session" and not is_error:
                    try:
                        self.query_one(InteractiveShellPanel).stop_monitoring()
                    except Exception as e:
                         self.logger.error(f"Failed to stop monitoring: {e}")

                elif tool_name in [
                    "create_todo",
                    "complete_todo",
                    "update_todo",
                    "list_todos",
                ]:
                    try:
                        from src.tools.todo_tools import get_todos_for_ui
                        todos = get_todos_for_ui()
                        self.query_one(TODOPanel).update_todos(todos)
                        if not is_error:
                            log_viewer.add_log(f"✅ Todo updated: {tool_name}", "info")
                    except Exception as e:
                        self.logger.error(f"Failed to update TODOPanel: {e}")

                # --- Search Feedback ---
                elif tool_name == "search_in_files" and not is_error:
                    matches = result.get("matches_found", 0)
                    files = result.get("files_searched", 0)
                    query = result.get("pattern", "unknown")
                    if matches == 0:
                         log_viewer.add_log(f"🔍 No matches found for \"{query}\" (scanned {files} files)", "warning")
                    else:
                         log_viewer.add_log(f"✅ Found {matches} matches for \"{query}\"", "info")

                elif tool_name == "read_url_content" and not is_error:
                    title = result.get("title", "No Title")
                    url = result.get("url", "unknown")
                    log_viewer.add_log(f"📄 Read: [{title}]({url})", "info")

                elif tool_name == "spawn_agent" and not is_error:
                    agent_id = result.get("agent_id", "unknown")
                    status = result.get("status", "unknown")
                    log_viewer.add_log(f"✅ Agent spawned ({status}). ID: `{agent_id}`", "info")

                # --- File Operations Feedback ---
                elif tool_name == "write_file" and not is_error:
                    path = result.get("file_path", "unknown")
                    basename = path.split("/")[-1] if path else "unknown"
                    lines = result.get("lines_written", "?")
                    op = result.get("operation", "wrote")

                    diff = result.get("diff", {})
                    added = diff.get("added", 0)
                    removed = diff.get("removed", 0)
                    diff_str = ""
                    if added > 0 or removed > 0:
                        diff_str = f" (+{added} -{removed})"

                    log_viewer.add_log(
                        f"📝 {op.capitalize()}: {basename} ({lines} lines written){diff_str}",
                        "info",
                    )
                    
                    if "diff_text" in diff and diff["diff_text"]:
                        log_viewer.add_log(f"```diff\n{diff['diff_text']}\n```", "info")

                elif tool_name == "modify_file" and not is_error:
                    path = result.get("file_path", "unknown")
                    basename = path.split("/")[-1] if path else "unknown"
                    replacements = result.get("replacements_made", 0)
                    diff = result.get("diff", {})
                    added = diff.get("added", 0)
                    removed = diff.get("removed", 0)

                    diff_str = ""
                    if added > 0 or removed > 0:
                        diff_str = f" (+{added} -{removed})"

                    log_viewer.add_log(
                        f"✏️ Modified: {basename} ({replacements} changes){diff_str}",
                        "info",
                    )

                    if "diff_text" in diff and diff["diff_text"]:
                        log_viewer.add_log(f"```diff\n{diff['diff_text']}\n```", "info")

                elif (
                    tool_name == "edit_file" or tool_name == "apply_multiple_edits"
                ) and not is_error:
                    # Added legacy check just in case
                    path = result.get("file_path", "unknown")
                    basename = path.split("/")[-1] if path else "unknown"
                    successful = result.get("successful_edits", 0)
                    total = result.get("total_edits", 0)

                    diff = result.get("diff", {})
                    added = diff.get("added", 0)
                    removed = diff.get("removed", 0)

                    diff_str = ""
                    if added > 0 or removed > 0:
                        diff_str = f" (+{added} -{removed})"

                    log_viewer.add_log(
                        f"🔨 Applied edits: {basename} ({successful}/{total} success){diff_str}",
                        "info",
                    )

                    if "diff_text" in diff and diff["diff_text"]:
                        log_viewer.add_log(f"```diff\n{diff['diff_text']}\n```", "info")

                elif tool_name == "read_file_content" and not is_error:
                    path = result.get("file_path", "unknown")
                    basename = path.split("/")[-1] if path else "unknown"
                    lines = result.get("lines_returned", 0)
                    total = result.get("total_lines", 0)
                    if lines < total:
                        log_viewer.add_log(
                            f"📄 Read {lines}/{total} lines from {basename}", "info"
                        )
                    else:
                        log_viewer.add_log(
                            f"📄 Read {lines} lines from {basename}", "info"
                        )

                elif not is_error and tool_name not in [
                    "execute_shell_command",
                    "create_todo",
                    "complete_todo",
                    "update_todo",
                    "list_todos",
                    "write_file",
                    "modify_file",
                    "apply_multiple_edits",
                    "read_file_content",
                    "search_in_files",
                    "read_url_content",
                    "spawn_agent",
                    "search_web"
                ]:
                    # Generic success for other tools
                    log_viewer.add_log(f"✅ Tool '{tool_name}' completed", "info")

                # After any tool result, if the agent is not yet complete, go back to thinking
                if self.query_one(StatusBar).agent_state not in [
                    "complete",
                    "error",
                    "idle",
                ]:
                    self.query_one(StatusBar).agent_state = "thinking"

        except Exception as e:
            self.logger.error(f"Error handling agent event: {e}")

    async def on_active_agents_agent_selected(
        self, event: ActiveAgents.AgentSelected
    ) -> None:
        """Handle agent selection from sidebar"""
        agent_id = event.agent_id
        self.current_agent_id = agent_id  # Track which agent we're viewing
        dashboard = self.query_one(AgentDashboard)

        self.logger.info(f"Switching view to agent thread: {agent_id}")

        if agent_id == "main":
            # Load main thread
            if hasattr(self.bridge, "state") and "messages" in self.bridge.state:
                await dashboard.load_history(self.bridge.state["messages"])
                dashboard.query_one(StateIndicator).title = "Main Thread"
        else:
            # Load parallel agent thread
            from src.agents.manager import AgentManager

            manager = AgentManager()
            history = await manager.get_agent_history(agent_id)
            if history:
                await dashboard.load_history(history)
                # Update header to show we are viewing an agent
                agent = manager.get_agent(agent_id)
                dashboard.query_one(StateIndicator).title = f"Agent: {agent.agent_name}"
            else:
                dashboard.query_one("#log-viewer").add_log(
                    "⚠️ Unable to load agent history", "warning"
                )

    def on_directory_tree_file_selected(self, event: FileExplorer.FileSelected) -> None:
        """Handle file selection from sidebar"""
        path = event.path
        if path.is_file():
            # Show file in diff viewer (future: could show original content)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                # For now, just log the file open
                # DiffViewer will show diffs when files are modified
                self.logger.info(f"Opened file: {path}")
            except Exception as e:
                self.logger.error(f"Error opening file {path}: {e}")

    def on_agent_dashboard_execution_mode_toggled(
        self, message: "AgentDashboard.ExecutionModeToggled"
    ) -> None:
        """Handle execution mode toggle from dashboard"""
        self.logger.info(f"Execution mode changed to: {message.mode}")
        # Update status bar
        self.query_one(StatusBar).execution_mode = message.mode
        # Update TUI state
        self.state.execution_mode = message.mode

    async def on_agent_start(self) -> None:
        self.query_one(StatusBar).agent_state = "thinking"

    async def on_node_update(self, node_name: str, node_output: dict) -> None:
        self.logger.info(f"Node Update: {node_name}, data: {list(node_output.keys())}")
        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")

        # Log basic node info - DEPRECATED: Handled by AgentBridge specialized methods
        # if node_name not in ["execute_command", "summarize"]:
        #     pass

        # Update Execution Plan
        # Update LiveExecutionPanel and ResultsPanel after a command
        if (
            node_name == "execute_command"
            and "results" in node_output
            and node_output["results"]
        ):
            last_result: ExecutionResult = node_output["results"][-1]

            # Update live panel with latest result
            # InteractiveShellPanel handles its own state
            pass
            dashboard.query_one(StateIndicator).state = "executing"

            self.execution_results.append(last_result)

    async def _compact_conversation_async(self, log_viewer):
        """Async method to compact conversation"""
        try:
            from src.utils.conversation_compactor import compact_conversation

            # Get current messages from bridge state
            if hasattr(self.bridge, "state") and "messages" in self.bridge.state:
                messages = self.bridge.state["messages"]

                # Perform compaction
                compacted = await compact_conversation(messages, target_tokens=10000)

                # Update bridge state with compacted messages
                self.bridge.state["messages"] = compacted

                log_viewer.add_log("✅ Conversation compacted successfully", "info")
                log_viewer.add_log(
                    "📝 Summary created, recent context preserved", "info"
                )
            else:
                log_viewer.add_log("⚠️ No conversation to compact", "info")
        except Exception as e:
            log_viewer.add_log(f"❌ Error compacting: {str(e)}", "error")
            self.logger.error(f"Compaction error: {e}")

    async def on_agent_complete(self, state: dict) -> None:
        self.query_one(StatusBar).agent_state = "complete"
        dashboard = self.query_one(AgentDashboard)
        dashboard.query_one(StateIndicator).state = "complete"
        # self.query_one(InteractiveShellPanel).stop_monitoring() # It might already be stopped
        pass

        # Only show a simple completion marker, since the final message was already streamed/logged by the bridge
        dashboard.query_one("#log-viewer").add_log("🏁 **Session Finished**", "info")

    async def on_agent_error(self, error: str) -> None:
        self.query_one(StatusBar).agent_state = "error"
        dashboard = self.query_one(AgentDashboard)
        dashboard.query_one(StateIndicator).state = "error"
        dashboard.query_one("#log-viewer").add_log(f"Error: {error}", "error")
        # self.query_one(InteractiveShellPanel).stop_monitoring()
        pass


def run_tui(debug_mode: bool = False):
    app = ShellAgentTUI(debug_mode=debug_mode)
    app.run()


if __name__ == "__main__":
    run_tui()
