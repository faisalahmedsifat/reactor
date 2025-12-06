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
            content = ""
            encoding_used = "utf-8"
            
            # Simple binary check
            try:
                with open(path, "rb") as f:
                    chunk = f.read(1024)
                    if b"\0" in chunk:
                        self.update(Text(f"Binary file detected ({path.name}). Cannot display.", style="yellow"))
                        return
            except Exception:
                pass # Proceed to try text reading

            # Try UTF-8 first
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code = f.read()
            except UnicodeDecodeError:
                # Fallback to latin-1
                try:
                    encoding_used = "latin-1"
                    with open(path, "r", encoding="latin-1") as f:
                        code = f.read()
                except Exception as e:
                    self.update(Text(f"Error decoding file: {e}", style="red"))
                    return

            # Determine lexer from extension
            ext = path.suffix.lstrip(".") or "txt"
            
            # Add header to show encoding if not utf-8
            display_text = code
            
            syntax = Syntax(
                display_text,
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
