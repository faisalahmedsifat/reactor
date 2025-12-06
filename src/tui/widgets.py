"""
Custom widgets for the Shell Agent TUI
"""

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Input, Label, RichLog, Tree
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from typing import Optional, List
from src.models import Command, ExecutionPlan, ExecutionResult, RiskLevel


class SystemInfoPanel(Static):
    """Display system information at the top"""
    
    system_info: reactive[Optional[dict]] = reactive(None)
    
    def watch_system_info(self, system_info: Optional[dict]) -> None:
        """Update display when system info changes"""
        if system_info:
            self.update(self._render_info(system_info))
    
    def _render_info(self, info: dict) -> Panel:
        """Render system information panel"""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column(style="green")
        
        table.add_row("🖥️  OS:", info.get("os_type", "Unknown"))
        table.add_row("🐚 Shell:", info.get("shell_type", "Unknown"))
        table.add_row("📁 Directory:", info.get("working_directory", "Unknown"))
        
        return Panel(
            table,
            title="[bold blue]⚡ System Information[/bold blue]",
            border_style="blue",
            padding=(0, 1)
        )
    
    def render(self) -> Panel:
        """Render the widget"""
        if self.system_info:
            return self._render_info(self.system_info)
        
        return Panel(
            "[dim]Loading system information...[/dim]",
            title="[bold blue]⚡ System Information[/bold blue]",
            border_style="dim blue"
        )


class CommandInputPanel(Container):
    """Beautiful input panel for user commands"""
    
    def compose(self) -> ComposeResult:
        """Create child widgets"""
        with Vertical():
            yield Label("💬 [bold cyan]Enter your command:[/bold cyan]")
            yield Input(
                placeholder="e.g., Create a Python project with venv and install pytest",
                id="command-input"
            )


class ExecutionPlanDisplay(Container):
    """Display the execution plan as a tree"""
    
    current_plan: reactive[Optional[ExecutionPlan]] = reactive(None)
    current_index: reactive[int] = reactive(0)
    
    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Tree("📋 Execution Plan", id="plan-tree")
    
    def watch_current_plan(self, plan: Optional[ExecutionPlan]) -> None:
        """Update tree when plan changes"""
        if plan:
            tree = self.query_one("#plan-tree", Tree)
            tree.clear()
            tree.label = "📋 Execution Plan"
            
            # Add strategy
            strategy_node = tree.root.add(f"[bold cyan]Strategy:[/bold cyan] {plan.overall_strategy}")
            
            # Add commands
            commands_node = tree.root.add("[bold yellow]Commands:[/bold yellow]")
            for i, cmd in enumerate(plan.commands):
                risk_emoji = {
                    RiskLevel.SAFE: "✅",
                    RiskLevel.MODERATE: "⚠️",
                    RiskLevel.DANGEROUS: "🔴"
                }.get(cmd.risk_level, "❓")
                
                cmd_text = f"{risk_emoji} [{i}] {cmd.cmd}"
                cmd_node = commands_node.add(cmd_text)
                cmd_node.add(f"[dim]{cmd.description}[/dim]")
    
    def watch_current_index(self, index: int) -> None:
        """Highlight current command"""
        # This would update the tree highlighting
        pass


class LogViewer(RichLog):
    """Scrollable log viewer with color-coded messages"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.auto_scroll = True
    
    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log message with appropriate styling"""
        # Define the actual update logic
        def _update_ui():
            styles = {
                "info": "blue",
                "success": "green",
                "warning": "yellow",
                "error": "red",
                "agent": "magenta"
            }
            
            style = styles.get(level, "white")
            self.write(Text(message, style=style))
            self.scroll_end(animate=False)
        
        # Schedule this update to run on the main thread
        # Safe to call from both main thread and background threads
        try:
            self.app.call_from_thread(_update_ui)
        except RuntimeError as e:
            # If we're already on main thread, just call directly
            if "different thread" in str(e):
                _update_ui()
            else:
                raise
    
    def add_command(self, command: str) -> None:
        """Add a command with syntax highlighting"""
        def _update_ui():
            syntax = Syntax(command, "bash", theme="monokai", line_numbers=False)
            self.write(syntax)
            self.scroll_end(animate=False)
        
        try:
            self.app.call_from_thread(_update_ui)
        except RuntimeError as e:
            if "different thread" in str(e):
                _update_ui()
            else:
                raise
    
    def add_result(self, result: ExecutionResult) -> None:
        """Add an execution result"""
        def _update_ui():
            if result.success:
                self.write(Text(f"✅ Success: {result.command}", style="bold green"))
                if result.stdout.strip():
                    self.write(Text(f"Output: {result.stdout[:500]}", style="green"))
            else:
                self.write(Text(f"❌ Failed: {result.command}", style="bold red"))
                if result.stderr.strip():
                    self.write(Text(f"Error: {result.stderr[:500]}", style="red"))
            self.scroll_end(animate=False)
        
        try:
            self.app.call_from_thread(_update_ui)
        except RuntimeError as e:
            if "different thread" in str(e):
                _update_ui()
            else:
                raise


class ApprovalDialog(Container):
    """Modal dialog for command approval"""
    
    command: reactive[str] = reactive("")
    risk_level: reactive[RiskLevel] = reactive(RiskLevel.SAFE)
    warnings: reactive[List[str]] = reactive([])
    
    def compose(self) -> ComposeResult:
        """Create dialog widgets"""
        with Vertical(id="approval-dialog"):
            yield Label("[bold yellow]⚠️  Approval Required[/bold yellow]", id="dialog-title")
            yield Static(id="command-display")
            yield Static(id="warnings-display")
            with Horizontal(id="dialog-buttons"):
                yield Button("✅ Approve", variant="success", id="approve-btn")
                yield Button("❌ Reject", variant="error", id="reject-btn")
    
    def watch_command(self, command: str) -> None:
        """Update command display"""
        cmd_display = self.query_one("#command-display", Static)
        cmd_display.update(Panel(
            Syntax(command, "bash", theme="monokai", line_numbers=False),
            title="[bold]Command[/bold]",
            border_style="yellow"
        ))
    
    def watch_warnings(self, warnings: List[str]) -> None:
        """Update warnings display"""
        warnings_display = self.query_one("#warnings-display", Static)
        if warnings:
            warning_text = "\n".join([f"• {w}" for w in warnings])
            warnings_display.update(Panel(
                warning_text,
                title="[bold red]⚠️  Warnings[/bold red]",
                border_style="red"
            ))
        else:
            warnings_display.update("")


class StatusBar(Static):
    """Bottom status bar"""
    
    status: reactive[str] = reactive("Ready")
    agent_state: reactive[str] = reactive("idle")
    
    def watch_status(self, status: str) -> None:
        """Update status display"""
        self.update(self._render_status())
    
    def watch_agent_state(self, state: str) -> None:
        """Update when agent state changes"""
        self.update(self._render_status())
    
    def _render_status(self) -> Text:
        """Render status bar"""
        state_emoji = {
            "idle": "💤",
            "thinking": "🤔",
            "executing": "⚡",
            "waiting": "⏸️",
            "complete": "✅",
            "error": "❌"
        }.get(self.agent_state, "❓")
        
        text = Text()
        text.append(f"{state_emoji} {self.status}", style="bold")
        text.append(" | ", style="dim")
        text.append("Ctrl+C: Quit", style="cyan")
        text.append(" | ", style="dim")
        text.append("Ctrl+L: Clear", style="cyan")
        
        return text
    
    def render(self) -> Text:
        """Render the widget"""
        return self._render_status()


class ResultsPanel(Static):
    """Summary panel for execution results"""
    
    results: reactive[List[ExecutionResult]] = reactive([])
    
    def watch_results(self, results: List[ExecutionResult]) -> None:
        """Update results display"""
        if not results:
            self.update("[dim]No results yet[/dim]")
            return
        
        table = Table(title="📊 Execution Results", border_style="blue")
        table.add_column("Status", style="bold")
        table.add_column("Command")
        table.add_column("Duration", justify="right")
        
        for result in results:
            status = "✅" if result.success else "❌"
            duration = f"{result.duration_ms:.0f}ms"
            table.add_row(status, result.command[:50], duration)
        
        self.update(table)
