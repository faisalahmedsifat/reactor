"""
Main TUI Application for Reactive Shell Agent
"""

import os
import asyncio
import logging
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Header, Footer, Input, Button
from textual.binding import Binding
from textual.reactive import reactive
from typing import Optional

from src.tui.widgets import (
    SystemInfoPanel,
    CommandInputPanel,
    ExecutionPlanDisplay,
    LogViewer,
    ApprovalDialog,
    StatusBar,
    ResultsPanel
)
from src.tui.bridge import AgentBridge
from src.state import ShellAgentState

# Setup file logging - ONLY to file, not console (so it doesn't cover TUI)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('debug.log', mode='w')
    ]
)
logger = logging.getLogger(__name__)
logger.info("="*80)
logger.info("TUI Application Starting")
logger.info("="*80)


class ShellAgentTUI(App):
    """Beautiful TUI for Reactive Shell Agent"""
    
    CSS_PATH = "styles.tcss"
    TITLE = "🤖 Reactive Shell Agent"
    
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+l", "clear_logs", "Clear Logs"),
        Binding("ctrl+r", "reset", "Reset"),
    ]
    
    # Reactive state
    show_approval_dialog: reactive[bool] = reactive(False)
    agent_state: reactive[str] = reactive("idle")
    
    def __init__(self):
        super().__init__()
        self.bridge = AgentBridge(self)
        self.approval_callback: Optional[asyncio.Future] = None
        
    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header()
        
        with Container(id="main-container"):
            # Chat area - logs take up most of the space
            with ScrollableContainer(id="chat-area"):
                yield LogViewer(id="log-viewer")
            
            # Input area - sticky at bottom
            with Container(id="input-container"):
                yield Input(
                    placeholder="Enter your command or request...",
                    id="command-input"
                )
            
            # Approval dialog (hidden by default, overlays chat)
            yield ApprovalDialog(id="approval-dialog")
        
        yield StatusBar()
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app starts"""
        logger.info("on_mount called - App is mounting")
        
        # Hide approval dialog initially
        approval_dialog = self.query_one("#approval-dialog", ApprovalDialog)
        approval_dialog.display = False
        logger.info("Approval dialog hidden")
        
        # Focus the input
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()
        logger.info(f"Focused input widget: {input_widget.id}")
        
        # Welcome message
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.add_log("🤖 Reactive Shell Agent", "agent")
        log_viewer.add_log("", "info")
        log_viewer.add_log("I can help you execute shell commands safely.", "info")
        log_viewer.add_log("Just type what you need and I'll analyze, plan, and execute it.", "info")
        log_viewer.add_log("", "info")
        log_viewer.add_log("─" * 60, "info")
        log_viewer.add_log("", "info")
        logger.info("Welcome messages added to log viewer")
        logger.info("on_mount complete - App ready for input")
    

    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission"""
        logger.info(f"on_input_submitted CALLED! Value='{event.value}', ID={event.input.id}")
        
        # Only handle our command input
        if event.input.id != "command-input":
            logger.info(f"Ignoring input from {event.input.id}")
            return
        
        logger.info("This is our command input!")
        
        command = event.value.strip()
        logger.info(f"Stripped command: '{command}'")
        
        if not command:
            logger.warning("Empty command, returning")
            return
        
        # Get log viewer
        log_viewer = self.query_one("#log-viewer", LogViewer)
        
        # Clear input
        event.input.value = ""
        logger.info("Cleared input field")
        
        # Add user message to chat
        log_viewer.add_log("", "info")
        log_viewer.add_log(f"💬 You: {command}", "info")
        log_viewer.add_log("", "info")
        logger.info("Added user request to log viewer")
        
        # Update status
        self.agent_state = "thinking"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "thinking"
        status_bar.status = "Processing..."
        logger.info("Updated status bar to 'thinking'")
        
        logger.info("About to call run_worker...")
        
        try:
            # Process through agent in background task
            worker = self.run_worker(self.bridge.process_request(command), exclusive=True)
            logger.info(f"run_worker returned: {worker}")
            logger.info("Worker started successfully!")
        except Exception as e:
            logger.error(f"Error starting worker: {e}", exc_info=True)
            log_viewer.add_log(f"❌ Error: {e}", "error")
    
    async def on_agent_start(self) -> None:
        """Called when agent starts processing"""
        logger.info("on_agent_start called")
        self.agent_state = "thinking"
        log_viewer = self.query_one("#log-viewer", LogViewer)
        logger.info("Got log viewer")
        log_viewer.add_log("🚀 Agent started processing...", "agent")
        self.screen.refresh()  # Force screen refresh
        logger.info("Added agent start message to log viewer")
    
    async def on_node_update(self, node_name: str, node_output: dict) -> None:
        """Called when agent node produces output"""
        logger.info(f"on_node_update called for node: {node_name}")
        log_viewer = self.query_one("#log-viewer", LogViewer)
        logger.info("Got log viewer in on_node_update")
        
        try:
            # Log node activation (subtle, not intrusive)
            log_viewer.add_log(f"[{node_name.upper()}]", "agent")
            logger.info(f"Added node name to log viewer: [{node_name.upper()}]")
            
            # Show execution plan in chat
            if "execution_plan" in node_output and node_output["execution_plan"]:
                plan = node_output["execution_plan"]
                logger.info(f"Found execution_plan with {len(plan.commands)} commands")
                
                log_viewer.add_log(f"📋 Plan: {plan.overall_strategy}", "success")
                if plan.commands:
                    log_viewer.add_log(f"   Commands: {len(plan.commands)}", "info")
                logger.info("Showed plan in chat")
            
            # Show results in chat
            if "results" in node_output and node_output["results"]:
                logger.info(f"Found {len(node_output['results'])} results")
                last_result = node_output["results"][-1]
                log_viewer.add_result(last_result)
                logger.info("Showed result in chat")
            
            # Show messages (main output)
            if "messages" in node_output and node_output["messages"]:
                logger.info(f"Found {len(node_output['messages'])} messages")
                last_msg = node_output["messages"][-1]
                content = last_msg.content
                logger.info(f"Last message content (first 100 chars): {content[:100]}")
                
                # Show agent response
                if "✅" in content or "Success" in content:
                    log_viewer.add_log(content, "success")
                elif "❌" in content or "Failed" in content:
                    log_viewer.add_log(content, "error")
                elif "⚠️" in content or "warning" in content.lower():
                    log_viewer.add_log(content, "warning")
                else:
                    log_viewer.add_log(content, "info")
                logger.info("Added message to log viewer")
            
            # Add spacing for readability
            log_viewer.add_log("", "info")
            
            # Force screen update
            self.screen.refresh()
            self.refresh(layout=True)
            logger.info(f"on_node_update completed for {node_name}")
        except Exception as e:
            # Log any errors in UI update
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"UI Update Error in on_node_update: {str(e)}")
            logger.error(f"Traceback: {error_details}")
            log_viewer.add_log(f"❌ Error: {str(e)}", "error")
            self.screen.refresh()
    
    async def on_approval_required(self, state: dict) -> None:
        """Called when approval is required"""
        self.agent_state = "waiting"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "waiting"
        status_bar.status = "Waiting for approval..."
        
        # Get current command
        plan = state.get("execution_plan")
        idx = state.get("current_command_index", 0)
        
        if plan and idx < len(plan.commands):
            cmd = plan.commands[idx]
            
            # Show approval dialog
            approval_dialog = self.query_one("#approval-dialog", ApprovalDialog)
            approval_dialog.command = cmd.cmd
            approval_dialog.risk_level = cmd.risk_level
            
            # Extract warnings from messages
            warnings = []
            for msg in state.get("messages", []):
                if "⚠️" in msg.content and "Safety warnings:" in msg.content:
                    warnings_str = msg.content.split("Safety warnings:")[1].strip()
                    warnings = [w.strip() for w in warnings_str.split(",")]
            
            approval_dialog.warnings = warnings
            approval_dialog.display = True
            
            # Add to log
            log_viewer = self.query_one("#log-viewer", LogViewer)
            log_viewer.add_log("\n⏸️  APPROVAL REQUIRED", "warning")
            log_viewer.add_command(cmd.cmd)
            self.screen.refresh()  # Force screen refresh
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "approve-btn":
            await self.handle_approval(True)
        elif event.button.id == "reject-btn":
            await self.handle_approval(False)
    
    async def handle_approval(self, approved: bool) -> None:
        """Handle approval decision"""
        # Hide dialog
        approval_dialog = self.query_one("#approval-dialog", ApprovalDialog)
        approval_dialog.display = False
        
        # Log decision
        log_viewer = self.query_one("#log-viewer", LogViewer)
        if approved:
            log_viewer.add_log("✅ Command approved by user", "success")
            self.agent_state = "executing"
            status_bar = self.query_one(StatusBar)
            status_bar.agent_state = "executing"
            status_bar.status = "Executing command..."
        else:
            log_viewer.add_log("❌ Command rejected by user", "error")
            self.agent_state = "idle"
        
        # Provide decision to agent in background task
        self.run_worker(self.bridge.provide_approval(approved), exclusive=True)
    
    async def on_approval_rejected(self) -> None:
        """Called when user rejects approval"""
        self.agent_state = "idle"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "idle"
        status_bar.status = "Ready"
        
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.add_log("Execution cancelled by user.", "info")
    
    async def on_agent_complete(self, state: dict) -> None:
        """Called when agent completes"""
        self.agent_state = "complete"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "complete"
        status_bar.status = "Ready"
        
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.add_log("\n✅ Agent execution completed!", "success")
        log_viewer.add_log("", "info")
        
        self.screen.refresh()  # Force screen refresh
    
    async def on_agent_error(self, error: str) -> None:
        """Called when agent encounters error"""
        self.agent_state = "error"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "error"
        status_bar.status = "Error occurred"
        
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.add_log(f"\n❌ Error: {error}", "error")
        self.screen.refresh()  # Force screen refresh
    
    def action_clear_logs(self) -> None:
        """Clear log viewer"""
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.clear()
        log_viewer.add_log("📋 Logs cleared", "info")
    
    def action_reset(self) -> None:
        """Reset the application"""
        # Clear logs
        log_viewer = self.query_one("#log-viewer", LogViewer)
        log_viewer.clear()
        
        # Reset status
        self.agent_state = "idle"
        status_bar = self.query_one(StatusBar)
        status_bar.agent_state = "idle"
        status_bar.status = "Ready"
        
        log_viewer.add_log("🔄 Application reset", "info")


def run_tui():
    """Run the TUI application"""
    app = ShellAgentTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
