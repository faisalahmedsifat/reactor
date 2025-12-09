"""
src/skills/loader.py

Skill loader for discovering and loading skill definitions from .md files.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re


@dataclass
class SkillConfig:
    """Skill configuration parsed from markdown file"""
    name: str
    description: str
    version: str
    author: Optional[str] = None
    instructions: str = ""
    allowed_tools: List[str] = None
    working_patterns: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.allowed_tools is None:
            self.allowed_tools = []
        if self.working_patterns is None:
            self.working_patterns = []
        if self.metadata is None:
            self.metadata = {}


class SkillLoader:
    """Discover and load skill definitions from .reactor/skills/"""
    
    _cache: Dict[str, SkillConfig] = {}
    _discovered: bool = False
    
    @classmethod
    def discover_skills(cls, force_refresh: bool = False) -> List[str]:
        """
        Discover all available skills from project and user directories.
        
        Returns:
            List of skill names
        """
        if cls._discovered and not force_refresh:
            return list(cls._cache.keys())
        
        cls._cache.clear()
        skill_paths = cls._get_skill_paths()
        
        for skill_path in skill_paths:
            if skill_path.exists() and skill_path.is_dir():
                for md_file in skill_path.glob("*.md"):
                    try:
                        skill = cls._load_skill_file(md_file)
                        # Project-level skills override user-level
                        if skill.name not in cls._cache or str(md_file).startswith(os.getcwd()):
                            cls._cache[skill.name] = skill
                    except Exception as e:
                        print(f"Warning: Failed to load skill {md_file}: {e}")
        
        cls._discovered = True
        return list(cls._cache.keys())
    
    @classmethod
    def load_skill(cls, skill_name: str) -> SkillConfig:
        """
        Load specific skill by name.
        
        Args:
            skill_name: Name of the skill to load
            
        Returns:
            SkillConfig object
            
        Raises:
            ValueError: If skill not found
        """
        # Ensure discovery has run
        if not cls._discovered:
            cls.discover_skills()
        
        if skill_name not in cls._cache:
            raise ValueError(
                f"Skill '{skill_name}' not found. Available skills: {', '.join(cls._cache.keys())}"
            )
        
        return cls._cache[skill_name]
    
    @classmethod
    def load_multiple_skills(cls, skill_names: List[str]) -> List[SkillConfig]:
        """
        Load multiple skills by name.
        
        Args:
            skill_names: List of skill names
            
        Returns:
            List of SkillConfig objects
        """
        return [cls.load_skill(name) for name in skill_names]
    
    @classmethod
    def list_skills(cls) -> List[Dict[str, str]]:
        """
        List all available skills with metadata.
        
        Returns:
            List of dicts with skill info
        """
        cls.discover_skills()
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "version": skill.version,
                "author": skill.author or "Unknown",
            }
            for skill in cls._cache.values()
        ]
    
    @classmethod
    def _get_skill_paths(cls) -> List[Path]:
        """Get list of paths to search for skills (user and project level)"""
        paths = []
        
        # User-level: ~/.reactor/skills/
        user_path = Path.home() / ".reactor" / "skills"
        paths.append(user_path)
        
        # Project-level: .reactor/skills/
        project_path = Path.cwd() / ".reactor" / "skills"
        paths.append(project_path)
        
        return paths
    
    @classmethod
    def _load_skill_file(cls, file_path: Path) -> SkillConfig:
        """
        Load skill from markdown file with YAML frontmatter.
        
        Args:
            file_path: Path to .md file
            
        Returns:
            SkillConfig object
        """
        content = file_path.read_text(encoding="utf-8")
        
        # Parse frontmatter and content
        frontmatter, markdown_content = cls._parse_markdown_frontmatter(content)
        
        # Validate required fields
        if "name" not in frontmatter:
            raise ValueError(f"Skill file {file_path} missing 'name' field in frontmatter")
        if "description" not in frontmatter:
            raise ValueError(f"Skill file {file_path} missing 'description' field in frontmatter")
        
        # Build SkillConfig
        return SkillConfig(
            name=frontmatter["name"],
            description=frontmatter["description"],
            version=frontmatter.get("version", "1.0"),
            author=frontmatter.get("author"),
            instructions=markdown_content.strip(),
            allowed_tools=frontmatter.get("allowed_tools", []),
            working_patterns=frontmatter.get("working_patterns", []),
            metadata=frontmatter,
        )
    
    @staticmethod
    def _parse_markdown_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        """
        Parse YAML frontmatter from markdown content.
        
        Returns:
            (frontmatter_dict, markdown_content)
        """
        # Match YAML frontmatter
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
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
