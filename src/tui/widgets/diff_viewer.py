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


class CodeViewer(VerticalScroll):
    """Widget to display code files and diffs"""

    DEFAULT_CSS = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_content: Dict = {}  # Store content by filepath
        self.modes: Dict = {}  # 'code' or 'diff' per file

    def compose(self):
        yield Label("📝 Context / Draft", classes="diff-header")
        # Use a single Static widget for content that we update directly
        yield Static("No files loaded", id="code-display", classes="diff-empty")

    def show_file(self, filepath: str, content: str, language: str = "python"):
        """Display file content"""
        self.current_content.clear() 
        self.current_content[filepath] = {"type": "code", "content": content, "language": language}
        self.log(f"CodeViewer showing file: {filepath} ({len(content)} bytes)")
        self.update_display()

    def add_diff(self, filepath: str, old_content: str, new_content: str):
        """Add a file diff to display"""
        self.current_content[filepath] = {
            "type": "diff",
            "old": old_content,
            "new": new_content,
        }
        self.update_display()

    def update_display(self):
        """Update the display"""
        display = self.query_one("#code-display", Static)
        
        if not self.current_content:
            display.update("No files loaded")
            display.add_class("diff-empty")
            return
        
        display.remove_class("diff-empty")

        # Render the first/only item
        # Since we clear() in show_file, we usually have 1 item.
        # If we have multiple (diffs?), we might need to change this logic or just show the last one.
        # For now, let's just pick the last one added.
        filepath, data = list(self.current_content.items())[-1]
            
        if data["type"] == "code":
            panel = Panel(
                Syntax(
                    data["content"],
                    data["language"],
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True, # Ensure long lines don't break layout
                ),
                title=f"[bold green]{filepath}[/]",
                border_style="green",
            )
            display.update(panel)
            
        elif data["type"] == "diff":
            # Create unified diff
            old_lines = data["old"].splitlines(keepends=True)
            new_lines = data["new"].splitlines(keepends=True)

            diff = difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{filepath}",
                tofile=f"b/{filepath}",
                lineterm="",
            )
            diff_text = "".join(diff)

            panel = Panel(
                Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                title=f"[bold cyan]Diff: {filepath}[/]",
                border_style="cyan",
            )
            display.update(panel)
        
        # Force refresh to be safe, though update() should trigger it
        self.refresh()

    def clear(self):
        """Clear all content"""
        self.current_content.clear()
        self.update_display()
