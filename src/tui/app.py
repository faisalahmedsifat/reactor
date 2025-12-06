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
from src.tui.widgets.agent_ui import (
    StateIndicator, 
    LiveExecutionPanel, 
    ExecutionPlanDisplay,
    ResultsPanel
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
    ]
    
    # Global Reactive State
    show_sidebar = reactive(True)
    show_context = reactive(True)
    
    def __init__(self):
        super().__init__()
        self.bridge = AgentBridge(self)
        self.state = TUIState()
        self.execution_results: List[ExecutionResult] = []
        
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
                yield CodeViewer(id="code-viewer")
                yield Static("LIVE OUTPUT", classes="panel-header")
                yield LiveExecutionPanel(id="live-execution")
                yield Static("EXECUTION PLAN", classes="panel-header")
                yield ExecutionPlanDisplay(id="plan-display")
                yield ResultsPanel(id="results-panel")
        
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

    # --- Agent Bridge Handlers ---
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input from AgentDashboard"""
        if event.input.id == "agent-input":
            command = event.value.strip()
            if not command:
                return
                
            dashboard = self.query_one(AgentDashboard)
            log_viewer = dashboard.query_one("#log-viewer")
            
            # Reset UI elements for new run
            self.execution_results = []
            self.query_one(ExecutionPlanDisplay).update_plan(None)
            self.query_one(ResultsPanel).update_results([])
            
            # Prepare Live Execution Panel
            live_panel = self.query_one(LiveExecutionPanel)
            live_panel.clear()
            live_panel.add_class("-visible")

            # Clear input
            event.input.value = ""
            
            # Show user message
            log_viewer.add_log(f"💬 You: {command}", "info")
            self.query_one(StatusBar).agent_state = "thinking"
            dashboard.query_one(StateIndicator).state = "thinking"
            
            # Send to bridge with execution mode
            execution_mode = self.query_one(AgentDashboard).execution_mode
            self.run_worker(self.bridge.process_request(command, execution_mode), exclusive=True)

    def on_directory_tree_file_selected(self, event: FileExplorer.FileSelected) -> None:
        """Handle file selection from sidebar"""
        path = event.path
        if path.is_file():
            # Load file in CodeViewer
            code_viewer = self.query_one(CodeViewer)
            code_viewer.load_file(path)
            
            logger.info(f"Opened file: {path}")
    
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
        
        # Log basic node info (Filter out execution details from chat)
        if node_name not in ["execute_command", "summarize"]:
            # Mark intermediate outputs as thoughts
            if node_name in ["agent", "tools"]:
                log_viewer.add_log(f"[{node_name}]", "agent", is_thought=True)
                if "messages" in node_output and node_output["messages"]:
                    last_msg = node_output["messages"][-1]
                    # Handle different message types
                    if hasattr(last_msg, 'content') and last_msg.content:
                        # Only show as thought if it contains tool calls
                        if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                            tool_info = f"Using tools: {', '.join([tc['name'] for tc in last_msg.tool_calls])}"
                            log_viewer.add_log(tool_info, "info", is_thought=True)
                        elif not hasattr(last_msg, 'tool_calls'):
                            # This is the final answer
                            log_viewer.add_log(str(last_msg.content), "info", is_thought=False)
                    elif isinstance(last_msg, str):
                        log_viewer.add_log(last_msg, "info", is_thought=False)
            else:
                log_viewer.add_log(f"[{node_name}]", "agent")
                if "messages" in node_output and node_output["messages"]:
                    last_msg = node_output["messages"][-1]
                    if hasattr(last_msg, 'content') and last_msg.content:
                        log_viewer.add_log(str(last_msg.content), "info")
                    elif isinstance(last_msg, str):
                        log_viewer.add_log(last_msg, "info")

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
            
            # Update cumulative results panel
            self.execution_results.append(last_result)
            self.query_one(ResultsPanel).update_results(self.execution_results)


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
