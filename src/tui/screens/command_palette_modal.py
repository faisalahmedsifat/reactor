from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem, Label
from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message


class CommandPalette(ModalScreen):
    """Command palette modal"""

    class Selected(Message):
        """Command selected message"""

        def __init__(self, action: str):
            self.action = action
            super().__init__()

    COMMANDS = {
        "Toggle File Sidebar": "toggle_sidebar",
        "Toggle Context Panel": "toggle_context",
        "Find File": "fuzzy_find",
        "Clear Logs": "clear_logs",
        "Quit": "quit",
    }

    def compose(self) -> ComposeResult:
        with Container(id="fuzzy-container"):
            yield Label("Command Palette", id="fuzzy-title")
            yield Input(placeholder="> Type a command...", id="cmd-input")
            yield ListView(id="cmd-list")

    def on_mount(self) -> None:
        self.update_list("")
        self.query_one(Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.update_list(event.value)

    def update_list(self, query: str) -> None:
        list_view = self.query_one(ListView)
        list_view.clear()

        query = query.lower()
        for name, action in self.COMMANDS.items():
            if query in name.lower():
                list_view.append(ListItem(Label(name), name=action))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item and event.item.name:
            self.post_message(self.Selected(event.item.name))
            self.dismiss()
