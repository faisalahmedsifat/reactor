"""
AST cache for performance optimization.
"""

try:
    from .performance_optimizer import PerformanceOptimizer
except ImportError:
    PerformanceOptimizer = None

__all__ = [
    'PerformanceOptimizer'
]