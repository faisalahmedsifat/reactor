from textual.widgets import DirectoryTree
from textual.binding import Binding


class FileExplorer(DirectoryTree):
    """Sidebar file explorer widget"""

    BINDINGS = [
        Binding("enter", "select_file", "Open File", priority=True),
    ]
