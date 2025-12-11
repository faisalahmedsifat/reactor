"""
src/tui/widgets/agent_editor_modal.py

Modal for creating and editing agent definitions.
"""

from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Input, TextArea, Button, Label, Static, Select
from textual.binding import Binding
from pathlib import Path


class AgentEditorModal(ModalScreen):
    """Modal for creating or editing agent definitions"""

    DEFAULT_BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
    ]

    def __init__(self, agent_name: str = None, edit_mode: bool = False):
        """
        Initialize agent editor modal.

        Args:
            agent_name: Name of agent to edit (for edit mode)
            edit_mode: True if editing existing agent, False for new agent
        """
        super().__init__()
        self.agent_name = agent_name
        self.edit_mode = edit_mode
        self.agent_data = None

        if edit_mode and agent_name:
            # Load existing agent
            from src.agents.loader import AgentLoader

            try:
                agent_config = AgentLoader.load_agent(agent_name)
                self.agent_data = {
                    "name": agent_config.name,
                    "description": agent_config.description,
                    "version": agent_config.version,
                    "author": agent_config.author or "",
                    "required_skills": agent_config.required_skills or [],
                    "preferred_tools": agent_config.preferred_tools or [],
                    "system_prompt": agent_config.system_prompt,
                }
            except Exception as e:
                self.agent_data = None

    def compose(self) -> ComposeResult:
        """Create the agent editor form"""
        title = "Edit Agent" if self.edit_mode else "Create New Agent"

        with Container(id="agent-editor-dialog"):
            yield Static(title, id="editor-title")

            with Vertical(id="editor-form"):
                # Name
                yield Label("Agent Name:")
                name_input = Input(
                    placeholder="e.g., web-researcher",
                    id="agent-name",
                    disabled=self.edit_mode,  # Can't change name in edit mode
                )
                if self.agent_data:
                    name_input.value = self.agent_data["name"]
                yield name_input

                # Description
                yield Label("Description:")
                desc_input = Input(
                    placeholder="Brief description of agent's purpose",
                    id="agent-description",
                )
                if self.agent_data:
                    desc_input.value = self.agent_data["description"]
                yield desc_input

                # Version
                yield Label("Version:")
                version_input = Input(placeholder="1.0", id="agent-version")
                if self.agent_data:
                    version_input.value = self.agent_data["version"]
                yield version_input

                # Author
                yield Label("Author (optional):")
                author_input = Input(placeholder="Your name", id="agent-author")
                if self.agent_data:
                    author_input.value = self.agent_data["author"]
                yield author_input

                # Required Skills
                yield Label("Required Skills (comma-separated):")
                skills_input = Input(
                    placeholder="e.g., web-search, data-analysis", id="agent-skills"
                )
                if self.agent_data:
                    skills_input.value = ", ".join(self.agent_data["required_skills"])
                yield skills_input

                # System Prompt
                yield Label("System Prompt (Markdown):")
                prompt_area = TextArea(id="agent-prompt", language="markdown")
                if self.agent_data:
                    prompt_area.text = self.agent_data["system_prompt"]
                else:
                    prompt_area.text = """# Agent Name

You are a specialized agent for...

## Capabilities
- Capability 1
- Capability 2

## Approach
1. Step 1
2. Step 2"""
                yield prompt_area

            # Buttons
            with Horizontal(id="editor-buttons"):
                yield Button("Save", variant="primary", id="save-button")
                yield Button("Cancel", variant="default", id="cancel-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self.save_agent()

    def save_agent(self) -> None:
        """Save the agent definition"""
        try:
            # Collect form data
            name = self.query_one("#agent-name", Input).value.strip()
            description = self.query_one("#agent-description", Input).value.strip()
            version = self.query_one("#agent-version", Input).value.strip() or "1.0"
            author = self.query_one("#agent-author", Input).value.strip()
            skills_raw = self.query_one("#agent-skills", Input).value.strip()
            system_prompt = self.query_one("#agent-prompt", TextArea).text.strip()

            # Validate
            if not name:
                self.app.notify("Agent name is required", severity="error")
                return

            if not description:
                self.app.notify("Description is required", severity="error")
                return

            if not system_prompt:
                self.app.notify(" System prompt is required", severity="error")
                return

            # Parse skills
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

            # Build markdown content
            frontmatter = f"""---
name: {name}
description: {description}
version: {version}"""

            if author:
                frontmatter += f"\nauthor: {author}"

            if skills:
                frontmatter += "\nrequired_skills:"
                for skill in skills:
                    frontmatter += f"\n  - {skill}"

            frontmatter += "\n---\n\n"

            full_content = frontmatter + system_prompt

            # Save to file
            agents_dir = Path.cwd() / ".reactor" / "agents"
            agents_dir.mkdir(parents=True, exist_ok=True)

            agent_file = agents_dir / f"{name}.md"
            agent_file.write_text(full_content, encoding="utf-8")

            # Reload agents
            from src.agents.loader import AgentLoader

            AgentLoader.discover_agents(force_refresh=True)

            action = "updated" if self.edit_mode else "created"
            self.dismiss({"name": name, "action": action, "file": str(agent_file)})

        except Exception as e:
            self.app.notify(f"Error saving agent: {str(e)}", severity="error")

    def action_dismiss(self) -> None:
        """Dismiss modal"""
        self.dismiss(None)


class AgentDetailModal(ModalScreen):
    """Modal for viewing agent details"""

    DEFAULT_BINDINGS = [
        Binding("escape", "dismiss", "Close"),
    ]

    def __init__(self, agent_name: str):
        super().__init__()
        self.agent_name = agent_name

        # Load agent
        from src.agents.loader import AgentLoader

        try:
            self.agent_config = AgentLoader.load_agent(agent_name)
        except Exception as e:
            self.agent_config = None
            self.error = str(e)

    def compose(self) -> ComposeResult:
        """Show agent details"""
        with Container(id="agent-detail-dialog"):
            if not self.agent_config:
                yield Static(f"Error loading agent: {self.error}", id="error-message")
                yield Button("Close", id="close-button")
                return

            yield Static(f"Agent: {self.agent_config.name}", id="detail-title")

            with Vertical(id="detail-content"):
                yield Static(f"**Description:** {self.agent_config.description}")
                yield Static(f"**Version:** {self.agent_config.version}")
                if self.agent_config.author:
                    yield Static(f"**Author:** {self.agent_config.author}")

                if self.agent_config.required_skills:
                    yield Static(
                        f"**Required Skills:** {', '.join(self.agent_config.required_skills)}"
                    )

                if self.agent_config.preferred_tools:
                    yield Static(
                        f"**Preferred Tools:** {', '.join(self.agent_config.preferred_tools)}"
                    )

                yield Static("\n**System Prompt:**")
                yield TextArea(
                    self.agent_config.system_prompt,
                    language="markdown",
                    read_only=True,
                    id="prompt-view",
                )

            with Horizontal(id="detail-buttons"):
                yield Button("Edit", variant="primary", id="edit-button")
                yield Button("Close", variant="default", id="close-button")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press"""
        if event.button.id == "close-button":
            self.dismiss(None)
        elif event.button.id == "edit-button":
            self.dismiss({"action": "edit", "agent_name": self.agent_name})

    def action_dismiss(self) -> None:
        """Dismiss modal"""
        self.dismiss(None)
