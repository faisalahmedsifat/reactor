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
            with open(yaml_file, 'r', encoding='utf-8') as f:
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
