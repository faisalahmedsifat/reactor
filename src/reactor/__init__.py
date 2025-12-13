"""
src/reactor

Automatic AST analysis and validation for file operations.
Implements the "Simple Actions, Smart Reactions" architecture.
"""

from .code_reactor import CodeReactor
from .config import ReactorConfig
from .validators import SyntaxValidator, ImportValidator
from .analyzers import DependencyAnalyzer, ImpactAnalyzer
from .auto_fixes import AutoFixer
from .feedback import FeedbackFormatter

__all__ = [
    "CodeReactor",
    "ReactorConfig",
    "SyntaxValidator",
    "ImportValidator",
    "DependencyAnalyzer",
    "ImpactAnalyzer",
    "AutoFixer",
    "FeedbackFormatter",
]
