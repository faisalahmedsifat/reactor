"""
src/tui/widgets/active_agents.py

Sidebar widget to display and select active background agents.
"""

from textual.widgets import Static, OptionList
from textual.app import ComposeResult
from textual import work
from textual.message import Message
from typing import List, Dict

from src.agents.manager import AgentManager


class ActiveAgents(Static):
    """Sidebar list of active agents"""

    class AgentSelected(Message):
        """Emitted when an agent (or Main) is selected"""

        def __init__(self, agent_id: str):
            self.agent_id = agent_id
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Static("Active Agents", classes="panel-header")
        yield OptionList(id="agent-list")

    def on_mount(self) -> None:
        """Start polling and set initial state"""
        self.update_agents()
        self.set_interval(2.0, self.update_agents)  # Poll every 2s

    def update_agents(self) -> None:
        """Refreshes the agent list from AgentManager"""
        manager = AgentManager()
        agents = manager.list_agents()

        # Get OptionList
        opt_list = self.query_one(OptionList)

        # We want to preserve selection if possible, but OptionList
        # is tricky to update in-place without clearing.
        # For an MVP, we will only add new ones or rebuild if count changes
        # to avoid flickering.
        # Actually, let's just rebuild "Main" + Agents every time for safety
        # but check if changed to avoid unnecessary renders.

        # Current items format: ["Main Thread", "Agent X (...)"]

        new_items = ["Main Thread"]
        self.agent_ids = ["main"]  # Mapping index -> ID

        for agent in agents:
            # Format: "Web Researcher (running)"
            status_icon = (
                "🟢"
                if agent["state"] == "running"
                else "🔴" if agent["state"] == "error" else "⚪"
            )
            label = f"{status_icon} {agent['name']} ({agent['state']})"
            new_items.append(label)
            self.agent_ids.append(agent["id"])

        # If content differs, update.
        # OptionList doesn't verify content equality easily, allowing rebuild for now.
        # To prevent flickering, we could check if list of strings matches exactly.

        # Hacky check:
        # We can't easily read OptionList content back.
        # We'll just clear and add if we suspect change, or just do it.
        # Textual's OptionList.clear() + add_options() is fast enough usually.

        # However, clearing resets selection. That's bad.
        # We need to track the SELECTED ID.
        selected_idx = opt_list.highlighted
        selected_id = "main"
        if selected_idx is not None and selected_idx < len(self.agent_ids):
            selected_id = self.agent_ids[selected_idx]

        # Rebuild
        opt_list.clear_options()
        opt_list.add_options(new_items)

        # Restore selection
        try:
            new_idx = self.agent_ids.index(selected_id)
            opt_list.highlighted = new_idx
        except ValueError:
            opt_list.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection"""
        if event.option_index is None:
            return

        idx = event.option_index
        if idx < len(self.agent_ids):
            agent_id = self.agent_ids[idx]
            self.post_message(self.AgentSelected(agent_id))
