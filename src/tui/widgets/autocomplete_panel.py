"""
src/tui/widgets/autocomplete_panel.py

Autocomplete suggestion panel for TUI.
"""

from textual.widgets import Static
from textual.reactive import reactive
from rich.table import Table
from typing import List


class AutocompletePanel(Static):
    """Panel showing autocomplete suggestions"""

    suggestions: reactive[List[str]] = reactive([])
    selected_index: reactive[int] = reactive(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.suggestions = []
        self.selected_index = 0

    def watch_suggestions(self, new_suggestions: List[str]) -> None:
        """Update display when suggestions change"""
        self.refresh()

    def watch_selected_index(self, new_index: int) -> None:
        """Update display when selection changes"""
        self.refresh()

    def render(self) -> Table | str:
        """Render suggestions table"""
        if not self.suggestions:
            return ""

        table = Table(show_header=False, show_edge=False, padding=(0, 1), expand=True)
        table.add_column("Suggestion", style="cyan")

        for i, suggestion in enumerate(self.suggestions[:5]):  # Show max 5
            if i == self.selected_index:
                table.add_row(f"→ {suggestion}", style="bold green")
            else:
                table.add_row(f"  {suggestion}", style="dim")

        if len(self.suggestions) > 5:
            table.add_row(
                f"  ... and {len(self.suggestions) - 5} more", style="dim italic"
            )

        return table

    def show_suggestions(self, suggestions: List[str]) -> None:
        """Show suggestions"""
        self.suggestions = suggestions
        self.selected_index = 0
        self.remove_class("-hidden")
        self.styles.display = "block"

    def hide_suggestions(self) -> None:
        """Hide suggestions"""
        self.suggestions = []
        self.add_class("-hidden")
        self.styles.display = "none"

    def select_next(self) -> None:
        """Select next suggestion"""
        if self.suggestions:
            self.selected_index = (self.selected_index + 1) % len(self.suggestions)

    def select_prev(self) -> None:
        """Select previous suggestion"""
        if self.suggestions:
            self.selected_index = (self.selected_index - 1) % len(self.suggestions)

    def get_selected(self) -> str | None:
        """Get currently selected suggestion"""
        if self.suggestions and 0 <= self.selected_index < len(self.suggestions):
            return self.suggestions[self.selected_index]
        return None
