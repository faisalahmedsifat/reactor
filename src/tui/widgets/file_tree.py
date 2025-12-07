from textual.widgets import DirectoryTree
from textual.binding import Binding
from pathlib import Path


class FileExplorer(DirectoryTree):
    """Sidebar file explorer widget"""

    BINDINGS = [
        Binding("enter", "select_file", "Open File", priority=True),
    ]

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Propagate file selection to parent/app"""
        # The parent or app will handle the event
        pass
