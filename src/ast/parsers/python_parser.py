"""
src/ast/parsers/python_parser.py

Python-specific AST parsing using built-in ast module.
"""

import ast
import sys
import time
import asyncio
from typing import List, Dict, Any, Optional, Union

from ..core.base_parser import (
    BaseParser,
    ASTResult,
    Language,
    Parameter,
    Property,
    Method,
    Function,
    Class,
    Import,
    Variable,
)


class PythonParser(BaseParser):
    """Python-specific AST parser using built-in ast module"""

    def __init__(self):
        super().__init__()
        self.language = Language.PYTHON

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".py", ".pyx", ".pyd"]

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """
        Parse Python file content into AST

        Args:
            file_path: Path to the Python file
            content: File content as string

        Returns:
            ASTResult with parsed structure
        """
        start_time = time.time()

        try:
            # Parse using built-in ast module
            tree = ast.parse(content, filename=file_path)

            # Extract information
            functions = self.extract_functions(tree)
            classes = self.extract_classes(tree)
            imports = self.extract_imports(tree)
            variables = self.extract_variables(tree)

            # Build metadata
            metadata = {
                "file_path": file_path,
                "encoding": "utf-8",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
                "node_count": self._count_nodes(tree),
                "complexity_score": self._calculate_complexity(tree),
            }

            parse_time = int((time.time() - start_time) * 1000)

            return ASTResult(
                success=True,
                language=self.language,
                ast_root=tree,
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata=metadata,
                parse_time_ms=parse_time,
            )

        except SyntaxError as e:
            parse_time = int((time.time() - start_time) * 1000)
            return ASTResult(
                success=False,
                language=self.language,
                error=f"Syntax error at line {e.lineno}: {e.msg}",
                parse_time_ms=parse_time,
            )
        except Exception as e:
            parse_time = int((time.time() - start_time) * 1000)
            return ASTResult(
                success=False,
                language=self.language,
                error=f"Parse error: {str(e)}",
                parse_time_ms=parse_time,
            )

    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """Parse multiple files in parallel."""
        tasks = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                tasks.append(self.parse_file(file_path, content))
            except Exception as e:
                # Create error result for files that can't be read
                error_msg = str(e)

                async def error_result():
                    return ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Cannot read file: {error_msg}",
                    )

                tasks.append(error_result())

        return await asyncio.gather(*tasks)

    def extract_functions(self, ast_root: ast.AST) -> List[Function]:
        """Extract function definitions from AST"""
        functions = []

        for node in ast.walk(ast_root):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Extract parameters
                parameters = []
                for arg in node.args.args:
                    param_type = (
                        self._get_type_annotation(arg.annotation)
                        if arg.annotation
                        else ""
                    )
                    parameters.append(
                        Parameter(
                            name=arg.arg,
                            type_hint=param_type,
                            default_value=None,  # TODO: Extract default values
                            is_optional=False,
                            docstring=None,
                        )
                    )

                # Handle *args
                if node.args.vararg:
                    vararg_type = (
                        self._get_type_annotation(node.args.vararg.annotation)
                        if node.args.vararg.annotation
                        else ""
                    )
                    parameters.append(
                        Parameter(
                            name=f"*{node.args.vararg.arg}",
                            type_hint=vararg_type,
                            default_value=None,
                            is_optional=False,
                            docstring=None,
                        )
                    )

                # Handle **kwargs
                if node.args.kwarg:
                    kwarg_type = (
                        self._get_type_annotation(node.args.kwarg.annotation)
                        if node.args.kwarg.annotation
                        else ""
                    )
                    parameters.append(
                        Parameter(
                            name=f"**{node.args.kwarg.arg}",
                            type_hint=kwarg_type,
                            default_value=None,
                            is_optional=False,
                            docstring=None,
                        )
                    )

                # Extract return type
                return_type = (
                    self._get_type_annotation(node.returns) if node.returns else ""
                )

                # Extract decorators
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(self._get_attribute_name(decorator))

                # Extract docstring
                docstring = ast.get_docstring(node) or ""

                # Calculate complexity
                complexity = self._calculate_function_complexity(node)

                # Check if function is a method
                is_method, class_name = self._is_method(node, ast_root)

                function = Function(
                    name=node.name,
                    parameters=parameters,
                    return_type=return_type,
                    decorators=decorators,
                    line_number=node.lineno,
                    docstring=docstring,
                    complexity_score=complexity,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    is_method=is_method,
                    class_name=class_name,
                )

                functions.append(function)

        return functions

    def extract_classes(self, ast_root: ast.AST) -> List[Class]:
        """Extract class definitions from AST"""
        classes = []

        for node in ast.walk(ast_root):
            if isinstance(node, ast.ClassDef):
                # Extract base classes
                base_classes = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_classes.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        base_classes.append(self._get_attribute_name(base))

                # Extract decorators
                decorators = []
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Name):
                        decorators.append(decorator.id)
                    elif isinstance(decorator, ast.Attribute):
                        decorators.append(self._get_attribute_name(decorator))

                # Extract docstring
                docstring = ast.get_docstring(node) or ""

                # Extract methods
                methods = []
                properties = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_info = self._extract_method_info(item)
                        methods.append(method_info)
                    elif isinstance(item, ast.AnnAssign) and isinstance(
                        item.target, ast.Name
                    ):
                        if self._is_property(item):
                            prop_type = (
                                self._get_type_annotation(item.annotation)
                                if item.annotation
                                else ""
                            )
                            properties.append(
                                Property(
                                    name=item.target.id,
                                    type_hint=prop_type,
                                    line_number=item.lineno,
                                    default_value=None,
                                    access_level="public",
                                    docstring=None,
                                    is_property=True,
                                )
                            )

                class_obj = Class(
                    name=node.name,
                    base_classes=base_classes,
                    methods=methods,
                    properties=properties,
                    decorators=decorators,
                    docstring=docstring,
                    line_number=node.lineno,
                    is_abstract=self._is_abstract_class(node),
                    access_level="public",  # Python doesn't have explicit access levels
                )

                classes.append(class_obj)

        return classes

    def extract_imports(self, ast_root: ast.AST) -> List[Import]:
        """Extract import statements from AST"""
        imports = []

        for node in ast.walk(ast_root):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_obj = Import(
                        module=alias.name,
                        name=alias.asname if alias.asname else alias.name,
                        alias=alias.asname,
                        line_number=node.lineno,
                        import_type="import",
                        is_relative=False,
                        is_standard_library=self._is_standard_library(alias.name),
                    )
                    imports.append(import_obj)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                is_relative = node.level > 0
                for alias in node.names:
                    import_obj = Import(
                        module=module,
                        name=alias.name,
                        alias=alias.asname,
                        line_number=node.lineno,
                        import_type="from",
                        is_relative=is_relative,
                        is_standard_library=(
                            self._is_standard_library(module) if module else False
                        ),
                    )
                    imports.append(import_obj)

        return imports

    def extract_variables(self, ast_root: ast.AST) -> List[Variable]:
        """Extract variable definitions from AST"""
        variables = []

        # Track assignments at module level
        for node in ast.walk(ast_root):
            if isinstance(node, ast.Assign):
                # Only process module-level assignments
                if self._is_module_level(node, ast_root):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_type = self._infer_variable_type(node.value)
                            variable = Variable(
                                name=target.id,
                                type_hint=var_type or "",
                                default_value=None,  # TODO: Extract actual values
                                line_number=node.lineno,
                                is_global=True,
                                is_constant=False,
                            )
                            variables.append(variable)

            elif isinstance(node, ast.AnnAssign):
                # Only process module-level annotated assignments
                if self._is_module_level(node, ast_root):
                    if isinstance(node.target, ast.Name):
                        var_type = (
                            self._get_type_annotation(node.annotation)
                            if node.annotation
                            else ""
                        )
                        variable = Variable(
                            name=node.target.id,
                            type_hint=var_type,
                            default_value=None,
                            line_number=node.lineno,
                            is_global=True,
                            is_constant=False,
                        )
                        variables.append(variable)

        return variables

    def _get_type_annotation(self, annotation: ast.AST) -> str:
        """Convert type annotation to string"""
        if annotation is None:
            return ""

        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Attribute):
            return self._get_attribute_name(annotation)
        elif isinstance(annotation, ast.Subscript):
            base = self._get_type_annotation(annotation.value)
            # Handle different slice types for different Python versions
            if sys.version_info >= (3, 9):
                slice_val = self._get_type_annotation(annotation.slice)
            else:
                # For Python < 3.9, slice is an Index node
                slice_val = self._get_type_annotation(
                    annotation.slice.value
                    if hasattr(annotation.slice, "value")
                    else annotation.slice
                )
            return f"{base}[{slice_val}]"
        elif isinstance(annotation, ast.List):
            elements = [self._get_type_annotation(elt) for elt in annotation.elts]
            return f"[{', '.join(elements)}]"
        elif isinstance(annotation, ast.Tuple):
            elements = [self._get_type_annotation(elt) for elt in annotation.elts]
            return f"({', '.join(elements)})"
        else:
            return str(type(annotation).__name__)

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name (e.g., module.Class.method)"""
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        else:
            return node.attr

    def _calculate_function_complexity(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate overall file complexity"""
        total_complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_complexity += self._calculate_function_complexity(node)
        return total_complexity

    def _count_nodes(self, tree: ast.AST) -> int:
        """Count total AST nodes"""
        return len(list(ast.walk(tree)))

    def _is_method(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], tree: ast.AST
    ) -> tuple[bool, Optional[str]]:
        """Check if function is a method inside a class and return class name"""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True, parent.name
        return False, None

    def _extract_method_info(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> Method:
        """Extract method information"""
        parameters = []
        for arg in node.args.args:
            param_type = (
                self._get_type_annotation(arg.annotation) if arg.annotation else ""
            )
            parameters.append(
                Parameter(
                    name=arg.arg,
                    type_hint=param_type,
                    default_value=None,
                    is_optional=False,
                    docstring=None,
                )
            )

        return_type = self._get_type_annotation(node.returns) if node.returns else ""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)

        docstring = ast.get_docstring(node) or ""
        complexity = self._calculate_function_complexity(node)

        return Method(
            name=node.name,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            line_number=node.lineno,
            docstring=docstring,
            access_level="public",
            is_static="staticmethod" in decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def _is_property(self, node: ast.AnnAssign) -> bool:
        """Check if annotated assignment is a property"""
        # Simple heuristic - could be enhanced
        return hasattr(node, "annotation") and node.annotation is not None

    def _is_abstract_class(self, node: ast.ClassDef) -> bool:
        """Check if class is abstract"""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "abstractmethod":
                return True
        return False

    def _is_module_level(self, node: ast.AST, tree: ast.AST) -> bool:
        """Check if node is at module level"""
        # Simple implementation - could be improved
        return isinstance(tree, ast.Module) and node in tree.body

    def _infer_variable_type(self, value: ast.AST) -> Optional[str]:
        """Infer variable type from assignment value"""
        if isinstance(value, ast.Constant):
            return type(value.value).__name__
        elif isinstance(value, ast.List):
            return "list"
        elif isinstance(value, ast.Dict):
            return "dict"
        elif isinstance(value, ast.Set):
            return "set"
        elif isinstance(value, ast.Tuple):
            return "tuple"
        elif isinstance(value, ast.Call):
            if isinstance(value.func, ast.Name):
                return value.func.id
        return None

    def _is_standard_library(self, module_name: str) -> bool:
        """Check if import is from Python standard library"""
        stdlib_modules = {
            "os",
            "sys",
            "json",
            "datetime",
            "time",
            "math",
            "random",
            "re",
            "collections",
            "itertools",
            "functools",
            "operator",
            "pathlib",
            "urllib",
            "http",
            "socket",
            "ssl",
            "hashlib",
            "hmac",
            "secrets",
            "threading",
            "multiprocessing",
            "concurrent",
            "asyncio",
            "logging",
            "unittest",
            "argparse",
            "configparser",
            "tempfile",
            "shutil",
            "glob",
            "fnmatch",
            "pickle",
            "csv",
            "sqlite3",
        }

        # Check if it's a standard library module
        base_module = module_name.split(".")[0]
        return base_module in stdlib_modules
