"""
src/agents/loader.py

Agent loader for discovering and loading agent definitions from .md files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class AgentConfig:
    """Agent configuration parsed from markdown file"""

    name: str
    description: str
    version: str
    author: Optional[str] = None
    system_prompt: str = ""
    required_skills: List[str] = None
    preferred_tools: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.required_skills is None:
            self.required_skills = []
        if self.preferred_tools is None:
            self.preferred_tools = []
        if self.metadata is None:
            self.metadata = {}


class AgentLoader:
    """Discover and load agent definitions from .reactor/agents/"""

    _cache: Dict[str, AgentConfig] = {}
    _discovered: bool = False

    @classmethod
    def discover_agents(cls, force_refresh: bool = False) -> List[str]:
        """
        Discover all available agents from project and user directories.

        Returns:
            List of agent names
        """
        if cls._discovered and not force_refresh:
            return list(cls._cache.keys())

        cls._cache.clear()
        agent_paths = cls._get_agent_paths()

        for agent_path in agent_paths:
            if agent_path.exists() and agent_path.is_dir():
                for md_file in agent_path.glob("*.md"):
                    try:
                        agent = cls._load_agent_file(md_file)
                        # Project-level agents override user-level
                        if agent.name not in cls._cache or str(md_file).startswith(
                            os.getcwd()
                        ):
                            cls._cache[agent.name] = agent
                    except Exception as e:
                        print(f"Warning: Failed to load agent {md_file}: {e}")

        cls._discovered = True
        return list(cls._cache.keys())

    @classmethod
    def load_agent(cls, agent_name: str) -> AgentConfig:
        """
        Load specific agent by name.

        Args:
            agent_name: Name of the agent to load

        Returns:
            AgentConfig object

        Raises:
            ValueError: If agent not found
        """
        # Ensure discovery has run
        if not cls._discovered:
            cls.discover_agents()

        if agent_name not in cls._cache:
            raise ValueError(
                f"Agent '{agent_name}' not found. Available agents: {', '.join(cls._cache.keys())}"
            )

        return cls._cache[agent_name]

    @classmethod
    def list_agents(cls) -> List[Dict[str, str]]:
        """
        List all available agents with metadata.

        Returns:
            List of dicts with agent info
        """
        cls.discover_agents()
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "author": agent.author or "Unknown",
            }
            for agent in cls._cache.values()
        ]

    @classmethod
    def _get_agent_paths(cls) -> List[Path]:
        """Get list of paths to search for agents (user and project level)"""
        paths = []

        # User-level: ~/.reactor/agents/
        user_path = Path.home() / ".reactor" / "agents"
        paths.append(user_path)

        # Project-level: .reactor/agents/
        project_path = Path.cwd() / ".reactor" / "agents"
        paths.append(project_path)

        return paths

    @classmethod
    def _load_agent_file(cls, file_path: Path) -> AgentConfig:
        """
        Load agent from markdown file with YAML frontmatter.

        Args:
            file_path: Path to .md file

        Returns:
            AgentConfig object
        """
        content = file_path.read_text(encoding="utf-8")

        # Parse frontmatter and content
        frontmatter, markdown_content = cls._parse_markdown_frontmatter(content)

        # Validate required fields
        if "name" not in frontmatter:
            raise ValueError(
                f"Agent file {file_path} missing 'name' field in frontmatter"
            )
        if "description" not in frontmatter:
            raise ValueError(
                f"Agent file {file_path} missing 'description' field in frontmatter"
            )

        # Build AgentConfig
        return AgentConfig(
            name=frontmatter["name"],
            description=frontmatter["description"],
            version=frontmatter.get("version", "1.0"),
            author=frontmatter.get("author"),
            system_prompt=markdown_content.strip(),
            required_skills=frontmatter.get("required_skills", []),
            preferred_tools=frontmatter.get("preferred_tools", []),
            metadata=frontmatter,
        )

    @staticmethod
    def _parse_markdown_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from markdown content.

        Format:
        ---
        key: value
        ---

        Markdown content here

        Returns:
            (frontmatter_dict, markdown_content)
        """
        # Match YAML frontmatter
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            # No frontmatter, treat entire content as markdown
            return {}, content

        frontmatter_yaml = match.group(1)
        markdown_content = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_yaml) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in frontmatter: {e}")

        return frontmatter, markdown_content
