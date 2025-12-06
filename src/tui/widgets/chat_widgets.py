from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static, Collapsible, Label
from textual.reactive import reactive
from rich.text import Text
from rich.markdown import Markdown as RichMarkdown
from rich.panel import Panel


class ThoughtsSection(Static):
    """Collapsible section for agent's internal reasoning and tool outputs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.thoughts = []
        self.is_expanded = False
    
    def add_thought(self, message: str):
        """Add a thought/tool output to this section"""
        self.thoughts.append(message)
        self.update_display()
    
    def update_display(self):
        """Update the display with current thoughts"""
        if not self.thoughts:
            return
        
        # Header with thought count
        header = f"💭 Thoughts ({len(self.thoughts)} steps)"
        
        if self.is_expanded:
            # Show all thoughts
            thoughts_text = "\n\n".join([f"**Step {i+1}:** {t}" for i, t in enumerate(self.thoughts)])
            content = f"{header}\n\n{thoughts_text}\n\n▼ Click to collapse"
        else:
            # Compact view
            content = f"{header} ▶ Click to expand"
        
        md = RichMarkdown(content)
        self.update(Panel(
            md,
            border_style="dim",
            title="[dim]Agent Reasoning[/dim]",
            padding=(0, 1),
            style="white on #11112b",
            expand=True
        ))
    
    def on_click(self):
        """Toggle expansion when clicked"""
        self.is_expanded = not self.is_expanded
        self.update_display()


class MessageBubble(Static):
    """A message bubble for user or agent messages"""
    
    def __init__(self, message: str, sender: str = "agent", **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.sender = sender
        self.render_bubble()
    
    def render_bubble(self):
        """Render the message bubble"""
        ACCENT_CYAN = "#00f3ff"   # Agent
        ACCENT_PURPLE = "#bc13fe" # User
        BG_TERTIARY = "#11112b"
        
        if self.sender == "user":
            border_style = ACCENT_PURPLE
            title = "[bold]User[/]"
            title_align = "right"
        else:
            border_style = ACCENT_CYAN
            title = "[bold]Agent[/]"
            title_align = "left"
        
        md = RichMarkdown(self.message)
        self.update(Panel(
            md,
            border_style=border_style,
            title=title,
            title_align=title_align,
            padding=(0, 1),
            style=f"white on {BG_TERTIARY}",
            expand=True
        ))
