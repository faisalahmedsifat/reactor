"""
src/tui/widgets/suggestions_list.py

Inline autocomplete suggestions widget (VSCode-style).
"""

from textual.widgets import Static
from textual.reactive import reactive
from textual.containers import Container
from rich.text import Text
from typing import List


class SuggestionsList(Static):
    """Inline suggestions list that appears below input"""

    suggestions: reactive[List[str]] = reactive([])
    selected_index: reactive[int] = reactive(0)

    DEFAULT_CSS = """
    SuggestionsList {
        width: 100%;
        height: auto;
        max-height: 10;
        background: $surface;
        border: solid $primary;
        padding: 0;
        display: none;
    }
    
    SuggestionsList.visible {
        display: block;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.suggestions = []
        self.selected_index = 0

    def watch_suggestions(self, new_suggestions: List[str]) -> None:
        """Update display when suggestions change"""
        if new_suggestions:
            self.add_class("visible")
            self.selected_index = 0
        else:
            self.remove_class("visible")
        self.refresh()

    def render(self) -> Text:
        """Render suggestions"""
        if not self.suggestions:
            return Text("")

        lines = []
        for i, suggestion in enumerate(self.suggestions[:10]):  # Max 10
            if i == self.selected_index:
                # Highlighted selection
                lines.append(Text(f"→ {suggestion}", style="bold cyan on blue"))
            else:
                lines.append(Text(f"  {suggestion}", style="dim"))

        if len(self.suggestions) > 10:
            lines.append(
                Text(f"  ... and {len(self.suggestions) - 10} more", style="dim italic")
            )

        return Text("\n").join(lines)

    def show_suggestions(self, suggestions: List[str]) -> None:
        """Show suggestions"""
        self.suggestions = suggestions

    def hide(self) -> None:
        """Hide suggestions"""
        self.suggestions = []

    def select_next(self) -> None:
        """Select next suggestion"""
        if self.suggestions and self.selected_index < len(self.suggestions) - 1:
            self.selected_index += 1
            self.refresh()

    def select_prev(self) -> None:
        """Select previous suggestion"""
        if self.suggestions and self.selected_index > 0:
            self.selected_index -= 1
            self.refresh()

    def get_selected(self) -> str | None:
        """Get currently selected suggestion"""
        if self.suggestions and 0 <= self.selected_index < len(self.suggestions):
            return self.suggestions[self.selected_index]
        return None
