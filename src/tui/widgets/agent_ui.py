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
    """Scrollable log viewer with text selection support"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.can_focus = True
    
    def add_log(self, message: str, level: str = "info") -> None:
        """Add a log message with styling"""
        from rich.markdown import Markdown as RichMarkdown
        
        # Cyberpunk Palette
        ACCENT_CYAN = "#00f3ff"   # Agent
        ACCENT_PURPLE = "#bc13fe" # User
        BG_TERTIARY = "#11112b"   # Message BG

        border_style = "dim"
        title = None
        
        if level == "info":
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
        else:
            border_style = "dim"
            content = message
            
        md = RichMarkdown(content)
        
        # Create Panel and mount as Static widget - this allows expand=True to work!
        # The Panel will respect container width just like StateIndicator does
        panel_widget = Static()
        panel_widget.update(Panel(
            md,
            border_style=border_style,
            title=title,
            title_align="left" if title == "[bold]Agent[/]" else "right",
            padding=(0, 1),
            style=f"white on {BG_TERTIARY}",
            expand=True  # Now this will work correctly!
        ))
        
        self.mount(panel_widget)
        self.scroll_end(animate=False)

class LiveExecutionPanel(Static):
    """Panel to show live output of running commands"""
    
    output: reactive[object] = reactive("")
    
    def set_content(self, result: ExecutionResult) -> None:
        """Update panel content from an ExecutionResult."""
        from rich.text import Text

        header = Text(f"CMD: {result.command}\nEXIT CODE: {result.exit_code}\n", style="bold")
        
        stdout_header = Text("\n--- STDOUT ---\n", style="bold green")
        # FIX: folding overflow to prevent horizontal scroll
        stdout_content = Text(result.stdout if result.stdout.strip() else "[empty]", style="green", overflow="fold", no_wrap=False)

        stderr_header = Text("\n--- STDERR ---\n", style="bold red")
        stderr_content = Text(result.stderr if result.stderr.strip() else "[empty]", style="red", overflow="fold", no_wrap=False)

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
            height=None,
            expand=True # Force fit to container width
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
            
        spinner_name, text, color = self.DISPLAY_STATES.get(self.state, ("dots", "Processing...", "white"))
        
        return Panel(
            Spinner(spinner_name, text=text, style=color),
            border_style=color,
            title=f"[{color}]{self.state.title()}[/{color}]",
            expand=True
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
            # FIX: Truncate strategy if too long
            short_strat = (plan.overall_strategy[:50] + '...') if len(plan.overall_strategy) > 50 else plan.overall_strategy
            strategy_node = tree.root.add(f"[bold cyan]Strategy:[/bold cyan] {short_strat}")
            strategy_node.expand()
            
            commands_node = tree.root.add("[bold yellow]Commands:[/bold yellow]")
            commands_node.expand()
            for i, cmd in enumerate(plan.commands):
                risk_emoji = {
                    RiskLevel.SAFE: "✅",
                    RiskLevel.MODERATE: "⚠️",
                    RiskLevel.DANGEROUS: "🔴"
                }.get(cmd.risk_level, "❓")
                
                # FIX: Fold command text
                cmd_text = Text(f"{risk_emoji} [{i}] {cmd.cmd}", overflow="fold", no_wrap=False)
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
            self.update(Panel("[dim]No results yet[/dim]", title="📊 Execution Results", border_style="dim blue", expand=True))
            return
        
        table = Table(title="📊 Execution Results", border_style="blue", expand=True)
        table.add_column("Status", style="bold", width=8)
        # FIX: overflow='fold' allows wrapping within the cell
        table.add_column("Command", overflow="fold", no_wrap=False) 
        table.add_column("Time", justify="right", width=8)
        
        for result in results:
            status = "[bold green]✅ OK[/]" if result.success else "[bold red]❌ FAIL[/]"
            duration = f"{result.duration_ms:.0f}ms"
            # Command column handles the wrapping now
            table.add_row(status, result.command, duration)
        
        self.update(table)

class AgentDashboard(Container):
    """Main dashboard for Agent interaction (Chat & Input)"""
    
    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-container"):
            yield StateIndicator(id="agent-state")
            yield LogViewer(id="log-viewer")
            with Container(id="input-container"):
                yield Input(placeholder="Ask the agent...", id="agent-input")