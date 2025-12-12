"""
src/reactor/analyzers.py

Dependency analysis and impact assessment components.
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from pathlib import Path
import difflib

from src.ast.core.ast_manager import ASTManager
from src.ast.core.base_parser import Language, Function, Class, Import
from .config import ReactorConfig


class AnalysisResult:
    """Result of analysis operation"""
    
    def __init__(self):
        self.success = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.details: Dict[str, Any] = {}


class DependencyAnalyzer:
    """Analyzes dependencies between files"""
    
    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config
        self._dependency_cache: Dict[str, List[str]] = {}
    
    async def find_dependents(self, file_path: str) -> List[str]:
        """
        Find files that depend on the given file
        
        Args:
            file_path: Path to the file to find dependents for
            
        Returns:
            List of file paths that depend on this file
        """
        try:
            # Get the module name from file path
            module_name = self._get_module_name_from_path(file_path)
            if not module_name:
                return []
            
            # Search for files that import this module
            dependents = []
            
            # Get all Python files in the project
            project_files = await self._get_project_files()
            
            # Check each file for imports
            for candidate_file in project_files:
                if candidate_file == file_path:
                    continue
                
                imports = await self.ast_manager.extract_imports_from_file(candidate_file)
                for import_name in imports:
                    if self._is_import_of_module(import_name, module_name, file_path):
                        dependents.append(candidate_file)
                        break
            
            return dependents
            
        except Exception as e:
            return []
    
    async def get_dependencies(self, file_path: str) -> List[str]:
        """
        Get files that this file depends on
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            List of file paths that this file depends on
        """
        try:
            if file_path in self._dependency_cache:
                return self._dependency_cache[file_path]
            
            dependencies = []
            imports = await self.ast_manager.extract_imports_from_file(file_path)
            
            for import_name in imports:
                dep_file = await self._resolve_import_to_file(import_name, file_path)
                if dep_file:
                    dependencies.append(dep_file)
            
            # Cache the result
            self._dependency_cache[file_path] = dependencies
            return dependencies
            
        except Exception as e:
            return []
    
    async def analyze_dependency_graph(self, file_paths: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze the dependency graph for multiple files
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with dependency information for each file
        """
        graph = {}
        
        for file_path in file_paths:
            try:
                dependencies = await self.get_dependencies(file_path)
                dependents = await self.find_dependents(file_path)
                
                graph[file_path] = {
                    "dependencies": dependencies,
                    "dependents": dependents,
                    "dependency_count": len(dependencies),
                    "dependent_count": len(dependents),
                    "is_leaf": len(dependents) == 0,
                    "is_root": len(dependencies) == 0
                }
            except Exception as e:
                graph[file_path] = {
                    "error": str(e),
                    "dependencies": [],
                    "dependents": [],
                    "dependency_count": 0,
                    "dependent_count": 0,
                    "is_leaf": True,
                    "is_root": True
                }
        
        return graph
    
    def _get_module_name_from_path(self, file_path: str) -> Optional[str]:
        """Extract module name from file path"""
        try:
            path = Path(file_path)
            if path.suffix != '.py':
                return None
            
            # Remove .py extension
            module_path = path.with_suffix('')
            
            # Convert path separators to dots
            module_name = str(module_path).replace('/', '.').replace('\\', '.')
            
            return module_name
        except Exception:
            return None
    
    async def _get_project_files(self) -> List[str]:
        """Get all Python files in the project"""
        try:
            # For now, just return files in current directory and subdirectories
            # In a real implementation, this would be more sophisticated
            import os
            python_files = []
            
            for root, dirs, files in os.walk('.'):
                # Skip common ignore directories
                dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', '.venv']]
                
                for file in files:
                    if file.endswith('.py'):
                        python_files.append(str(Path(root) / file))
            
            return python_files
        except Exception:
            return []
    
    def _is_import_of_module(self, import_name: str, module_name: str, file_path: str) -> bool:
        """Check if an import statement refers to the given module"""
        # Simple check - in a real implementation this would be more sophisticated
        return import_name.startswith(module_name) or import_name == module_name
    
    async def _resolve_import_to_file(self, import_name: str, source_file: str) -> Optional[str]:
        """Resolve import name to actual file path"""
        try:
            # This is a simplified implementation
            # In a real implementation, this would handle relative imports,
            # package resolution, etc.
            
            parts = import_name.split('.')
            source_dir = Path(source_file).parent
            
            # Try to find the module file
            current_path = source_dir
            for part in parts:
                py_file = current_path / f"{part}.py"
                init_file = current_path / part / "__init__.py"
                
                if py_file.exists():
                    current_path = py_file.parent
                    return str(py_file)
                elif init_file.exists():
                    current_path = init_file.parent
                    return str(init_file)
                else:
                    current_path = current_path / part
            
            return None
        except Exception:
            return None


class ImpactAnalyzer:
    """Analyzes the impact of code changes"""
    
    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config
        self.dependency_analyzer = DependencyAnalyzer(ast_manager, config)
    
    async def assess_impact(self, file_path: str, old_content: str, new_content: str) -> AnalysisResult:
        """
        Assess the impact of changes to a file
        
        Args:
            file_path: Path to the file that was changed
            old_content: Previous content of the file
            new_content: New content of the file
            
        Returns:
            AnalysisResult with impact assessment
        """
        result = AnalysisResult()
        
        try:
            # Parse both old and new content
            old_ast = await self.ast_manager.parse_file(file_path)
            new_ast = await self.ast_manager.parse_file(file_path)
            
            if not old_ast.success or not new_ast.success:
                result.success = False
                result.errors.append("Could not parse file for impact analysis")
                return result
            
            # Analyze changes
            breaking_changes = await self._detect_breaking_changes(old_ast, new_ast)
            api_changes = await self._detect_api_changes(old_ast, new_ast)
            removed_items = await self._detect_removed_items(old_ast, new_ast)
            
            # Find affected files
            affected_files = await self.dependency_analyzer.find_dependents(file_path)
            
            # Categorize impact
            impact_level = self._categorize_impact(breaking_changes, api_changes, affected_files)
            
            result.details.update({
                "breaking_changes": breaking_changes,
                "api_changes": api_changes,
                "removed_items": removed_items,
                "affected_files": affected_files,
                "impact_level": impact_level,
                "affected_file_count": len(affected_files)
            })
            
            # Add warnings for breaking changes
            if breaking_changes:
                result.warnings.append(f"Breaking changes detected: {len(breaking_changes)} items")
            
            if affected_files:
                result.warnings.append(f"Changes affect {len(affected_files)} dependent files")
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Impact analysis error: {str(e)}")
        
        return result
    
    async def _detect_breaking_changes(self, old_ast, new_ast) -> List[Dict[str, Any]]:
        """Detect breaking changes between old and new AST"""
        breaking_changes = []
        
        try:
            # Get functions and classes from both versions
            old_functions = {f.name: f for f in (old_ast.functions or [])}
            new_functions = {f.name: f for f in (new_ast.functions or [])}
            
            old_classes = {c.name: c for c in (old_ast.classes or [])}
            new_classes = {c.name: c for c in (new_ast.classes or [])}
            
            # Check for removed functions
            for func_name, old_func in old_functions.items():
                if func_name not in new_functions:
                    breaking_changes.append({
                        "type": "removed_function",
                        "name": func_name,
                        "line_number": old_func.line_number,
                        "description": f"Function '{func_name}' was removed"
                    })
                else:
                    # Check for signature changes
                    new_func = new_functions[func_name]
                    if self._function_signature_changed(old_func, new_func):
                        breaking_changes.append({
                            "type": "changed_function_signature",
                            "name": func_name,
                            "line_number": new_func.line_number,
                            "description": f"Function '{func_name}' signature changed"
                        })
            
            # Check for removed classes
            for class_name, old_class in old_classes.items():
                if class_name not in new_classes:
                    breaking_changes.append({
                        "type": "removed_class",
                        "name": class_name,
                        "line_number": old_class.line_number,
                        "description": f"Class '{class_name}' was removed"
                    })
            
        except Exception as e:
            breaking_changes.append({
                "type": "analysis_error",
                "description": f"Error detecting breaking changes: {str(e)}"
            })
        
        return breaking_changes
    
    async def _detect_api_changes(self, old_ast, new_ast) -> List[Dict[str, Any]]:
        """Detect API changes (non-breaking but potentially impactful)"""
        api_changes = []
        
        try:
            # Get functions and classes from both versions
            old_functions = {f.name: f for f in (old_ast.functions or [])}
            new_functions = {f.name: f for f in (new_ast.functions or [])}
            
            old_classes = {c.name: c for c in (old_ast.classes or [])}
            new_classes = {c.name: c for c in (new_ast.classes or [])}
            
            # Check for added functions
            for func_name, new_func in new_functions.items():
                if func_name not in old_functions:
                    api_changes.append({
                        "type": "added_function",
                        "name": func_name,
                        "line_number": new_func.line_number,
                        "description": f"Function '{func_name}' was added"
                    })
            
            # Check for added classes
            for class_name, new_class in new_classes.items():
                if class_name not in old_classes:
                    api_changes.append({
                        "type": "added_class",
                        "name": class_name,
                        "line_number": new_class.line_number,
                        "description": f"Class '{class_name}' was added"
                    })
            
        except Exception as e:
            api_changes.append({
                "type": "analysis_error",
                "description": f"Error detecting API changes: {str(e)}"
            })
        
        return api_changes
    
    async def _detect_removed_items(self, old_ast, new_ast) -> List[Dict[str, Any]]:
        """Detect items that were removed"""
        removed_items = []
        
        try:
            # This is similar to breaking changes but includes all removals
            old_functions = {f.name: f for f in (old_ast.functions or [])}
            new_functions = {f.name: f for f in (new_ast.functions or [])}
            
            old_classes = {c.name: c for c in (old_ast.classes or [])}
            new_classes = {c.name: c for c in (new_ast.classes or [])}
            
            # Removed functions
            for func_name, old_func in old_functions.items():
                if func_name not in new_functions:
                    removed_items.append({
                        "type": "function",
                        "name": func_name,
                        "line_number": old_func.line_number
                    })
            
            # Removed classes
            for class_name, old_class in old_classes.items():
                if class_name not in new_classes:
                    removed_items.append({
                        "type": "class",
                        "name": class_name,
                        "line_number": old_class.line_number
                    })
            
        except Exception as e:
            removed_items.append({
                "type": "analysis_error",
                "description": f"Error detecting removed items: {str(e)}"
            })
        
        return removed_items
    
    def _function_signature_changed(self, old_func: Function, new_func: Function) -> bool:
        """Check if function signature changed"""
        # Compare parameter counts
        if len(old_func.parameters) != len(new_func.parameters):
            return True
        
        # Compare parameter names and types
        for old_param, new_param in zip(old_func.parameters, new_func.parameters):
            if old_param.name != new_param.name:
                return True
            if old_param.type_hint != new_param.type_hint:
                return True
        
        # Compare return types
        if old_func.return_type != new_func.return_type:
            return True
        
        return False
    
    def _categorize_impact(self, breaking_changes: List, api_changes: List, affected_files: List) -> str:
        """Categorize the level of impact"""
        if breaking_changes and affected_files:
            return "high"
        elif breaking_changes or (api_changes and affected_files):
            return "medium"
        elif api_changes or affected_files:
            return "low"
        else:
            return "minimal"