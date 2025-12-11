"""
Centralized prompt management system.
All system prompts stored in YAML files and loaded dynamically with hot reload capability.
"""

from pathlib import Path
from typing import Dict, Optional
import yaml

PROMPTS_DIR = Path(__file__).parent


class PromptManager:
    """Centralized prompt management with caching and hot reload"""

    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._cache: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load all YAML prompt files into cache"""
        self._cache.clear()
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._flatten_dict(data, self._cache)

    def _flatten_dict(self, d: dict, cache: dict, prefix: str = ""):
        """Flatten nested dict into dot-notation keys"""
        for key, value in d.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_dict(value, cache, full_key)
            else:
                cache[full_key] = value

    def get(self, key: str, **kwargs) -> str:
        """
        Get prompt with optional variable substitution.

        Args:
            key: Dot-notation key (e.g., "thinking.system", "agent.system")
            **kwargs: Variables to format into the prompt template

        Returns:
            Formatted prompt string

        Raises:
            KeyError: If prompt key not found
        """
        if key not in self._cache:
            available = ", ".join(self._cache.keys())
            raise KeyError(f"Prompt '{key}' not found. Available: {available}")

        prompt = self._cache[key]

        # Substitute variables if provided
        if kwargs:
            return prompt.format(**kwargs)
        return prompt

    def reload(self):
        """Reload prompts from disk (hot reload)"""
        self._load_prompts()

    def list_prompts(self) -> list:
        """List all available prompt keys"""
        return list(self._cache.keys())


# Global singleton instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get singleton PromptManager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_prompt(key: str, **kwargs) -> str:
    """
    Convenience function to get prompt by key.

    Args:
        key: Dot-notation key (e.g., "thinking.system")
        **kwargs: Variables to format into the prompt

    Returns:
        Formatted prompt string
    """
    return get_prompt_manager().get(key, **kwargs)


def reload_prompts():
    """Reload all prompts from disk (hot reload)"""
    pm = get_prompt_manager()
    pm.reload()
    return f"Reloaded {len(pm.list_prompts())} prompts"


def get_agent_prompt(agent_name: str) -> str:
    """
    Load agent system prompt from .reactor/agents/

    Args:
        agent_name: Name of the agent to load

    Returns:
        Agent's system prompt content
    """
    from src.agents.loader import AgentLoader

    agent_config = AgentLoader.load_agent(agent_name)
    return agent_config.system_prompt


def get_skill_instructions(skill_names: list[str]) -> str:
    """
    Load and merge skill instructions from .reactor/skills/

    Args:
        skill_names: List of skill names to load

    Returns:
        Combined skill instructions
    """
    from src.skills.loader import SkillLoader

    if not skill_names:
        return ""

    skills = SkillLoader.load_multiple_skills(skill_names)
    instructions = []

    for skill in skills:
        instructions.append(f"## Skill: {skill.name}\n\n{skill.instructions}")

    return "\n\n".join(instructions)


def compose_prompt(
    base_prompt: str,
    agent_name: Optional[str] = None,
    skill_names: Optional[list[str]] = None,
) -> str:
    """
    Compose final system prompt by merging base prompt with agent and skills.

    Args:
        base_prompt: The base system prompt (thinking or agent)
        agent_name: Optional agent name to load custom prompt
        skill_names: Optional list of skill names for additional context

    Returns:
        Composed system prompt
    """
    parts = [base_prompt]

    # Add agent-specific prompt
    if agent_name:
        try:
            agent_prompt = get_agent_prompt(agent_name)
            parts.append(f"\n\n# AGENT ROLE: {agent_name.upper()}\n\n{agent_prompt}")
        except Exception as e:
            print(f"Warning: Failed to load agent '{agent_name}': {e}")

    # Add skill instructions
    if skill_names:
        try:
            skill_instructions = get_skill_instructions(skill_names)
            if skill_instructions:
                parts.append(f"\n\n# ACTIVE SKILLS\n\n{skill_instructions}")
        except Exception as e:
            print(f"Warning: Failed to load skills: {e}")

    # CRITICAL: Append runtime enforcement to the VERY END to override any agent-specific hallucinations
    parts.append(
        """
# ⚠️ REAL-TIME ENFORCEMENT ⚠️
1. **TOOL USE MANDATE**: You MUST use the actual tool functions (e.g., `execute_shell_command`).
2. **NO TEXT HALLUCINATION**: Do NOT write code blocks like `file_tools.read_file(...)`. calls must be creating using the Tool binding.
3. **ACT NOW**: If you need to do something, CALL THE TOOL IMMEDIATELY. Do not just "plan" to do it.
"""
    )

    return "\n".join(parts)
