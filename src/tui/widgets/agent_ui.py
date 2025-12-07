from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, RichLog, Label, Input, Tree, Markdown, Button
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List

from src.models import ExecutionResult, ExecutionPlan, RiskLevel, Command


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
        else:
            border_style = "dim"
            content = message

        md = RichMarkdown(content)

        # Create Panel and mount as Static widget
        # Needs to be created before container
        panel_widget = Static()
        panel_widget.update(
            Panel(
                md,
                border_style=border_style,
                title=title,
                title_align="left" if title == "[bold]Agent[/]" else "right",
                padding=(0, 1),
                style=f"white on {BG_TERTIARY}",
                expand=True,
            )
        )

        # Add copy button (small, unobtrusive)
        copy_btn = Button("Copy", variant="default", classes="copy-btn")
        copy_btn.tooltip = "Copy message to clipboard"
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


class LiveExecutionPanel(Static):
    """Panel to show live output of running commands"""

    output: reactive[object] = reactive("")

    def set_content(self, result: ExecutionResult) -> None:
        """Update panel content from an ExecutionResult."""
        from rich.text import Text

        header = Text(
            f"CMD: {result.command}\\nEXIT CODE: {result.exit_code}\\n", style="bold"
        )

        stdout_header = Text("\\n--- STDOUT ---\\n", style="bold green")
        # FIX: folding overflow to prevent horizontal scroll
        stdout_content = Text(
            result.stdout if result.stdout.strip() else "[empty]",
            style="green",
            overflow="fold",
            no_wrap=False,
        )

        stderr_header = Text("\\n--- STDERR ---\\n", style="bold red")
        stderr_content = Text(
            result.stderr if result.stderr.strip() else "[empty]",
            style="red",
            overflow="fold",
            no_wrap=False,
        )

        self.update(
            Text.assemble(
                header, stdout_header, stdout_content, stderr_header, stderr_content
            )
        )

    def clear(self) -> None:
        """Clear the panel content."""
        self.update("")

    def render(self) -> Panel:
        content = self.output or "[dim]No active execution[/dim]"
        return Panel(
            content,
            title="[bold yellow]Live Output[/bold yellow]",
            border_style="yellow",
            height=None,
            expand=True,  # Force fit to container width
        )


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


class AgentDashboard(Container):
    """Main dashboard for Agent interaction (Chat & Input)"""

    class ExecutionModeToggled(Message):
        """Message sent when execution mode is toggled"""

        def __init__(self, mode: str):
            self.mode = mode
            super().__init__()

    execution_mode: reactive[str] = reactive("sequential")

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-container"):
            # Header with execution mode toggle
            with Horizontal(id="dashboard-header"):
                yield StateIndicator(id="agent-state")
                yield Button("Sequential", id="mode-toggle", variant="primary")
            yield LogViewer(id="log-viewer")
            with Container(id="input-container"):
                yield Input(placeholder="Ask the agent...", id="agent-input")

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

            # Post message to app
            self.post_message(self.ExecutionModeToggled(self.execution_mode))
