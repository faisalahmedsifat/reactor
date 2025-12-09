from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from pathlib import Path
import os


class FuzzyFinder(ModalScreen):
    """Fuzzy file finder modal"""

    class Selected(Message):
        """File selected message"""

        def __init__(self, path: Path):
            self.path = path
            super().__init__()

    def __init__(self, root: Path = None):
        super().__init__()
        self.root = root or Path.cwd()
        self.files = []

    def compose(self) -> ComposeResult:
        with Container(id="fuzzy-container"):
            yield Label("Search Files", id="fuzzy-title")
            yield Input(placeholder="Type to search...", id="fuzzy-input")
            yield ListView(id="fuzzy-list")

    def on_mount(self) -> None:
        """Load files"""
        self.files = []
        for root, dirs, filenames in os.walk(self.root):
            # Skip hidden dirs like .git
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in filenames:
                if not f.startswith("."):
                    self.files.append(Path(root) / f)

        self.update_list("")
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter list"""
        self.update_list(event.value)

    def update_list(self, query: str) -> None:
        """Update the ListView"""
        list_view = self.query_one(ListView)
        list_view.clear()

        query = query.lower()
        matches = [
            f for f in self.files if query in str(f.relative_to(self.root)).lower()
        ]

        # Limit results for performance
        for match in matches[:20]:
            list_view.append(
                ListItem(Label(str(match.relative_to(self.root))), name=str(match))
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle selection"""
        if event.item and event.item.name:
            self.post_message(self.Selected(Path(event.item.name)))
            self.dismiss()
