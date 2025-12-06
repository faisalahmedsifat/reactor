"""
Powerhouse TUI Application for Reactive Shell Agent
"""
import logging
from typing import List
from textual.app import App, ComposeResult
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
    FuzzyFinder,
    CommandPalette
)
from src.tui.widgets.file_reference_modal import FileReferenceModal
from src.tui.widgets.diff_viewer import DiffViewer
from src.tui.widgets.todo_panel import TODOPanel
from src.tui.widgets.agent_ui import (
    StateIndicator, 
    LiveExecutionPanel, 
    ExecutionPlanDisplay
)
from src.tui.bridge import AgentBridge
from src.models import ExecutionResult, ExecutionPlan

# Reuse the StatusBar from the old widgets if possible, or redefine it here/in widgets
# I'll quickly redefine a compatible StatusBar for the footer
from textual.widgets import Static
class StatusBar(Static):
    """Bottom status bar"""
    agent_state = reactive("idle")
    status = reactive("Ready")
    execution_mode = reactive("sequential")
    
    def render(self):
        mode_display = "⏩ Sequential" if self.execution_mode == "sequential" else "⚡ Parallel"
        return f" {self.status} | State: {self.agent_state} | Mode: {mode_display} "

# Setup logging
logging.basicConfig(level=logging.DEBUG, filename='debug_tui.log', filemode='w')
logger = logging.getLogger(__name__)

class ShellAgentTUI(App):
    """Powerhouse TUI for Reactive Shell Agent"""
    
    CSS_PATH = "styles.tcss"
    TITLE = "🤖 Reactive Shell Agent IDE"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+backslash", "toggle_context", "Context Panel"),
        Binding("ctrl+p", "fuzzy_find", "Find File"),
        Binding("ctrl+shift+p", "command_palette", "Command Palette"),
        Binding("escape", "cancel_agent", "Cancel Agent"),
    ]
    
    # Global Reactive State
    show_sidebar = reactive(True)
    show_context = reactive(True)
    
    def __init__(self):
        super().__init__()
        self.bridge = AgentBridge(self)
        self.state = TUIState()
        self.execution_results: List[ExecutionResult] = []
        self.agent_worker = None  # Track running agent worker
        
    def compose(self) -> ComposeResult:
        """Create the Cyberpunk IDE layout"""
        yield Header()
        
        # Main Gradient/Neon Layout
        with Container(id="main-layout"):
            # Col 1: Files
            with Vertical(id="col-files"):
                yield Static("SESSION HISTORY", classes="panel-header")
                yield FileExplorer("./", id="file-explorer")
            
            # Col 2: Agent
            with Vertical(id="col-agent"):
                yield Static("CYBERPUNK AGENT", classes="panel-header panel-header-purple")
                yield AgentDashboard(id="agent-dashboard")

            # Col 3: Context
            with Vertical(id="col-context"):
                yield Static("CONTEXT / DRAFT", classes="panel-header")
                with Container(id="right-panel"):
                    yield DiffViewer(id="diff-viewer")
                yield Static("LIVE OUTPUT", classes="panel-header")
                yield LiveExecutionPanel(id="live-execution")
                yield Static("EXECUTION PLAN", classes="panel-header")
                yield ExecutionPlanDisplay(id="execution-plan")
                yield Static("TODO TASKS", classes="panel-header")
                yield TODOPanel(id="todo-panel")
        
        # Footer
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Initialize"""
        logger.info("TUI Mounted")
        self.query_one(AgentDashboard).query_one("#log-viewer").add_log("Welcome to the Powerhouse TUI!", "info")

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
        if hasattr(self, 'agent_worker') and self.agent_worker and self.agent_worker.is_running:
            self.agent_worker.cancel()
            dashboard = self.query_one(AgentDashboard)
            dashboard.query_one("#log-viewer").add_log("⚠️ Agent execution cancelled by user", "warning")
            self.query_one(StatusBar).agent_state = "idle"
            dashboard.query_one(StateIndicator).state = "complete"
            self.query_one(LiveExecutionPanel).remove_class("-visible")

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
            logger.info(f"Opened file via fuzzy finder: {path}")

    def on_command_palette_selected(self, event: CommandPalette.Selected) -> None:
        """Handle command selection from command palette"""
        action_name = f"action_{event.action}"
        if hasattr(self, action_name):
            getattr(self, action_name)()
        elif event.action == 'quit':
            self.exit()
        else:
            logger.warning(f"Unknown command palette action: {event.action}")


    # --- File Reference Modal Handlers ---
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Detect @ and open file reference modal"""
        if event.input.id == "agent-input" and event.value.endswith("@"):
            self.push_screen(FileReferenceModal())
    
    def on_file_reference_modal_file_selected(self, message: FileReferenceModal.FileSelected) -> None:
        """Insert selected file path into input"""
        agent_input = self.query_one("#agent-input", Input)
        current = agent_input.value
        # Replace trailing @ with @filepath
        agent_input.value = current[:-1] + f"@{message.path} "
        agent_input.focus()
    
    # --- Agent Bridge Handlers ---
    
    def _handle_slash_command(self, command: str) -> None:
        """Handle slash commands like /clear, /help, /compact"""
        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")
        
        if command == "/clear":
            # Clear the log viewer by removing all children
            for child in log_viewer.query("*"):
                child.remove()
            log_viewer.add_log("🧹 Conversation cleared", "info")
            
            # Reset execution results
            self.execution_results = []
            self.query_one(ExecutionPlanDisplay).update_plan(None)
            
            # Clear conversation in bridge (reset agent state)
            if hasattr(self.bridge, 'reset_conversation'):
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
- `/clear` - Clear conversation history
- `/compact` - Summarize and compact conversation
- `/help` - Show this help message
- `@filename` - Reference a file in your message"""
            log_viewer.add_log(help_text, "info")
        else:
            log_viewer.add_log(f"⚠️ Unknown command: {command}. Type /help for available commands.", "warning")
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input from AgentDashboard"""
        if event.input.id == "agent-input":
            command = event.value.strip()
            if not command:
                return
            
            # Handle slash commands
            if command.startswith("/"):
                self._handle_slash_command(command)
                event.input.value = ""
                return
            
            # Extract @ file references
            import re
            file_refs = re.findall(r'@([^\s]+)', command)
            
            # If file references exist, prepend instruction to read them first
            if file_refs:
                files_str = ", ".join([f'"{ref}"' for ref in file_refs])
                command = f"Before proceeding, use read_file_content tool to read these files: {files_str}. Then: {command}"
                
            dashboard = self.query_one(AgentDashboard)
            log_viewer = dashboard.query_one("#log-viewer")
            
            # Reset UI elements for new run
            self.execution_results = []
            self.query_one(ExecutionPlanDisplay).update_plan(None)
            
            # Prepare Live Execution Panel
            live_panel = self.query_one(LiveExecutionPanel)
            live_panel.clear()
            live_panel.add_class("-visible")

            # Clear input
            event.input.value = ""
            
            # Show user message (original, before modification)
            log_viewer.add_log(f"💬 You: {event.value.strip()}", "info")
            self.query_one(StatusBar).agent_state = "thinking"
            dashboard.query_one(StateIndicator).state = "thinking"
            
            # Send to bridge with execution mode
            execution_mode = self.query_one(AgentDashboard).execution_mode
            self.agent_worker = self.run_worker(self.bridge.process_request(command, execution_mode), exclusive=True)

    def on_directory_tree_file_selected(self, event: FileExplorer.FileSelected) -> None:
        """Handle file selection from sidebar"""
        path = event.path
        if path.is_file():
            # Show file in diff viewer (future: could show original content)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # For now, just log the file open
                # DiffViewer will show diffs when files are modified
                logger.info(f"Opened file: {path}")
            except Exception as e:
                logger.error(f"Error opening file {path}: {e}")
    
    def on_agent_dashboard_execution_mode_toggled(self, message: "AgentDashboard.ExecutionModeToggled") -> None:
        """Handle execution mode toggle from dashboard"""
        logger.info(f"Execution mode changed to: {message.mode}")
        # Update status bar
        self.query_one(StatusBar).execution_mode = message.mode
        # Update TUI state
        self.state.execution_mode = message.mode
    
    async def on_agent_start(self) -> None:
        self.query_one(StatusBar).agent_state = "thinking"
        
    async def on_node_update(self, node_name: str, node_output: dict) -> None:
        logger.info(f"Node Update: {node_name}, data: {list(node_output.keys())}")
        dashboard = self.query_one(AgentDashboard)
        log_viewer = dashboard.query_one("#log-viewer")
        
        # Log basic node info - DEPRECATED: Handled by AgentBridge specialized methods
        # if node_name not in ["execute_command", "summarize"]:
        #     pass 

        # Update Execution Plan
        if "execution_plan" in node_output and node_output["execution_plan"] is not None:
            plan: ExecutionPlan = node_output["execution_plan"]
            self.query_one(ExecutionPlanDisplay).update_plan(plan)

        # Update LiveExecutionPanel and ResultsPanel after a command
        if node_name == "execute_command" and "results" in node_output and node_output["results"]:
            last_result: ExecutionResult = node_output["results"][-1]
            
            # Update live panel with latest result
            self.query_one(LiveExecutionPanel).set_content(last_result)
            dashboard.query_one(StateIndicator).state = "executing"
            
            self.execution_results.append(last_result)



    async def _compact_conversation_async(self, log_viewer):
        """Async method to compact conversation"""
        try:
            from src.utils.conversation_compactor import compact_conversation
            
            # Get current messages from bridge state
            if hasattr(self.bridge, 'state') and 'messages' in self.bridge.state:
                messages = self.bridge.state['messages']
                
                # Perform compaction
                compacted = await compact_conversation(messages, target_tokens=10000)
                
                # Update bridge state with compacted messages
                self.bridge.state['messages'] = compacted
                
                log_viewer.add_log("✅ Conversation compacted successfully", "info")
                log_viewer.add_log("📝 Summary created, recent context preserved", "info")
            else:
                log_viewer.add_log("⚠️ No conversation to compact", "info")
        except Exception as e:
            log_viewer.add_log(f"❌ Error compacting: {str(e)}", "error")
            logger.error(f"Compaction error: {e}")

    async def on_agent_complete(self, state: dict) -> None:
        self.query_one(StatusBar).agent_state = "complete"
        dashboard = self.query_one(AgentDashboard)
        dashboard.query_one(StateIndicator).state = "complete"
        self.query_one(LiveExecutionPanel).remove_class("-visible")

    async def on_agent_error(self, error: str) -> None:
        self.query_one(StatusBar).agent_state = "error"
        dashboard = self.query_one(AgentDashboard)
        dashboard.query_one(StateIndicator).state = "error"
        dashboard.query_one("#log-viewer").add_log(f"Error: {error}", "error")
        self.query_one(LiveExecutionPanel).remove_class("-visible")

def run_tui():
    app = ShellAgentTUI()
    app.run()

if __name__ == "__main__":
    run_tui()
