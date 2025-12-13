from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import (
    Static,
    RichLog,
    Label,
    Input,
    Tree,
    Markdown,
    Button,
    TextArea,
)
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


class WelcomeWidget(Static):
    """Welcome screen with branding and prompts"""

    def compose(self) -> ComposeResult:
        branding = """
[bold cyan]
    ____                  ___     ______  ______  ____  ____ 
   / __ \  ___   ____    /   |   / ____/ /_  __/ / __ \/ __ \\
  / /_/ / / _ \ / __ \  / /| |  / /       / /   / / / / /_/ /
 / _, _/ /  __// / / / / ___ | / /___    / /   / /_/ / _, _/ 
/_/ |_|  \___//_/ /_/ /_/  |_| \____/   /_/    \____/_/ |_|  
[/]                                                             
[dim]Advanced Agentic Environment[/]
"""
        yield Static(branding, classes="welcome-branding")
        yield Label("Try these prompts to get started:", classes="welcome-subtitle")

        prompts = [
            "Analyze this repository structure",
            "Refactor src/tui/app.tcss to be more modern",
            "Create a new agent for database management",
            "Explain how the detailed execution plan works",
        ]

        for prompt in prompts:
            yield Static(f"⚡ [bold]{prompt}[/]", classes="welcome-prompt")


class LogViewer(VerticalScroll):
    """Scrollable log viewer with collapsible thoughts support"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_focus = True
        self.current_activity = []
        self.pending_activity_widget = None
        self.welcome_widget = None

    def on_mount(self) -> None:
        """Show welcome message on mount if empty"""
        self.welcome_widget = WelcomeWidget()
        self.mount(self.welcome_widget)

    def remove_welcome_message(self):
        """Remove welcome message if it exists"""
        if self.welcome_widget:
            self.welcome_widget.remove()
            self.welcome_widget = None

    def add_activity(self, message: str) -> None:
        """Add an activity/tool call to the current execution session"""
        if not message.strip():
            return

        self.remove_welcome_message()

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

        self.remove_welcome_message()

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
        # Create Panel and mount as Static widget
        # Determine specific class for styling
        msg_class = f"log-{level}"
        container_classes = f"message-container {msg_class}"
        is_chat_message = False

        if level == "info" and title == "[bold]User[/]":
            msg_class = "log-user"
            container_classes = f"message-container log-user"
            is_chat_message = True
        elif title == "[bold]Agent[/]":
            msg_class = "log-agent"
            container_classes = f"message-container log-agent"
            is_chat_message = True
        elif level == "agent":
            msg_class = "log-agent"
            container_classes = f"message-container log-agent"
            is_chat_message = True

        # We perform styling on the Container now (borders, backgrounds)
        # So the inner static widget (panel_widget) should generally be transparent/unbordered
        # unless it's a special panel type.

        panel_widget = Static(classes="message-content")

        # For Chat Messages (User/Agent), we DROP the rich.Panel because the CSS provides the "bubble" look.
        # For other types (Error, Plan, etc.) we keep the Panel for its specific visual formatting.
        if is_chat_message:
            panel_widget.update(md)
        else:
            # For System/Other messages, keep the 'Rich' Panel look for now
            # But we might need to be careful about double borders if container has them too.
            # Best approach: if it has rich.Panel, the container acts as a wrapper.
            panel_widget.update(
                Panel(
                    md,
                    border_style=border_style,
                    title=title,
                    title_align="left" if level == "agent" else "right",
                    padding=(0, 1),
                    expand=True,
                )
            )

        # Add copy button (Text icon: CPY)
        copy_btn = Button("COPY", variant="default", classes="copy-btn")
        copy_btn.tooltip = "Copy to clipboard"
        copy_btn.copy_content = content

        # Create Container for message and copy button
        # The container uses the `container_classes` calculated above
        container = Container(panel_widget, copy_btn, classes=container_classes)

        self.mount(container)
        self.scroll_end(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle copy button click"""
        if "copy-btn" in event.button.classes and hasattr(event.button, "copy_content"):
            try:
                # Try Textual's clipboard API
                self.app.copy_to_clipboard(event.button.copy_content)
                self.notify("Copied!", title="Success", severity="information")
            except Exception:
                pass


class InteractiveShellPanel(Vertical):
    """Panel to show live output of interactive shell sessions"""

    _poll_timer: Optional[object] = None
    current_log_path: Optional[str] = None
    session_id: Optional[str] = None
    log_file_pos: int = 0

    # Bindings for keyboard shortcuts
    BINDINGS = [
        Binding("ctrl+k", "kill_session", "Kill Session", priority=True),
    ]

    class ShellInputSubmitted(Message):
        """Posted when user submits input to the shell"""

        def __init__(self, session_id: str, value: str):
            self.session_id = session_id
            self.value = value
            super().__init__()

    class KillShellSession(Message):
        """Posted when user requests to kill the current session"""

        def __init__(self, session_id: str):
            self.session_id = session_id
            super().__init__()

    class SessionSelected(Message):
        """Posted when user selects a different session"""

        def __init__(self, session_id: str):
            self.session_id = session_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Interactive Shell", classes="panel-header")
        yield RichLog(
            id="shell-output-log",
            classes="cyber-textarea",
            highlight=False,
            markup=False,
            wrap=True,
        )
        yield Input(
            placeholder="Type command...", id="shell-input", classes="shell-input"
        )
        with Horizontal(classes="panel-footer"):
            # Use Select for session management instead of static label
            from textual.widgets import Select

            yield Select(
                [],
                prompt="No Active Sessions",
                id="session-select",
                classes="session-select",
                allow_blank=True,
            )
            # Add explicit Kill button next to Copy
            yield Button(
                "💀 Kill (Ctrl+K)",
                id="kill-shell-btn",
                variant="error",
                classes="kill-btn",
            )
            yield Button("📋 Copy", id="copy-shell-btn", variant="default")

    def start_monitoring(self, session_id: str, log_path: str) -> None:
        """Start monitoring a specific session log."""
        self.session_id = session_id
        self.current_log_path = log_path
        self.log_file_pos = 0

        rich_log = self.query_one("#shell-output-log", RichLog)
        rich_log.clear()
        rich_log.write(
            f"--- Attached to Session {session_id} ---\nWaiting for output..."
        )

        # Update select
        from textual.widgets import Select

        select = self.query_one("#session-select", Select)
        # We might need to fetch all sessions from app, but for now ensure current is selected
        # If the option doesn't exist, simple-hack add it
        current_options = [x[0] for x in select.options] if select.options else []
        if session_id not in current_options:
            # This is a bit hacky, normally app should drive the list
            pass
        select.value = session_id
        select.prompt = f"ACTIVE: {session_id}"

        # Enable input
        shell_input = self.query_one("#shell-input", Input)
        shell_input.disabled = False
        shell_input.value = ""
        shell_input.focus()

        self.remove_class("-hidden")
        self.styles.display = "block"

        # Start timer to read log file
        self.set_interval(0.2, self._poll_log)

    def stop_monitoring(self) -> None:
        """Stop monitoring."""
        from textual.widgets import Select

        select = self.query_one("#session-select", Select)
        select.prompt = f"CLOSED: {self.session_id}"
        select.value = None

        # Disable input
        shell_input = self.query_one("#shell-input", Input)
        shell_input.disabled = True

        self.current_log_path = None
        self.session_id = None

    def update_session_list(self, sessions: List[str], active_id: Optional[str] = None):
        """Update the dropdown of active sessions"""
        from textual.widgets import Select

        select = self.query_one("#session-select", Select)
        options = [(s, s) for s in sessions]
        select.set_options(options)
        if active_id:
            select.value = active_id

    def _poll_log(self) -> None:
        """Read the live log file incrementally and update display."""
        if not self.current_log_path:
            return

        try:
            log_path = Path(self.current_log_path)
            if not log_path.exists():
                return

            with open(log_path, "rb") as f:
                f.seek(self.log_file_pos)
                new_data = f.read()

                if new_data:
                    self.log_file_pos = f.tell()
                    text_content = new_data.decode("utf-8", errors="replace")
                    rich_text = Text.from_ansi(text_content)

                    rich_log = self.query_one("#shell-output-log", RichLog)
                    rich_log.write(rich_text)
        except Exception:
            pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "shell-input":
            if self.session_id and event.value:
                self.post_message(
                    self.ShellInputSubmitted(self.session_id, event.value)
                )
                event.input.value = ""

    def action_kill_session(self) -> None:
        """Handle kill session action (Ctrl+K)"""
        if self.session_id:
            self.post_message(self.KillShellSession(self.session_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-shell-btn":
            # Copy implementation...
            try:
                self.notify(
                    "Copy not fully supported on RichLog yet.", severity="warning"
                )
            except Exception:
                pass
        elif event.button.id == "kill-shell-btn":
            self.action_kill_session()

    def on_select_changed(self, event) -> None:
        """Handle session switch"""
        from textual.widgets import Select

        if event.control.id == "session-select":
            if event.value and event.value != self.session_id:
                self.post_message(self.SessionSelected(event.value))


class StateIndicator(Static):
    """Visual indicator of agent state with animation"""

    DISPLAY_STATES = {
        "thinking": ("Thinking...", "yellow"),
        "executing": ("Executing...", "green"),
        "error": ("Error", "red"),
        "complete": ("Done", "blue"),
        "idle": ("Idle", "dim"),
        "compacting": ("Compacting...", "magenta"),
    }

    # Frames for the spinner animation
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    state: reactive[str] = reactive("idle")
    spinner_index = reactive(0)

    def on_mount(self) -> None:
        """Start the animation timer"""
        self.set_interval(0.1, self.advance_spinner)

    def advance_spinner(self) -> None:
        """Advance the spinner frame if active"""
        if self.state in ["thinking", "executing", "compacting"]:
            self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)

    def render(self) -> str:
        # Simplified render returning a string/Renderable instead of a Panel
        # allowing CSS to control the container style (badge look)
        if self.state == "idle":
            return "Idle"

        text, color = self.DISPLAY_STATES.get(self.state, ("Processing...", "white"))

        # Only show spinner if state is active
        if self.state in ["thinking", "executing", "compacting"]:
            frame = self.SPINNER_FRAMES[self.spinner_index]
            content = f" {frame} {text} "
        else:
            content = f" {text} "

        # Return rich Text object with style
        return Text(content, style=color)


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
        from src.tui.helpers.fuzzy_search import (
            get_command_suggestions,
            get_file_suggestions,
        )

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
            query = text_before_cursor[last_at + 1 :]
            suggestions = get_file_suggestions(query)
            if suggestions:
                self._show_suggestions(suggestions, "file", last_at + 1)
            else:
                self._hide_suggestions()
        else:
            self._hide_suggestions()

    def _show_suggestions(
        self, suggestions: List[str], type: str, start_pos: int
    ) -> None:
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
                    if (
                        len(suggestions_list.suggestions) == 1
                        or suggestions_list.selected_index >= 0
                    ):
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
        new_line = (
            current_line[: self.autocomplete_start_pos]
            + suggestion
            + " "
            + current_line[cursor_col:]
        )
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
