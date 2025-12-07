"""
File diff viewer widget for displaying before/after changes made by the agent.
Shows syntax-highlighted diffs in the right panel.
"""

from textual.widget import Widget
from textual.widgets import Static, Label
from textual.containers import VerticalScroll, Container
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from typing import Optional, Dict
import difflib


class DiffViewer(VerticalScroll):
    """Widget to display file diffs"""

    DEFAULT_CSS = """
    DiffViewer {
        background: $panel;
        border: solid $primary;
        padding: 1;
    }
    
    .diff-header {
        background: $accent;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    
    .diff-empty {
        color: $text-muted;
        text-align: center;
        padding: 2;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_diffs: Dict = {}

    def compose(self):
        yield Label("📝 File Changes", classes="diff-header")
        yield Container(
            Static("No changes yet", classes="diff-empty"), id="diff-content"
        )

    def add_diff(self, filepath: str, old_content: str, new_content: str):
        """Add a file diff to display"""
        self.current_diffs[filepath] = {"old": old_content, "new": new_content}
        self.update_display()

    def update_display(self):
        """Update the diff display"""
        content_container = self.query_one("#diff-content", Container)
        content_container.remove_children()

        if not self.current_diffs:
            content_container.mount(Static("No changes yet", classes="diff-empty"))
            return

        for filepath, diff_data in self.current_diffs.items():
            # Create unified diff
            old_lines = diff_data["old"].splitlines(keepends=True)
            new_lines = diff_data["new"].splitlines(keepends=True)

            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
                lineterm="",
            )

            diff_text = "\n".join(diff)

            # Create panel with diff
            diff_panel = Panel(
                Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                title=f"[bold cyan]{filepath}[/]",
                border_style="cyan",
            )

            content_container.mount(Static(diff_panel))

    def clear(self):
        """Clear all diffs"""
        self.current_diffs.clear()
        self.update_display()
