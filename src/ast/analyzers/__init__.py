"""
AST analyzers for code quality, security, and architecture.
"""

try:
    from .security_analyzer import SecurityAnalyzer
except ImportError:
    SecurityAnalyzer = None

try:
    from .code_quality_analyzer import CodeQualityAnalyzer
except ImportError:
    CodeQualityAnalyzer = None

try:
    from .architecture_analyzer import ArchitectureAnalyzer
except ImportError:
    ArchitectureAnalyzer = None

__all__ = [
    'SecurityAnalyzer',
    'CodeQualityAnalyzer', 
    'ArchitectureAnalyzer'
]