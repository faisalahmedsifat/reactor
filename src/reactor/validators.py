"""
src/reactor/validators.py

Validation components for syntax and import checking.
"""

import ast
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.ast.core.ast_manager import ASTManager
from src.ast.core.base_parser import Language, Import
from .config import ReactorConfig


class ValidationResult:
    """Result of validation operation"""

    def __init__(self, is_valid: bool, language: Language = Language.PYTHON):
        self.is_valid = is_valid
        self.language = language
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.line_number: Optional[int] = None
        self.details: Dict[str, Any] = {}


class SyntaxValidator:
    """Validates syntax using AST parsing"""

    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config

    async def validate_syntax(self, file_path: str, content: str) -> ValidationResult:
        """
        Validate syntax of file content

        Args:
            file_path: Path to the file
            content: File content to validate

        Returns:
            ValidationResult with syntax validation results
        """
        result = ValidationResult(is_valid=True)

        try:
            # Check file size
            if (
                len(content.encode("utf-8"))
                > self.config.get_max_file_size_mb() * 1024 * 1024
            ):
                result.is_valid = False
                result.errors.append(
                    f"File too large: exceeds {self.config.get_max_file_size_mb()}MB limit"
                )
                return result

            # Use AST manager to parse
            ast_result = await self.ast_manager.parse_file(file_path, use_cache=True)
            result.language = ast_result.language

            if not ast_result.success:
                result.is_valid = False
                result.errors.append(ast_result.error or "Unknown parsing error")
                # Try to extract line number from error message if available
                if ast_result.error:
                    import re

                    line_match = re.search(r"line (\d+)", ast_result.error)
                    if line_match:
                        result.line_number = int(line_match.group(1))
            else:
                result.details.update(
                    {
                        "parse_time_ms": ast_result.parse_time_ms,
                        "language": ast_result.language.value,
                        "ast_root_available": ast_result.ast_root is not None,
                    }
                )

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation error: {str(e)}")

        # Special handling for JavaScript/TypeScript: If AST passed (likely fallback) but we have 'node',
        # run a real syntax check because fallback regex parser misses syntax errors.
        if result.is_valid and (
            result.language == Language.JAVASCRIPT
            or result.language == Language.TYPESCRIPT
        ):
            await self._validate_node_check(file_path, result)

        return result

    async def _validate_node_check(self, file_path: str, result: ValidationResult):
        """Run 'node -c' to check syntax for JS/TS files"""
        try:
            # Check if node is available
            import shutil

            if not shutil.which("node"):
                return

            # Run node check
            proc = await asyncio.create_subprocess_exec(
                "node",
                "--check",
                file_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                result.is_valid = False
                error_msg = stderr.decode().strip() or stdout.decode().strip()
                # Clean up error message (remove file path to keep it clean)
                result.errors.append(f"Syntax error (node): {error_msg}")
        except Exception:
            pass  # Ignore node check errors if usage fails

    def _validate_python_syntax(self, content: str) -> ValidationResult:
        """Validate Python syntax using built-in AST parser"""
        result = ValidationResult(is_valid=True, language=Language.PYTHON)

        try:
            ast.parse(content)
        except SyntaxError as e:
            result.is_valid = False
            result.errors.append(f"Syntax error: {e.msg}")
            result.line_number = e.lineno
            result.details.update({"offset": e.offset, "text": e.text})
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Parse error: {str(e)}")

        return result


class ImportValidator:
    """Validates import statements and dependencies"""

    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config

    async def validate_imports(self, file_path: str, content: str) -> ValidationResult:
        """
        Validate import statements in file content

        Args:
            file_path: Path to the file
            content: File content to validate

        Returns:
            ValidationResult with import validation results
        """
        result = ValidationResult(is_valid=True)

        try:
            # Parse the file to extract imports
            ast_result = await self.ast_manager.parse_file(file_path, use_cache=True)
            result.language = ast_result.language

            if not ast_result.success or not ast_result.ast_root:
                result.warnings.append("Could not parse file for import validation")
                return result

            # Get imports using AST manager
            imports = await self.ast_manager.extract_imports_from_file(file_path)

            # Validate each import
            invalid_imports = []
            missing_modules = []

            for import_name in imports:
                validation_result = await self._validate_single_import(
                    import_name, file_path
                )
                if not validation_result[0]:  # is_valid
                    invalid_imports.append(import_name)
                    if validation_result[1]:  # is_missing_module
                        missing_modules.append(import_name)

            # Update result
            if invalid_imports:
                result.is_valid = False
                result.errors.extend(
                    [f"Invalid import: {imp}" for imp in invalid_imports]
                )

            if missing_modules:
                result.warnings.extend(
                    [f"Missing module: {imp}" for imp in missing_modules]
                )

            result.details.update(
                {
                    "total_imports": len(imports),
                    "invalid_imports": len(invalid_imports),
                    "missing_modules": len(missing_modules),
                    "imports_list": imports,
                }
            )

        except Exception as e:
            result.warnings.append(f"Import validation error: {str(e)}")

        return result

    async def _validate_single_import(
        self, import_name: str, file_path: str
    ) -> Tuple[bool, bool]:
        """
        Validate a single import

        Returns:
            Tuple of (is_valid, is_missing_module)
        """
        try:
            # For Python, try to import the module
            if import_name.startswith("."):
                # Relative import - check if it makes sense in context
                return await self._validate_relative_import(import_name, file_path)
            else:
                # Absolute import - try to import
                return await self._validate_absolute_import(import_name)
        except Exception:
            return False, True

    async def _validate_absolute_import(self, import_name: str) -> Tuple[bool, bool]:
        """Validate absolute import by attempting to import"""
        try:
            # Split module and sub-item
            parts = import_name.split(".")
            module_name = parts[0]

            # Try to import the base module
            import importlib

            importlib.import_module(module_name)
            return True, False
        except ImportError:
            return False, True
        except Exception:
            return False, False

    async def _validate_relative_import(
        self, import_name: str, file_path: str
    ) -> Tuple[bool, bool]:
        """Validate relative import by checking file structure"""
        try:
            # Count the level of relative import
            level = 0
            while import_name.startswith("."):
                level += 1
                import_name = import_name[1:]

            if not import_name:
                # Just relative import like "from . import ..."
                return True, False

            # Get the file's directory
            file_path_obj = Path(file_path).parent

            # Go up the required number of levels
            for _ in range(level - 1):
                file_path_obj = file_path_obj.parent

            # Check if the module exists
            module_parts = import_name.split(".")
            current_path = file_path_obj

            for part in module_parts:
                # Check for .py file or directory with __init__.py
                py_file = current_path / f"{part}.py"
                init_file = current_path / part / "__init__.py"

                if py_file.exists():
                    current_path = py_file.parent
                elif init_file.exists():
                    current_path = init_file.parent
                else:
                    return False, True

            return True, False
        except Exception:
            return False, False


class CompositeValidator:
    """Combines multiple validators"""

    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.config = config
        self.syntax_validator = (
            SyntaxValidator(ast_manager, config)
            if config.should_validate_syntax()
            else None
        )
        self.import_validator = (
            ImportValidator(ast_manager, config)
            if config.should_validate_imports()
            else None
        )

    async def validate(self, file_path: str, content: str) -> ValidationResult:
        """
        Run all enabled validators

        Args:
            file_path: Path to the file
            content: File content to validate

        Returns:
            Combined ValidationResult
        """
        combined_result = ValidationResult(is_valid=True)

        # Run syntax validation
        if self.syntax_validator:
            syntax_result = await self.syntax_validator.validate_syntax(
                file_path, content
            )
            combined_result.is_valid &= syntax_result.is_valid
            combined_result.errors.extend(syntax_result.errors)
            combined_result.warnings.extend(syntax_result.warnings)
            combined_result.details.update({"syntax": syntax_result.details})
            if syntax_result.line_number:
                combined_result.line_number = syntax_result.line_number

        # Run import validation
        if self.import_validator:
            import_result = await self.import_validator.validate_imports(
                file_path, content
            )
            combined_result.is_valid &= import_result.is_valid
            combined_result.errors.extend(import_result.errors)
            combined_result.warnings.extend(import_result.warnings)
            combined_result.details.update({"imports": import_result.details})

        return combined_result
