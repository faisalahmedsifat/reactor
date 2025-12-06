"""
File autocomplete overlay for @ references in TUI input
"""
from textual.widgets import ListView, ListItem, Label
from textual.containers import Container
from textual.message import Message
from textual.reactive import reactive
from pathlib import Path
import os


class FileAutocomplete(Container):
    """Autocomplete overlay for file selection"""
    
    class FileSelected(Message):
        """File selected from autocomplete"""
        def __init__(self, filepath: str):
            self.filepath = filepath
            super().__init__()
    
    class Dismissed(Message):
        """Autocomplete dismissed without selection"""
        pass
    
    query: reactive[str] = reactive("")
    selected_index: reactive[int] = reactive(0)
    
    def __init__(self, root_path: Path = None, **kwargs):
        super().__init__(**kwargs)
        self.root_path = root_path or Path.cwd()
        self.files = []
        self.filtered_files = []
        self.can_focus = True  # Allow this widget to receive focus and keyboard events
        
    def compose(self):
        yield ListView(id="file-autocomplete-list")
    
    def on_mount(self):
        """Load all project files"""
        self.load_files()
        self.update_list()
        
    def load_files(self):
        """Scan project for files"""
        self.files = []
        for root, dirs, filenames in os.walk(self.root_path):
            # Skip hidden dirs and common ignore patterns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv']]
            for f in filenames:
                if not f.startswith('.') and not f.endswith('.pyc'):
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(self.root_path)
                    self.files.append(str(rel_path))
    
    def update_query(self, query: str):
        """Update search query and refresh list"""
        self.query = query
        self.selected_index = 0
        self.update_list()
    
    def update_list(self):
        """Update the displayed file list"""
        # Guard against calling before widget is mounted
        if not self.is_mounted:
            return
            
        try:
            list_view = self.query_one(ListView)
        except:
            return  # Widget not ready yet
            
        list_view.clear()
        
        # Fuzzy match
        query_lower = self.query.lower()
        if query_lower:
            matches = [f for f in self.files if query_lower in f.lower()]
        else:
            matches = self.files
        
        # Limit to 10 results
        self.filtered_files = matches[:10]
        
        for i, filepath in enumerate(self.filtered_files):
            item = ListItem(Label(filepath))
            if i == self.selected_index:
                item.add_class("selected")
            list_view.append(item)
    
    def move_selection(self, delta: int):
        """Move selection up or down"""
        if not self.filtered_files:
            return
        
        self.selected_index = (self.selected_index + delta) % len(self.filtered_files)
        
        # Update visual selection
        list_view = self.query_one(ListView)
        for i, item in enumerate(list_view.children):
            if i == self.selected_index:
                item.add_class("selected")
            else:
                item.remove_class("selected")
    
    def on_key(self, event) -> None:
        """Handle keyboard navigation in autocomplete"""
        if event.key == "down":
            self.move_selection(1)
            event.prevent_default()
            event.stop()
        elif event.key == "up":
            self.move_selection(-1)
            event.prevent_default()
            event.stop()
        elif event.key == "enter":
            self.select_current()
            event.prevent_default()
            event.stop()
        elif event.key == "escape":
            self.dismiss_autocomplete()
            event.prevent_default()
            event.stop()
    
    def select_current(self):
        """Select the currently highlighted file"""
        if self.filtered_files and 0 <= self.selected_index < len(self.filtered_files):
            selected_file = self.filtered_files[self.selected_index]
            self.post_message(self.FileSelected(selected_file))
    
    def dismiss_autocomplete(self):
        """Close autocomplete without selection"""
        self.post_message(self.Dismissed())

