"""
File reference modal for @ mentions
Simple modal screen that opens when user types @
"""
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from pathlib import Path
import os


class FileReferenceModal(ModalScreen):
    """Modal for selecting a file to reference with @"""
    
    class FileSelected(Message):
        """File selected message"""
        def __init__(self, path: str):
            self.path = path
            super().__init__()

    def __init__(self, root: Path = None):
        super().__init__()
        self.root = root or Path.cwd()
        self.files = []
    
    def compose(self) -> ComposeResult:
        with Container(id="file-ref-container"):
            yield Label("📁 Select File to Reference", id="file-ref-title")
            yield Input(placeholder="Type to filter files...", id="file-ref-input")
            yield ListView(id="file-ref-list")

    def on_mount(self) -> None:
        """Load files and focus input"""
        self.load_files()
        self.update_list("")
        self.query_one(Input).focus()

    def load_files(self):
        """Scan project for files"""
        self.files = []
        for root, dirs, filenames in os.walk(self.root):
            # Skip hidden dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
            for f in filenames:
                if not f.startswith('.') and not f.endswith('.pyc'):
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(self.root)
                    self.files.append(str(rel_path))

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter list as user types"""
        self.update_list(event.value)

    def update_list(self, query: str) -> None:
        """Update the displayed file list"""
        list_view = self.query_one(ListView)
        list_view.clear()
        
        query_lower = query.lower()
        if query_lower:
            matches = [f for f in self.files if query_lower in f.lower()]
        else:
            matches = self.files
        
        # Limit to 15 results
        for match in matches[:15]:
            list_view.append(ListItem(Label(match), name=match))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle file selection"""
        if event.item and event.item.name:
            self.post_message(self.FileSelected(event.item.name))
            self.dismiss()
    
    def on_key(self, event) -> None:
        """Handle keyboard navigation"""
        list_view = self.query_one(ListView)
        
        if event.key == "escape":
            self.dismiss()
        elif event.key == "up":
            # Move selection up (backward in list)
            list_view.action_cursor_up()
            event.prevent_default()
        elif event.key == "down":
            # Move selection down (forward in list)
            list_view.action_cursor_down()
            event.prevent_default()
        elif event.key == "enter":
            # Select current item
            if list_view.highlighted_child:
                self.post_message(self.FileSelected(list_view.highlighted_child.name))
                self.dismiss()
            event.prevent_default()
