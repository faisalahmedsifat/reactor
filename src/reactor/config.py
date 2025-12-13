"""
src/reactor/config.py

Configuration management for the reactor system.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml
import json


class ReactorConfig:
    """Configuration for the reactor system"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = self._load_default_config()

        if config_path:
            self._load_config_file(config_path)

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        return {
            "enabled": True,
            "validation": {
                "syntax_check": True,
                "import_check": True,
                "type_check": False,  # Optional - can be slow
            },
            "analysis": {
                "track_dependencies": True,
                "detect_breaking_changes": True,
                "analyze_complexity": False,
            },
            "auto_fixes": {
                "fix_imports": True,
                "remove_unused_imports": True,
                "format_code": False,  # Let agent control formatting
            },
            "feedback": {
                "verbosity": "standard",  # minimal, standard, detailed
                "include_suggestions": True,
                "max_suggestions": 5,
            },
            "cache": {
                "enabled": True,
                "max_size": 1000,
                "ttl_seconds": 3600,
            },
            "performance": {
                "max_file_size_mb": 10,
                "timeout_seconds": 30,
                "parallel_processing": True,
            },
        }

    def _load_config_file(self, config_path: str):
        """Load configuration from file"""
        try:
            path = Path(config_path)
            if not path.exists():
                return

            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() in [".yaml", ".yml"]:
                    file_config = yaml.safe_load(f)
                elif path.suffix.lower() == ".json":
                    file_config = json.load(f)
                else:
                    return

            # Merge with default config
            self._merge_config(self.config, file_config)

        except Exception:
            # If config file fails to load, use defaults
            pass

    def _merge_config(self, default: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries"""
        for key, value in override.items():
            if (
                key in default
                and isinstance(default[key], dict)
                and isinstance(value, dict)
            ):
                self._merge_config(default[key], value)
            else:
                default[key] = value

    def get(self, key_path: str, default=None):
        """Get configuration value using dot notation"""
        keys = key_path.split(".")
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key_path.split(".")
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def is_enabled(self) -> bool:
        """Check if reactor is enabled"""
        return bool(self.get("enabled", True))

    def should_validate_syntax(self) -> bool:
        """Check if syntax validation is enabled"""
        return bool(self.get("validation.syntax_check", True))

    def should_validate_imports(self) -> bool:
        """Check if import validation is enabled"""
        return bool(self.get("validation.import_check", True))

    def should_track_dependencies(self) -> bool:
        """Check if dependency tracking is enabled"""
        return bool(self.get("analysis.track_dependencies", True))

    def should_detect_breaking_changes(self) -> bool:
        """Check if breaking change detection is enabled"""
        return bool(self.get("analysis.detect_breaking_changes", True))

    def should_auto_fix_imports(self) -> bool:
        """Check if auto-fix for imports is enabled"""
        return bool(self.get("auto_fixes.fix_imports", True))

    def should_remove_unused_imports(self) -> bool:
        """Check if unused import removal is enabled"""
        return bool(self.get("auto_fixes.remove_unused_imports", True))

    def get_verbosity(self) -> str:
        """Get feedback verbosity level"""
        return str(self.get("feedback.verbosity", "standard"))

    def get_max_suggestions(self) -> int:
        """Get maximum number of suggestions to provide"""
        return int(self.get("feedback.max_suggestions", 5))

    def get_max_file_size_mb(self) -> int:
        """Get maximum file size to process in MB"""
        return int(self.get("performance.max_file_size_mb", 10))

    def get_timeout_seconds(self) -> int:
        """Get timeout for operations in seconds"""
        return int(self.get("performance.timeout_seconds", 30))

    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled"""
        return bool(self.get("cache.enabled", True))

    def get_cache_max_size(self) -> int:
        """Get maximum cache size"""
        return int(self.get("cache.max_size", 1000))

    def get_cache_ttl_seconds(self) -> int:
        """Get cache TTL in seconds"""
        return int(self.get("cache.ttl_seconds", 3600))

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return self.config.copy()

    def save_to_file(self, config_path: str):
        """Save configuration to file"""
        path = Path(config_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            if path.suffix.lower() in [".yaml", ".yml"]:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            elif path.suffix.lower() == ".json":
                json.dump(self.config, f, indent=2)
            else:
                raise ValueError(f"Unsupported config file format: {path.suffix}")


# Global configuration instance
_default_config = None


def get_default_config() -> ReactorConfig:
    """Get the default configuration instance"""
    global _default_config
    if _default_config is None:
        _default_config = ReactorConfig()
    return _default_config


def set_default_config(config: ReactorConfig):
    """Set the default configuration instance"""
    global _default_config
    _default_config = config
