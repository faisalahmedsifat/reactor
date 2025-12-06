from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import Static, RichLog, Label, Input, Tree, Markdown
from textual.reactive import reactive
from rich.text import Text
from rich.syntax import Syntax
from rich.spinner import Spinner
from rich.panel import Panel
from rich.table import Table
from typing import Optional, List

from src.models import ExecutionResult, ExecutionPlan, RiskLevel, Command

class LogViewer(VerticalScroll):
    """Scrollable log viewer with styled chat bubbles using Markdown"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
    
    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log message with appropriate styling and auto-scroll"""
        
        # Determine styling class based on content and level
        css_class = "message-system" # Default
        
        if level == "info":
            if message.startswith("💬 You:"):
                # User Message
                css_class = "message-user"
                # Strip prefix for cleaner look if desired, or keep it
                # message = message.replace("💬 You:", "").strip() 
            elif message == "Logs cleared.":
                css_class = "message-system"
            else:
                # Likely Agent Response content
                css_class = "message-agent"
        elif level == "agent":
            css_class = "message-system"
        elif level == "error":
            css_class = "message-system state-error"
            
        # Create Widget
        # using Markdown for rich content rendering
        msg_widget = Markdown(message)
        msg_widget.add_class(css_class)
        
        self.mount(msg_widget)
        self.call_after_refresh(self.scroll_end, animate=True)

    def clear(self) -> None:
        """Clear all messages"""
        self.remove_children()

class LiveExecutionPanel(Static):
    """Panel to show live output of running commands"""
    
    output: reactive[object] = reactive("")
    
    def set_content(self, result: ExecutionResult) -> None:
        """Update panel content from an ExecutionResult."""
        from rich.text import Text

        header = Text(f"CMD: {result.command}\nEXIT CODE: {result.exit_code}\n", style="bold")
        
        stdout_header = Text("\n--- STDOUT ---\n", style="bold green")
        stdout_content = Text(result.stdout if result.stdout.strip() else "[empty]", style="green")

        stderr_header = Text("\n--- STDERR ---\n", style="bold red")
        stderr_content = Text(result.stderr if result.stderr.strip() else "[empty]", style="red")

        self.update(Text.assemble(header, stdout_header, stdout_content, stderr_header, stderr_content))

    def clear(self) -> None:
        """Clear the panel content."""
        self.update("")

    def render(self) -> Panel:
        content = self.output or "[dim]No active execution[/dim]"
        return Panel(
            content,
            title="[bold yellow]⚡ Live Output[/bold yellow]",
            border_style="yellow",
            height=None
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
            return Panel("[dim]Idle[/dim]", border_style="dim")
            
        spinner_name, text, color = self.DISPLAY_STATES.get(self.state, ("dots", "Processing...", "white"))
        
        return Panel(
            Spinner(spinner_name, text=text, style=color),
            border_style=color,
            title=f"[{color}]{self.state.title()}[/{color}]"
        )

class ExecutionPlanDisplay(Container):
    """Display the execution plan as a tree"""
    
    current_plan: reactive[Optional[ExecutionPlan]] = reactive(None)
    
    def compose(self) -> ComposeResult:
        yield Tree("📋 Execution Plan", id="plan-tree")
    
    def on_mount(self) -> None:
        self.query_one(Tree).root.add("[dim]No plan generated yet...[/dim]")

    def update_plan(self, plan: Optional[ExecutionPlan]) -> None:
        """Update tree when plan changes"""
        tree = self.query_one(Tree)
        tree.clear()
        if plan:
            tree.label = "📋 Execution Plan"
            strategy_node = tree.root.add(f"[bold cyan]Strategy:[/bold cyan] {plan.overall_strategy}")
            strategy_node.expand()
            
            commands_node = tree.root.add("[bold yellow]Commands:[/bold yellow]")
            commands_node.expand()
            for i, cmd in enumerate(plan.commands):
                risk_emoji = {
                    RiskLevel.SAFE: "✅",
                    RiskLevel.MODERATE: "⚠️",
                    RiskLevel.DANGEROUS: "🔴"
                }.get(cmd.risk_level, "❓")
                
                cmd_text = f"{risk_emoji} [{i}] {cmd.cmd}"
                cmd_node = commands_node.add(cmd_text)
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
            self.update(Panel("[dim]No results yet[/dim]", title="📊 Execution Results", border_style="dim blue"))
            return
        
        table = Table(title="📊 Execution Results", border_style="blue", expand=True)
        table.add_column("Status", style="bold", width=8)
        table.add_column("Command")
        table.add_column("Duration", justify="right", width=10)
        
        for result in results:
            status = "[bold green]✅ OK[/]" if result.success else "[bold red]❌ FAIL[/]"
            duration = f"{result.duration_ms:.0f}ms"
            table.add_row(status, Text(result.command, overflow="ellipsis", no_wrap=True), duration)
        
        self.update(table)

class AgentDashboard(Container):
    """Main dashboard for Agent interaction (Chat & Input)"""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-container"):
            yield StateIndicator(id="agent-state")
            yield LogViewer(id="log-viewer")
            yield LiveExecutionPanel(id="live-execution")
            with Container(id="input-container"):
                yield Input(placeholder="Ask the agent...", id="agent-input")