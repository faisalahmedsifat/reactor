"""
AST transformers for refactoring, documentation, and testing.
"""

try:
    from .refactoring_engine import RefactoringEngine
except ImportError:
    RefactoringEngine = None

try:
    from .documentation_gen import DocumentationGenerator
except ImportError:
    DocumentationGenerator = None

try:
    from .test_generator import TestGenerator
except ImportError:
    TestGenerator = None

__all__ = [
    'RefactoringEngine',
    'DocumentationGenerator', 
    'TestGenerator'
]