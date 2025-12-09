from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, RichLog, Label, Input, Tree, Markdown, Button, TextArea
from textual.reactive import reactive
from textual.message import Message
from textual.binding import Binding
from rich.text import Text
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List, Any
from pathlib import Path
import logging

from src.models import ExecutionResult, ExecutionPlan, RiskLevel, Command
from src.tui.widgets.suggestions_list import SuggestionsList


class LogViewer(VerticalScroll):
    """Scrollable log viewer with collapsible thoughts support"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_focus = True
        self.current_activity = []
        self.pending_activity_widget = None

    def add_activity(self, message: str) -> None:
        """Add an activity/tool call to the current execution session"""
        if not message.strip():
            return

        self.current_activity.append(message)

        # Update or create the activity collapsible
        if self.pending_activity_widget:
            # Update existing collapsible
            self.update_activity_widget()
        else:
            # Create new collapsible
            from textual.widgets import Collapsible

            self.pending_activity_widget = Collapsible(
                Static(""),
                title=f"🛠️ Activity ({len(self.current_activity)} steps)",
                collapsed=True,
            )
            self.mount(self.pending_activity_widget)
            self.update_activity_widget()

    def update_activity_widget(self):
        """Update the activity collapsible content"""
        if not self.pending_activity_widget:
            return

        # Build activity content
        activity_text = "\n\n".join(
            [f"**Step {i+1}:** {t}" for i, t in enumerate(self.current_activity)]
        )

        from rich.markdown import Markdown as RichMarkdown

        md = RichMarkdown(activity_text)

        # Update the collapsible's content
        self.pending_activity_widget.title = (
            f"🛠️ Activity ({len(self.current_activity)} steps)"
        )
        # The Collapsible contains a Static widget, update that
        if self.pending_activity_widget.children:
            self.pending_activity_widget.children[0].update(md)

    def finalize_activity(self):
        """Mark current activity session as complete"""
        if not self.current_activity:
            return

        self.current_activity = []
        self.pending_activity_widget = None

    def add_log(
        self, message: str, level: str = "info", is_thought: bool = False
    ) -> None:
        """Add a log message with styling"""
        if not message.strip():
            return

        from rich.markdown import Markdown as RichMarkdown

        # If this is activity/tool output (passed as is_thought by bridge), add to activity section
        if is_thought or message.startswith("["):
            self.add_activity(message)
            return

        # Otherwise, finalize any pending activity and show the message normally
        self.finalize_activity()

        # Cyberpunk Palette
        ACCENT_CYAN = "#00f3ff"  # Agent
        ACCENT_PURPLE = "#bc13fe"  # User
        ACCENT_GOLD = "#ffd700"  # Understanding
        ACCENT_BLUE = "#4169e1"  # Plan
        ACCENT_GREEN = "#32cd32"  # Progress
        BG_TERTIARY = "#11112b"  # Message BG

        border_style = "dim"
        title = None

        # Special formatting for communication nodes
        if message.startswith("💡"):
            border_style = ACCENT_GOLD
            title = "[bold gold1]Understanding[/]"
            content = message.replace("💡 **Understanding Your Request**", "").strip()
        elif message.startswith("📋"):
            border_style = ACCENT_BLUE
            title = "[bold blue]Execution Plan[/]"
            content = message.replace("📋 **Execution Plan**", "").strip()
        elif message.startswith("⚡"):
            border_style = ACCENT_GREEN
            title = "[bold green]Progress[/]"
            content = message.replace("⚡ **Command Progress**", "").strip()
        elif message.startswith("🔄"):
            border_style = "bold orange1"
            title = "[bold orange1]Retry Analysis[/]"
            content = message
        elif level == "info" or level == "agent":
            if message.startswith("💬 You:"):
                # User Message
                border_style = ACCENT_PURPLE
                title = "[bold]User[/]"
                content = message.replace("💬 You:", "").strip()
            elif message == "Logs cleared.":
                border_style = "dim"
                content = message
            else:
                # Agent Message
                border_style = ACCENT_CYAN
                title = "[bold]Agent[/]"
                content = message
        elif level == "error":
            border_style = "bold red"
            title = "[bold red]Error[/]"
            content = message
        elif level == "warning":
            border_style = "bold orange1"
            title = "[bold orange1]Warning[/]"
            content = message
        elif level == "thought":
            border_style = "slate_blue1"
            title = "[italic slate_blue1]Thinking[/]"
            content = f"[italic]{message}[/]"
        else:
            border_style = "dim"
            content = message

        md = RichMarkdown(content)

        # Create Panel and mount as Static widget
        # Needs to be created before container
        # Use CSS classes for styling instead of hardcoded inline styles
        panel_widget = Static(classes=f"log-panel log-{level}")
        
        # We wrap content in a Panel object for the border/title, but let CSS handle valid styles where possible
        # Textual Panel object styles are limited, so we keep border styling here but move colors to CSS
        panel_widget.update(
            Panel(
                md,
                border_style=border_style,
                title=title,
                title_align="left" if title == "[bold]Agent[/]" else "right",
                padding=(0, 1),
                expand=True,
            )
        )

        # Add copy button (small, neon style)
        copy_btn = Button("📋", variant="default", classes="copy-btn")
        copy_btn.tooltip = "Copy to clipboard"
        # Store content for copying
        copy_btn.copy_content = content
        
        # Create Container for message and copy button
        # Pass children directly to constructor to avoid MountError
        container = Container(panel_widget, copy_btn, classes="message-container")

        self.mount(container)
        self.scroll_end(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle copy button click"""
        if "copy-btn" in event.button.classes and hasattr(event.button, "copy_content"):
            try:
                # Try Textual's clipboard API
                self.app.copy_to_clipboard(event.button.copy_content)
                self.notify(
                    "Copied to clipboard!", title="Success", severity="information"
                )
            except Exception:
                # Fallback
                self.notify(
                    "Clipboard not supported. Use Shift+Click to select.",
                    title="Info",
                    severity="warning",
                )


class LiveExecutionPanel(Vertical):
    """Panel to show live output of running commands"""
    
    # We don't use reactive output directly anymore, we update the TextArea
    _poll_timer: Optional[object] = None

    def compose(self) -> ComposeResult:
        yield Label("Live Output", classes="panel-header")
        # TextArea supports selection and scrolling natively
        yield TextArea(
            "", 
            language="text", 
            read_only=True, 
            id="live-output-text",
            classes="cyber-textarea"
        )
        with Horizontal(classes="panel-footer"):
            yield Button("📋 Copy Log", id="copy-live-btn", variant="default")
            yield Label("", id="live-status")

    def on_mount(self) -> None:
        pass

    def start_monitoring(self, command: str) -> None:
        """Start monitoring the live output log."""
        text_area = self.query_one("#live-output-text", TextArea)
        text_area.text = f"Executing: {command}\nWaiting for output..."
        self.remove_class("-hidden")
        self.styles.display = "block"
        
        # Start timer to read log file
        self.set_interval(0.2, self._poll_log)

    def stop_monitoring(self) -> None:
        pass

    def _poll_log(self) -> None:
        """Read the live log file and update display."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            import tempfile
            log_path = Path(tempfile.gettempdir()) / "reactor_live_output.log"
            if log_path.exists():
                content = log_path.read_text(encoding="utf-8")
                # Truncate if too long
                truncated = False
                if len(content) > 50000:
                    content = "... [truncated] ...\n" + content[-50000:]
                    truncated = True
                
                text_area = self.query_one("#live-output-text", TextArea)
                
                # Check if content actually changed to avoid cursor reset
                if text_area.text != content:
                    # Save cursor? TextArea might reset cursor on setting text.
                    # Ideally we append? But we read full file.
                    # Just set text and scroll end.
                    text_area.text = content
                    text_area.scroll_end(animate=False)
            else:
               status = self.query_one("#live-status", Label)
               status.update(f"Waiting for {log_path}...")
        except Exception as e:
            logger.error(f"Poll error: {e}")

    def set_content(self, result: ExecutionResult) -> None:
        """Update panel content from an ExecutionResult."""
        text_area = self.query_one("#live-output-text", TextArea)
        
        content = (
            f"CMD: {result.command}\n"
            f"EXIT CODE: {result.exit_code}\n\n"
            f"--- STDOUT ---\n{result.stdout}\n\n"
            f"--- STDERR ---\n{result.stderr}\n"
        )
        text_area.text = content
        text_area.scroll_end()

    def clear(self) -> None:
        """Clear the panel content."""
        self.query_one("#live-output-text", TextArea).text = ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-live-btn":
            text_area = self.query_one("#live-output-text", TextArea)
            try:
                self.app.copy_to_clipboard(text_area.text)
                self.notify("Log copied to clipboard!")
            except Exception:
                self.notify("Failed to copy.", severity="error")


class StateIndicator(Static):
    """Visual indicator of agent state"""

    DISPLAY_STATES = {
        "thinking": ("dots", "Thinking...", "yellow"),
        "executing": ("bouncingBar", "Executing...", "green"),
        "error": ("point", "Error", "red"),
        "complete": ("line", "Done", "blue"),
    }

    state: reactive[str] = reactive("idle")

    def render(self) -> Panel:
        if self.state == "idle":
            return Panel("[dim]Idle[/dim]", border_style="dim", expand=True)

        spinner_name, text, color = self.DISPLAY_STATES.get(
            self.state, ("dots", "Processing...", "white")
        )

        return Panel(
            Spinner(spinner_name, text=text, style=color),
            border_style=color,
            title=f"[{color}]{self.state.title()}[/{color}]",
            expand=True,
        )


class ExecutionPlanDisplay(Container):
    """Display the execution plan as a tree"""

    current_plan: reactive[Optional[ExecutionPlan]] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Tree("Execution Plan", id="plan-tree")

    def on_mount(self) -> None:
        self.query_one(Tree).root.add("[dim]No plan generated yet...[/dim]")

    def update_plan(self, plan: Optional[ExecutionPlan]) -> None:
        """Update tree when plan changes"""
        import textwrap

        tree = self.query_one(Tree)
        tree.clear()
        if plan:
            tree.label = "Execution Plan"

            # Wrap strategy text to fit width (max 60 chars per line)
            strategy_lines = textwrap.wrap(plan.overall_strategy, width=60)
            strategy_text = strategy_lines[0] if strategy_lines else ""
            if len(strategy_lines) > 1:
                strategy_text += "..."
            strategy_node = tree.root.add(
                f"[bold cyan]Strategy:[/bold cyan] {strategy_text}"
            )
            strategy_node.expand()

            commands_node = tree.root.add("[bold yellow]Commands:[/bold yellow]")
            commands_node.expand()
            for i, cmd in enumerate(plan.commands):
                risk_label = {
                    RiskLevel.SAFE: "[green]SAFE[/green]",
                    RiskLevel.MODERATE: "[yellow]MODERATE[/yellow]",
                    RiskLevel.DANGEROUS: "[red]DANGEROUS[/red]",
                }.get(cmd.risk_level, "[dim]UNKNOWN[/dim]")

                # Wrap command text to prevent horizontal overflow (max 50 chars)
                cmd_lines = textwrap.wrap(cmd.cmd, width=50)
                if cmd_lines:
                    # First line with risk label
                    cmd_node = commands_node.add(f"{risk_label} [{i}] {cmd_lines[0]}")
                    # Additional lines if wrapped
                    for line in cmd_lines[1:]:
                        cmd_node.add(f"[dim]    {line}[/dim]")
                    # Add description with wrapping
                    desc_lines = textwrap.wrap(cmd.description, width=55)
                    for desc_line in desc_lines:
                        cmd_node.add(f"[dim italic]{desc_line}[/dim italic]")
                else:
                    cmd_node = commands_node.add(f"{risk_label} [{i}] {cmd.cmd}")
                    cmd_node.add(f"[dim]{cmd.description}[/dim]")
        else:
            tree.root.add("[dim]No plan generated yet...[/dim]")


class ResultsPanel(Static):
    """Summary panel for execution results"""

    def on_mount(self) -> None:
        self.update_results([])

    def update_results(self, results: List[ExecutionResult]) -> None:
        """Update results display"""
        if not results:
            self.update(
                Panel(
                    "[dim]No results yet[/dim]",
                    title="Execution Results",
                    border_style="dim blue",
                    expand=True,
                )
            )
            return

        table = Table(title="Execution Results", border_style="blue", expand=True)
        table.add_column("Status", style="bold", width=10)
        # FIX: overflow='fold' allows wrapping within the cell
        table.add_column("Command", overflow="fold", no_wrap=False)
        table.add_column("Time", justify="right", width=8)

        for result in results:
            status = "[bold green]OK[/]" if result.success else "[bold red]FAIL[/]"
            duration = f"{result.duration_ms:.0f}ms"
            # Command column handles the wrapping now
            table.add_row(status, result.command, duration)

        self.update(table)


class ChatInput(TextArea):
    """Custom TextArea for chat input with inline autocomplete"""

    class Submitted(Message):
        """Posted when user presses Enter without Shift"""
        def __init__(self, value: str):
            self.value = value
            super().__init__()

    BINDINGS = [
        Binding("enter", "submit", "Submit", priority=True),
        Binding("shift+enter", "newline", "Newline", priority=True),
        Binding("down", "suggestion_down", "Next", priority=True),
        Binding("up", "suggestion_up", "Prev", priority=True),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.autocomplete_active = False
        self.autocomplete_type = ""  # 'command' or 'file'
        self.autocomplete_start_pos = 0

    def on_text_area_changed(self, event) -> None:
        """Handle text changes to show inline suggestions"""
        from src.tui.helpers.fuzzy_search import get_command_suggestions, get_file_suggestions
        
        text = self.text
        if not text:
            self._hide_suggestions()
            return
        
        # Get current cursor position
        cursor_row, cursor_col = self.cursor_location
        lines = text.split("\n")
        if cursor_row >= len(lines):
            return
        
        current_line = lines[cursor_row]
        text_before_cursor = current_line[:cursor_col]
        
        # Check if we should show autocomplete
        if text_before_cursor.startswith("/"):
            # Command autocomplete
            query = text_before_cursor[1:]
            suggestions = get_command_suggestions(query)
            if suggestions:
                self._show_suggestions(suggestions, "command", 0)
            else:
                self._hide_suggestions()
        elif "@" in text_before_cursor:
            # File autocomplete
            last_at = text_before_cursor.rfind("@")
            query = text_before_cursor[last_at+1:]
            suggestions = get_file_suggestions(query)
            if suggestions:
                self._show_suggestions(suggestions, "file", last_at + 1)
            else:
                self._hide_suggestions()
        else:
            self._hide_suggestions()
    
    def _show_suggestions(self, suggestions: List[str], type: str, start_pos: int) -> None:
        """Show suggestions in the suggestions list"""
        self.autocomplete_active = True
        self.autocomplete_type = type
        self.autocomplete_start_pos = start_pos
        
        # Get parent container and update suggestions list
        try:
            dashboard = self.ancestors[0]  # AgentDashboard
            suggestions_list = dashboard.query_one(SuggestionsList)
            suggestions_list.show_suggestions(suggestions)
        except Exception:
            pass
    
    def _hide_suggestions(self) -> None:
        """Hide suggestions"""
        self.autocomplete_active = False
        try:
            dashboard = self.ancestors[0]
            suggestions_list = dashboard.query_one(SuggestionsList)
            suggestions_list.hide()
        except Exception:
            pass
    
    def action_suggestion_down(self) -> None:
        """Select next suggestion"""
        if not self.autocomplete_active:
            return
        try:
            dashboard = self.ancestors[0]
            suggestions_list = dashboard.query_one(SuggestionsList)
            suggestions_list.select_next()
        except Exception:
            pass
    
    def action_suggestion_up(self) -> None:
        """Select previous suggestion"""
        if not self.autocomplete_active:
            return
        try:
            dashboard = self.ancestors[0]
            suggestions_list = dashboard.query_one(SuggestionsList)
            suggestions_list.select_prev()
        except Exception:
            pass

    def action_submit(self) -> None:
        """Submit the current text or accept autocomplete"""
        # If autocomplete is active, accept the selected suggestion
        if self.autocomplete_active:
            try:
                dashboard = self.ancestors[0]
                suggestions_list = dashboard.query_one(SuggestionsList)
                selected = suggestions_list.get_selected()
                
                if selected:
                    # Auto-complete if only one suggestion OR user has selected one
                    if len(suggestions_list.suggestions) == 1 or suggestions_list.selected_index >= 0:
                        self._accept_suggestion(selected)
                        return
            except Exception:
                pass
        
        # Otherwise submit normally
        value = self.text.strip()
        if value:
            self.post_message(self.Submitted(value))
            self.text = ""
            self.cursor_location = (0, 0)
            self._hide_suggestions()
    
    def _accept_suggestion(self, suggestion: str) -> None:
        """Accept and insert the selected suggestion"""
        text = self.text
        cursor_row, cursor_col = self.cursor_location
        lines = text.split("\n")
        
        if cursor_row >= len(lines):
            return
        
        current_line = lines[cursor_row]
        
        # Replace from autocomplete_start_pos to cursor with suggestion
        new_line = current_line[:self.autocomplete_start_pos] + suggestion + " " + current_line[cursor_col:]
        lines[cursor_row] = new_line
        
        self.text = "\n".join(lines)
        new_cursor_pos = self.autocomplete_start_pos + len(suggestion) + 1
        self.cursor_location = (cursor_row, new_cursor_pos)
        
        # Hide suggestions after accepting
        self._hide_suggestions()
    
    def action_newline(self) -> None:
        """Insert newline"""
        self.insert("\n")



class AgentDashboard(Container):
    """Main dashboard for Agent interaction (Chat & Input)"""

    class ExecutionModeToggled(Message):
        """Message sent when execution mode is toggled"""

        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    execution_mode: reactive[str] = reactive("sequential")
    _autocomplete_modal: Optional[object] = None  # Track current autocomplete modal
    _autocomplete_type: str = ""

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-container"):
            # Header with execution mode toggle
            with Horizontal(id="dashboard-header"):
                yield StateIndicator(id="agent-state")
                yield Button("Sequential", id="mode-toggle", variant="primary")
            yield LogViewer(id="log-viewer")
            with Container(id="input-container"):
                yield ChatInput(id="agent-input")
                yield SuggestionsList()  # Inline suggestions

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle execution mode toggle"""
        if event.button.id == "mode-toggle":
            # Toggle mode
            if self.execution_mode == "sequential":
                self.execution_mode = "parallel"
                event.button.label = "Parallel"
                event.button.variant = "success"
            else:
                self.execution_mode = "sequential"
                event.button.label = "Sequential"
                event.button.variant = "primary"

    async def load_history(self, messages: List[Any]) -> None:
        """Clear and load history from message objects"""
        log_viewer = self.query_one("#log-viewer")
        
        # Clear existing
        for child in log_viewer.query("*"):
            child.remove()
        
        # Re-render messages
        for msg in messages:
            content = msg.content
            if not content:
                continue
                
            # Determine type/style
            msg_type = msg.type
            level = "info"
            is_thought = False
            
            if msg_type == "human":
                content = f"💬 You: {content}"
                level = "info"
            elif msg_type == "ai":
                # Check if it has tool calls (which we might skip or show as activity)
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    # In this simplified view, maybe just show the thought?
                    pass
                level = "agent"
            elif msg_type == "tool":
                # Tool outputs often long, maybe show as thought/activity
                level = "info"
                is_thought = True
            
            # Rough heuristic for "thoughts" vs "responses"
            # If AI message starts with special tokens (formatting), handle in add_log
            
            log_viewer.add_log(str(content), level, is_thought=is_thought)
            
        log_viewer.add_log("🔄 Thread loaded", "info")

