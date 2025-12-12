"""
src/reactor/code_reactor.py

Main reactor implementation that orchestrates AST analysis and validation.
Implements the "Simple Actions, Smart Reactions" architecture.
"""

import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

from src.ast.core.ast_manager import ASTManager
from src.ast.core.base_parser import Language
from .config import ReactorConfig, get_default_config
from .validators import CompositeValidator
from .analyzers import DependencyAnalyzer, ImpactAnalyzer
from .auto_fixes import AutoFixer
from .feedback import FeedbackFormatter


class CodeReactor:
    """Automatically responds to file changes with AST analysis"""
    
    def __init__(self, config: Optional[ReactorConfig] = None, ast_manager: Optional[ASTManager] = None):
        self.config = config or get_default_config()
        self.ast_manager = ast_manager or ASTManager()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Register default parsers
        # Register default parsers
        
        # Python
        try:
            from src.ast.parsers.python_parser import PythonParser
            self.ast_manager.register_parser(Language.PYTHON, PythonParser())
        except ImportError:
            pass

        # JavaScript / TypeScript
        try:
            from src.ast.parsers.javascript_parser import JavaScriptASTParser
            js_parser = JavaScriptASTParser()
            self.ast_manager.register_parser(Language.JAVASCRIPT, js_parser)
            self.ast_manager.register_parser(Language.TYPESCRIPT, js_parser)
        except ImportError:
            pass

        # Java
        try:
            from src.ast.parsers.java_parser import JavaASTParser
            self.ast_manager.register_parser(Language.JAVA, JavaASTParser())
        except ImportError:
            pass

        # C++
        try:
            from src.ast.parsers.cpp_parser import CppParser
            self.ast_manager.register_parser(Language.CPP, CppParser())
        except ImportError:
            pass

        # Go
        try:
            from src.ast.parsers.go_parser import GoParser
            self.ast_manager.register_parser(Language.GO, GoParser())
        except ImportError:
            pass

        # Rust
        try:
            from src.ast.parsers.rust_parser import RustParser
            self.ast_manager.register_parser(Language.RUST, RustParser())
        except ImportError:
            pass

        # C#
        try:
            from src.ast.parsers.csharp_parser import CSharpParser
            self.ast_manager.register_parser(Language.CSHARP, CSharpParser())
        except ImportError:
            pass

        # Dart
        try:
            from src.ast.parsers.dart_parser import DartParser
            self.ast_manager.register_parser(Language.DART, DartParser())
        except ImportError:
            pass
        
        # Initialize components
        self.validator = CompositeValidator(self.ast_manager, self.config)
        self.dependency_analyzer = DependencyAnalyzer(self.ast_manager, self.config)
        self.impact_analyzer = ImpactAnalyzer(self.ast_manager, self.config)
        self.auto_fixer = AutoFixer(self.ast_manager, self.config)
        self.feedback_formatter = FeedbackFormatter(self.config)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Cache for previous file content (for impact analysis)
        self._content_cache: Dict[str, str] = {}
    
    async def on_file_written(self, file_path: str, content: str, operation: str = "write") -> Dict[str, Any]:
        """
        Triggered automatically when agent writes a file
        
        Args:
            file_path: Path to the file that was written
            content: New content of the file
            operation: Type of operation (write, modify, etc.)
            
        Returns:
            Formatted feedback for the agent
        """
        try:
            # Check if reactor is enabled
            if not self.config.is_enabled():
                return self.feedback_formatter.format_skipped_feedback(
                    file_path, "Reactor is disabled"
                )
            
            # Check if this is a code file we should process
            if not self._is_code_file(file_path):
                return self.feedback_formatter.format_skipped_feedback(
                    file_path, "Not a code file"
                )
            
            # Check file size
            if len(content.encode('utf-8')) > self.config.get_max_file_size_mb() * 1024 * 1024:
                return self.feedback_formatter.format_error_feedback(
                    file_path, f"File too large: exceeds {self.config.get_max_file_size_mb()}MB limit"
                )
            
            # Get previous content for impact analysis
            old_content = self._content_cache.get(file_path, "")
            
            # Run validation
            validation_result = await self.validator.validate(file_path, content)
            
            # Run impact analysis (if enabled)
            impact_result = None
            if self.config.should_track_dependencies() and old_content:
                impact_result = await self.impact_analyzer.assess_impact(
                    file_path, old_content, content
                )
            else:
                # Create empty impact result
                from .analyzers import AnalysisResult
                impact_result = AnalysisResult()
            
            # Apply auto-fixes (if enabled and validation passed)
            auto_fix_result = None
            if validation_result.is_valid and self.config.should_auto_fix_imports():
                auto_fix_result = await self.auto_fixer.apply_auto_fixes(
                    file_path, content, validation_result
                )
            else:
                # Create empty auto-fix result
                from .auto_fixes import AutoFixResult
                auto_fix_result = AutoFixResult()
            
            # Update content cache
            self._content_cache[file_path] = content
            
            # Format feedback based on verbosity
            if self.config.get_verbosity() == "minimal":
                return self.feedback_formatter.format_minimal_feedback(
                    file_path, validation_result, impact_result
                )
            elif self.config.get_verbosity() == "detailed":
                return self.feedback_formatter.format_detailed_feedback(
                    file_path, validation_result, impact_result, auto_fix_result, operation
                )
            else:
                # Standard verbosity
                return self.feedback_formatter.format_feedback(
                    file_path, validation_result, impact_result, auto_fix_result, operation
                )
                
        except Exception as e:
            self.logger.error(f"Error in reactor processing {file_path}: {str(e)}")
            return self.feedback_formatter.format_error_feedback(
                file_path, f"Reactor processing error: {str(e)}"
            )
    
    async def on_files_written(self, file_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process multiple file operations at once
        
        Args:
            file_operations: List of dicts with 'file_path', 'content', 'operation' keys
            
        Returns:
            Batch summary feedback
        """
        results = []
        
        for file_op in file_operations:
            result = await self.on_file_written(
                file_op.get('file_path', ''),
                file_op.get('content', ''),
                file_op.get('operation', 'write')
            )
            results.append(result)
        
        # Format batch summary
        from .feedback import ProgressFormatter
        progress_formatter = ProgressFormatter(self.config)
        return progress_formatter.format_batch_summary("batch_write", results)
    
    async def validate_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Validate a file without applying auto-fixes
        
        Args:
            file_path: Path to the file
            content: File content to validate
            
        Returns:
            Validation feedback
        """
        try:
            validation_result = await self.validator.validate(file_path, content)
            
            return {
                "status": "success",
                "file": file_path,
                "validation": self.feedback_formatter._format_validation(validation_result),
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
            
        except Exception as e:
            return self.feedback_formatter.format_error_feedback(
                file_path, f"Validation error: {str(e)}"
            )
    
    async def analyze_dependencies(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze dependencies for a file
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Dependency analysis feedback
        """
        try:
            dependencies = await self.dependency_analyzer.get_dependencies(file_path)
            dependents = await self.dependency_analyzer.find_dependents(file_path)
            
            return {
                "status": "success",
                "file": file_path,
                "dependencies": dependencies,
                "dependents": dependents,
                "dependency_count": len(dependencies),
                "dependent_count": len(dependents)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "file": file_path,
                "error": f"Dependency analysis error: {str(e)}"
            }
    
    async def get_project_analysis(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        Get analysis for multiple files in a project
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Project analysis feedback
        """
        try:
            dependency_graph = await self.dependency_analyzer.analyze_dependency_graph(file_paths)
            
            # Calculate project statistics
            total_files = len(file_paths)
            files_with_dependencies = sum(1 for info in dependency_graph.values() if info.get("dependency_count", 0) > 0)
            files_with_dependents = sum(1 for info in dependency_graph.values() if info.get("dependent_count", 0) > 0)
            
            return {
                "status": "success",
                "project_stats": {
                    "total_files": total_files,
                    "files_with_dependencies": files_with_dependencies,
                    "files_with_dependents": files_with_dependents,
                    "dependency_ratio": files_with_dependencies / total_files if total_files > 0 else 0
                },
                "dependency_graph": dependency_graph
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Project analysis error: {str(e)}"
            }
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file we should process"""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx',
            '.java', '.go', '.rs', '.cpp', '.c',
            '.cs', '.dart', '.php', '.rb', '.swift'
        }
        
        return Path(file_path).suffix.lower() in code_extensions
    
    def clear_cache(self):
        """Clear all caches"""
        self._content_cache.clear()
        self.ast_manager.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "content_cache_size": len(self._content_cache),
            "ast_cache_stats": self.ast_manager.get_cache_stats()
        }
    
    def update_config(self, new_config: ReactorConfig):
        """Update reactor configuration"""
        self.config = new_config
        
        # Reinitialize components with new config
        self.validator = CompositeValidator(self.ast_manager, self.config)
        self.dependency_analyzer = DependencyAnalyzer(self.ast_manager, self.config)
        self.impact_analyzer = ImpactAnalyzer(self.ast_manager, self.config)
        self.auto_fixer = AutoFixer(self.ast_manager, self.config)
        self.feedback_formatter = FeedbackFormatter(self.config)


# Global reactor instance
_global_reactor = None


def get_global_reactor() -> CodeReactor:
    """Get the global reactor instance"""
    global _global_reactor
    if _global_reactor is None:
        _global_reactor = CodeReactor()
    return _global_reactor


def set_global_reactor(reactor: CodeReactor):
    """Set the global reactor instance"""
    global _global_reactor
    _global_reactor = reactor