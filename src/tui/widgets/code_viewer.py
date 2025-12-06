from textual.widgets import Static
from rich.syntax import Syntax
from rich.text import Text
from pathlib import Path
from typing import Optional

class CodeViewer(Static):
    """Widget to display code with syntax highlighting"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_path: Optional[Path] = None

    def load_file(self, path: Path) -> None:
        """Load and display a file"""
        self.current_path = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = f.read()
            
            # Determine lexer from extension
            ext = path.suffix.lstrip(".") or "txt"
            
            syntax = Syntax(
                code,
                lexer=ext,
                theme="monokai",
                line_numbers=True,
                word_wrap=False
            )
            self.update(syntax)
            
        except Exception as e:
            self.update(Text(f"Error loading file: {e}", style="red"))

    def clear_viewer(self) -> None:
        """Clear the view"""
        self.current_path = None
        self.update("")
