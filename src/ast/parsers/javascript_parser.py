"""
src/ast/parsers/javascript_parser.py

JavaScript/TypeScript AST parser using tree-sitter.
"""

import re
import json
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

# Try to import tree-sitter, fallback to basic parsing if not available
try:
    import tree_sitter
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

# Try to import tree-sitter JavaScript language binding
try:
    import tree_sitter_javascript

    TREE_SITTER_JS_AVAILABLE = True
except ImportError:
    TREE_SITTER_JS_AVAILABLE = False

# Try to import tree-sitter TypeScript language binding
try:
    import tree_sitter_typescript

    TREE_SITTER_TS_AVAILABLE = True
except ImportError:
    TREE_SITTER_TS_AVAILABLE = False

from src.ast.core.base_parser import (
    BaseParser,
    ASTResult,
    Language,
    Function,
    Class,
    Import,
    Variable,
    Parameter,
)


class JavaScriptASTParser(BaseParser):
    """JavaScript/TypeScript AST parser using tree-sitter"""

    def __init__(self, language: Language = Language.JAVASCRIPT):
        super().__init__()
        self.language = language
        self.parser = None
        self.js_language = None
        self.ts_language = None

        if TREE_SITTER_AVAILABLE:
            try:
                self.parser = Parser()

                # Initialize JavaScript language
                if TREE_SITTER_JS_AVAILABLE:
                    self.js_language = Language(
                        tree_sitter_javascript.language(), "javascript"
                    )

                # Initialize TypeScript language
                if TREE_SITTER_TS_AVAILABLE:
                    self.ts_language = Language(
                        tree_sitter_typescript.language_typescript(), "typescript"
                    )

            except Exception as e:
                print(f"Warning: Failed to initialize tree-sitter: {e}")
                self.parser = None

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """
        Parse JavaScript/TypeScript file content into AST

        Args:
            file_path: Path to the JavaScript/TypeScript file
            content: File content as string

        Returns:
            ASTResult with parsed structure
        """
        try:
            if self.parser and (self.js_language or self.ts_language):
                return await self._parse_with_tree_sitter(file_path, content)
            else:
                return self._parse_fallback(file_path, content)

        except Exception as e:
            return ASTResult(
                success=False,
                language=self.language,
                error=f"Parse error: {str(e)}",
                parse_time_ms=0,
            )

    async def _parse_with_tree_sitter(self, file_path: str, content: str) -> ASTResult:
        """Parse using tree-sitter for accurate AST"""
        try:
            # Determine if this is TypeScript
            is_typescript = (
                file_path.endswith(".ts")
                or file_path.endswith(".tsx")
                or "interface " in content
                or "type " in content
                and "=" in content
            )

            # Set appropriate language
            if is_typescript and self.ts_language:
                self.parser.set_language(self.ts_language)
                actual_language = Language.TYPESCRIPT
            elif self.js_language:
                self.parser.set_language(self.js_language)
                actual_language = Language.JAVASCRIPT
            else:
                return self._parse_fallback(file_path, content)

            # Parse the code
            tree = self.parser.parse(bytes(content, "utf-8"))

            if not tree.root_node:
                return ASTResult(
                    success=False,
                    language=actual_language,
                    error="Failed to parse AST tree",
                    parse_time_ms=0,
                )

            # Extract functions, classes, imports
            functions = self._extract_functions_tree_sitter(tree.root_node, content)
            classes = self._extract_classes_tree_sitter(tree.root_node, content)
            imports = self._extract_imports_tree_sitter(tree.root_node, content)
            variables = self._extract_variables_tree_sitter(tree.root_node, content)

            # Build metadata
            metadata = {
                "file_path": file_path,
                "encoding": "utf-8",
                "parser": "tree_sitter",
                "node_count": self._count_nodes(tree.root_node),
                "complexity_score": sum(f.complexity_score for f in functions),
                "is_typescript": is_typescript,
                "has_jsx": file_path.endswith(".jsx") or file_path.endswith(".tsx"),
            }

            return ASTResult(
                success=True,
                language=actual_language,
                ast_root=tree,
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata=metadata,
                parse_time_ms=0,
            )

        except Exception as e:
            return ASTResult(
                success=False,
                language=self.language,
                error=f"Tree-sitter parse error: {str(e)}",
                parse_time_ms=0,
            )

    def _parse_fallback(self, file_path: str, content: str) -> ASTResult:
        """Fallback parsing using regex and basic patterns"""
        try:
            # Determine if TypeScript
            is_typescript = (
                file_path.endswith(".ts")
                or file_path.endswith(".tsx")
                or "interface " in content
                or "type " in content
                and "=" in content
            )

            actual_language = (
                Language.TYPESCRIPT if is_typescript else Language.JAVASCRIPT
            )

            # Extract functions
            functions = self._extract_functions_fallback(content)

            # Extract classes
            classes = self._extract_classes_fallback(content)

            # Extract imports
            imports = self._extract_imports_fallback(content)

            # Extract variables
            variables = self._extract_variables_fallback(content)

            metadata = {
                "file_path": file_path,
                "encoding": "utf-8",
                "parser": "regex_fallback",
                "node_count": len(functions) + len(classes) + len(variables),
                "complexity_score": sum(f.complexity_score for f in functions),
                "is_typescript": is_typescript,
                "has_jsx": file_path.endswith(".jsx") or file_path.endswith(".tsx"),
            }

            return ASTResult(
                success=True,
                language=actual_language,
                ast_root=None,  # No actual AST in fallback
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata=metadata,
                parse_time_ms=0,
            )

        except Exception as e:
            return ASTResult(
                success=False,
                language=self.language,
                error=f"Fallback parse error: {str(e)}",
                parse_time_ms=0,
            )

    def _extract_functions_tree_sitter(self, node, content: str) -> List[Function]:
        """Extract functions using tree-sitter AST"""
        functions = []

        def traverse(node):
            if node.type in [
                "function_declaration",
                "function_expression",
                "arrow_function",
                "method_definition",
            ]:
                func_info = self._parse_function_node(node, content)
                if func_info:
                    functions.append(func_info)

            for child in node.children:
                traverse(child)

        traverse(node)
        return functions

    def _parse_function_node(self, node, content: str) -> Optional[Function]:
        """Parse a function node from tree-sitter"""
        try:
            # Get function name
            name = "anonymous"
            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                    break

            # Get line number
            line_number = node.start_point[0] + 1

            # Extract parameters
            parameters = []
            for child in node.children:
                if child.type == "formal_parameters":
                    parameters = self._extract_parameters_tree_sitter(child, content)
                    break

            # Determine if async
            is_async = any(child.type == "async" for child in node.children)

            # Determine if method
            is_method = node.type == "method_definition"

            # Get return type for TypeScript
            return_type = ""
            for child in node.children:
                if child.type == "type_annotation":
                    return_type = (
                        content[child.start_byte : child.end_byte]
                        .replace(":", "")
                        .strip()
                    )
                    break

            # Calculate complexity
            complexity = self._calculate_complexity_tree_sitter(node)

            return Function(
                name=name,
                line_number=line_number,
                parameters=parameters,
                return_type=return_type,
                decorators=[],
                docstring="",
                complexity_score=complexity,
                is_async=is_async,
                is_method=is_method,
            )

        except Exception:
            return None

    def _extract_parameters_tree_sitter(self, node, content: str) -> List[Parameter]:
        """Extract parameters from function node"""
        parameters = []

        for child in node.children:
            if child.type == "formal_parameter":
                param_info = self._parse_parameter_node(child, content)
                if param_info:
                    parameters.append(param_info)

        return parameters

    def _parse_parameter_node(self, node, content: str) -> Optional[Parameter]:
        """Parse a parameter node"""
        try:
            name = ""
            param_type = ""
            is_optional = False

            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                elif child.type == "type_annotation":
                    param_type = (
                        content[child.start_byte : child.end_byte]
                        .replace(":", "")
                        .strip()
                    )
                elif child.type == "optional_parameter":
                    is_optional = True

            return Parameter(name=name, type_hint=param_type, is_optional=is_optional)

        except Exception:
            return None

    def _extract_classes_tree_sitter(self, node, content: str) -> List[Class]:
        """Extract classes using tree-sitter AST"""
        classes = []

        def traverse(node):
            if node.type in ["class_declaration", "class_expression"]:
                class_info = self._parse_class_node(node, content)
                if class_info:
                    classes.append(class_info)

            for child in node.children:
                traverse(child)

        traverse(node)
        return classes

    def _parse_class_node(self, node, content: str) -> Optional[Class]:
        """Parse a class node from tree-sitter"""
        try:
            # Get class name
            name = "Anonymous"
            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                    break

            # Get line number
            line_number = node.start_point[0] + 1

            # Extract inheritance
            base_classes = []
            for child in node.children:
                if child.type == "class_heritage":
                    for heritage_child in child.children:
                        if heritage_child.type == "identifier":
                            base_name = content[
                                heritage_child.start_byte : heritage_child.end_byte
                            ]
                            base_classes.append(base_name)

            # Extract methods
            methods = []
            for child in node.children:
                if child.type == "class_body":
                    methods = self._extract_class_methods_tree_sitter(child, content)
                    break

            return Class(
                name=name,
                line_number=line_number,
                base_classes=base_classes,
                methods=methods,
                properties=[],
                decorators=[],
                docstring="",
                is_abstract=False,
                access_level="public",
            )

        except Exception:
            return None

    def _extract_class_methods_tree_sitter(
        self, node, content: str
    ) -> List[Dict[str, Any]]:
        """Extract methods from class body"""
        methods = []

        for child in node.children:
            if child.type == "method_definition":
                method_info = self._parse_function_node(child, content)
                if method_info:
                    methods.append(
                        {
                            "name": method_info.name,
                            "line": method_info.line_number,
                            "parameters": [
                                {"name": p.name, "type": p.type_hint}
                                for p in method_info.parameters
                            ],
                            "return_type": method_info.return_type,
                            "is_static": any(
                                c.type == "static" for c in child.children
                            ),
                            "is_public": True,  # Default in JS/TS
                            "complexity": method_info.complexity_score,
                        }
                    )

        return methods

    def _extract_imports_tree_sitter(self, node, content: str) -> List[Import]:
        """Extract imports using tree-sitter AST"""
        imports = []

        def traverse(node):
            if node.type in ["import_statement", "import_declaration"]:
                import_info = self._parse_import_node(node, content)
                if import_info:
                    imports.append(import_info)

            for child in node.children:
                traverse(child)

        traverse(node)
        return imports

    def _parse_import_node(self, node, content: str) -> Optional[Import]:
        """Parse an import node from tree-sitter"""
        try:
            line_number = node.start_point[0] + 1
            module = ""
            name = None
            alias = None

            for child in node.children:
                if child.type == "string":
                    module = content[child.start_byte : child.end_byte].strip("\"'")
                elif child.type == "import_specifier":
                    for subchild in child.children:
                        if subchild.type == "identifier":
                            name = content[subchild.start_byte : subchild.end_byte]
                elif child.type == "identifier":
                    if not name:
                        name = content[child.start_byte : child.end_byte]

            return Import(
                module=module,
                name=name,
                alias=alias,
                line_number=line_number,
                import_type="import",
            )

        except Exception:
            return None

    def _extract_variables_tree_sitter(self, node, content: str) -> List[Variable]:
        """Extract variables using tree-sitter AST"""
        variables = []

        def traverse(node):
            if node.type in ["variable_declaration", "lexical_declaration"]:
                var_info = self._parse_variable_node(node, content)
                if var_info:
                    variables.append(var_info)

            for child in node.children:
                traverse(child)

        traverse(node)
        return variables

    def _parse_variable_node(self, node, content: str) -> Optional[Variable]:
        """Parse a variable node from tree-sitter"""
        try:
            line_number = node.start_point[0] + 1
            name = ""
            var_type = ""
            default_value = None
            is_constant = False

            for child in node.children:
                if child.type == "identifier":
                    name = content[child.start_byte : child.end_byte]
                elif child.type == "type_annotation":
                    var_type = (
                        content[child.start_byte : child.end_byte]
                        .replace(":", "")
                        .strip()
                    )
                elif child.type == "const":
                    is_constant = True

            return Variable(
                name=name,
                line_number=line_number,
                type_hint=var_type,
                default_value=default_value,
                is_constant=is_constant,
            )

        except Exception:
            return None

    def _calculate_complexity_tree_sitter(self, node) -> int:
        """Calculate complexity score for a node"""
        complexity = 1  # Base complexity

        def traverse(n):
            nonlocal complexity
            if n.type in [
                "if_statement",
                "for_statement",
                "while_statement",
                "switch_statement",
                "try_statement",
                "catch_clause",
            ]:
                complexity += 1
            for child in n.children:
                traverse(child)

        traverse(node)
        return complexity

    def _count_nodes(self, node) -> int:
        """Count total nodes in tree"""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    def _extract_functions_fallback(self, content: str) -> List[Function]:
        """Extract functions using regex fallback"""
        functions = []

        # Function patterns
        patterns = [
            r"function\s+(\w+)\s*\([^)]*\)\s*{",  # function declarations
            r"const\s+(\w+)\s*=\s*\([^)]*\)\s*=>",  # arrow functions
            r"let\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*{",  # function expressions
            r"(\w+)\s*:\s*\([^)]*\)\s*=>",  # TypeScript arrow functions
            r"async\s+function\s+(\w+)\s*\([^)]*\)\s*{",  # async functions
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                # Extract parameters (simplified)
                params_match = re.search(r"\(([^)]*)\)", match.group(0))
                parameters = []
                if params_match:
                    param_str = params_match.group(1)
                    if param_str.strip():
                        for param in param_str.split(","):
                            param = param.strip()
                            if param:
                                parameters.append(Parameter(name=param))

                # Check if async
                is_async = "async" in match.group(0)

                functions.append(
                    Function(
                        name=func_name,
                        line_number=line_num,
                        parameters=parameters,
                        return_type="",
                        decorators=[],
                        docstring="",
                        complexity_score=1,
                        is_async=is_async,
                        is_method=False,
                    )
                )

        return functions

    def _extract_classes_fallback(self, content: str) -> List[Class]:
        """Extract classes using regex fallback"""
        classes = []

        # Class pattern
        class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{"

        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            line_num = content[: match.start()].count("\n") + 1

            inheritance = [extends] if extends else []

            classes.append(
                Class(
                    name=class_name,
                    line_number=line_num,
                    base_classes=inheritance,
                    methods=[],
                    properties=[],
                    decorators=[],
                    docstring="",
                    is_abstract=False,
                    access_level="public",
                )
            )

        return classes

    def _extract_imports_fallback(self, content: str) -> List[Import]:
        """Extract imports using regex fallback"""
        imports = []

        # Import patterns
        patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',  # import ... from
            r'import\s+[\'"]([^\'"]+)[\'"]',  # import 'module'
            r'require\([\'"]([^\'"]+)[\'"]\)',  # require
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                imports.append(
                    Import(
                        module=module,
                        name=module.split("/")[-1],
                        line_number=line_num,
                        import_type="import",
                    )
                )

        return imports

    def _extract_variables_fallback(self, content: str) -> List[Variable]:
        """Extract variables using regex fallback"""
        variables = []

        # Variable patterns
        patterns = [
            r"const\s+(\w+)\s*=",  # const variables
            r"let\s+(\w+)\s*=",  # let variables
            r"var\s+(\w+)\s*=",  # var variables
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                var_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1
                is_constant = "const" in match.group(0)

                variables.append(
                    Variable(
                        name=var_name, line_number=line_num, is_constant=is_constant
                    )
                )

        return variables

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        return [".js", ".jsx", ".mjs", ".ts", ".tsx"]

    def extract_functions(self, ast_root: Any) -> List[Function]:
        """Extract function definitions from AST"""
        if ast_root and hasattr(ast_root, "root_node"):
            return self._extract_functions_tree_sitter(ast_root.root_node, "")
        return []

    def extract_classes(self, ast_root: Any) -> List[Class]:
        """Extract class definitions from AST"""
        if ast_root and hasattr(ast_root, "root_node"):
            return self._extract_classes_tree_sitter(ast_root.root_node, "")
        return []

    def extract_imports(self, ast_root: Any) -> List[Import]:
        """Extract import statements from AST"""
        if ast_root and hasattr(ast_root, "root_node"):
            return self._extract_imports_tree_sitter(ast_root.root_node, "")
        return []

    def extract_variables(self, ast_root: Any) -> List[Variable]:
        """Extract variable definitions from AST"""
        if ast_root and hasattr(ast_root, "root_node"):
            return self._extract_variables_tree_sitter(ast_root.root_node, "")
        return []

    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """Parse multiple files in parallel"""
        import asyncio

        tasks = []
        for file_path in file_paths:
            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                task = self.parse_file(file_path, content)
                tasks.append(task)
            except Exception:
                # Create error result for unreadable file
                tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Dummy task
                continue

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out dummy tasks and create proper error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Failed to parse {file_paths[i]}: {str(result)}",
                        parse_time_ms=0,
                    )
                )
            elif hasattr(result, "success"):
                final_results.append(result)
            else:
                # Dummy task result
                final_results.append(
                    ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Could not read file: {file_paths[i]}",
                        parse_time_ms=0,
                    )
                )

        return final_results
