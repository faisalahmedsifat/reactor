"""
TODO Panel widget for displaying agent's TODO tasks
"""
from textual.widgets import Static
from textual.containers import VerticalScroll
from rich.table import Table
from rich.text import Text


class TODOPanel(VerticalScroll):
    """Panel to display TODO tasks from the agent"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.todos = []
    
    def update_todos(self, todos: list):
        """Update the TODO list"""
        self.todos = todos
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the TODO display"""
        self.remove_children()
        
        if not self.todos:
            self.mount(Static("[dim]No tasks yet[/]"))
            return
        
        # Create table
        table = Table(show_header=True, header_style="bold cyan", expand=True)
        table.add_column("Status", width=8)
        table.add_column("Task", ratio=1)
        table.add_column("Created", width=16)
        
        for todo in self.todos:
            status = "✅" if todo['status'] == 'completed' else "⏳"
            title = todo['title']
            created = todo['created_at'][:16].replace('T', ' ')
            
            style = "dim" if todo['status'] == 'completed' else ""
            
            table.add_row(
                Text(status),
                Text(title, style=style),
                Text(created, style="dim")
            )
        
        self.mount(Static(table))
