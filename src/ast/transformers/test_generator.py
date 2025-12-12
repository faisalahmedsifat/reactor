"""Test generation from function signatures and AST analysis."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class GeneratedTest:
    """Represents a generated test case."""
    test_name: str
    test_type: str  # unit, integration, edge_case, etc.
    function_name: str
    test_code: str
    setup_code: str
    teardown_code: str
    assertions: List[str]
    mock_objects: List[str]
    test_data: Dict[str, Any]
    coverage_lines: List[int]


@dataclass
class TestSuite:
    """Complete test suite for a module."""
    suite_name: str
    framework: str  # pytest, unittest, jest, etc.
    tests: List[GeneratedTest]
    imports: List[str]
    fixtures: List[str]
    coverage_percentage: float


class TestGenerator:
    """Generates test cases from AST analysis."""
    
    def __init__(self):
        self.test_patterns = self._initialize_test_patterns()
        self.framework_templates = self._initialize_framework_templates()
    
    def _initialize_test_patterns(self) -> Dict[str, Dict]:
        """Initialize test generation patterns."""
        return {
            "happy_path": {
                "description": "Test normal expected behavior",
                "priority": "high"
            },
            "edge_case": {
                "description": "Test boundary conditions and edge cases",
                "priority": "medium"
            },
            "error_case": {
                "description": "Test error conditions and exceptions",
                "priority": "high"
            },
            "null_input": {
                "description": "Test with null/None inputs",
                "priority": "medium"
            },
            "empty_input": {
                "description": "Test with empty collections/strings",
                "priority": "medium"
            },
            "boundary": {
                "description": "Test numeric boundaries (0, max, min)",
                "priority": "medium"
            }
        }
    
    def _initialize_framework_templates(self) -> Dict[str, str]:
        """Initialize test framework templates."""
        return {
            "pytest": """
import pytest
{imports}

{fixtures}

class Test{class_name}:
{tests}
""",
            "unittest": """
import unittest
{imports}

{fixtures}

class Test{class_name}(unittest.TestCase):
{tests}
""",
            "jest": """
{imports}

{fixtures}

describe('{class_name}', () => {{
{tests}
}});
""",
            "junit": """
import org.junit.Test;
import org.junit.Before;
import org.junit.After;
import static org.junit.Assert.*;
{imports}

public class {class_name}Test {{
{fixtures}
{tests}
}}
"""
        }
    
    def generate_tests(self, ast_result: ASTResult, file_path: str, content: str, 
                     framework: str = "pytest") -> TestSuite:
        """Generate test suite from AST result."""
        
        # Determine framework based on language
        if hasattr(ast_result.language, 'value'):
            language = ast_result.language.value.lower()
        else:
            language = str(ast_result.language).lower()
        
        framework = self._detect_framework(language, framework)
        
        # Generate tests for functions
        function_tests = []
        if ast_result.functions:
            function_tests = self._generate_function_tests(ast_result.functions, framework, language)
        
        # Generate tests for classes
        class_tests = []
        if ast_result.classes:
            class_tests = self._generate_class_tests(ast_result.classes, framework, language)
        
        # Combine all tests
        all_tests = function_tests + class_tests
        
        # Generate imports and fixtures
        imports = self._generate_test_imports(ast_result, framework, language)
        fixtures = self._generate_test_fixtures(ast_result, framework, language)
        
        # Calculate coverage estimate
        coverage_percentage = self._estimate_coverage(ast_result, all_tests)
        
        return TestSuite(
            suite_name=self._get_suite_name(file_path),
            framework=framework,
            tests=all_tests,
            imports=imports,
            fixtures=fixtures,
            coverage_percentage=coverage_percentage
        )
    
    def _detect_framework(self, language: str, preferred: str) -> str:
        """Detect appropriate test framework for the language."""
        framework_map = {
            "python": "pytest",
            "javascript": "jest", 
            "typescript": "jest",
            "java": "junit",
            "csharp": "nunit",
            "cpp": "gtest",
            "rust": "cargo test",
            "go": "testing",
            "dart": "test"
        }
        
        return framework_map.get(language, preferred)
    
    def _generate_function_tests(self, functions: List[Function], framework: str, language: str) -> List[GeneratedTest]:
        """Generate tests for standalone functions."""
        tests = []
        
        for func in functions:
            # Skip private/internal functions
            if func.name.startswith('_') or not self._is_testable_function(func):
                continue
            
            # Generate different test types
            test_types = ["happy_path", "edge_case", "error_case"]
            
            for test_type in test_types:
                test = self._generate_function_test(func, test_type, framework, language)
                if test:
                    tests.append(test)
        
        return tests
    
    def _generate_class_tests(self, classes: List[Class], framework: str, language: str) -> List[GeneratedTest]:
        """Generate tests for classes and their methods."""
        tests = []
        
        for cls in classes:
            # Skip test classes or abstract classes
            if self._is_test_class(cls) or cls.is_abstract:
                continue
            
            # Generate tests for each method
            for method in cls.methods:
                if not self._is_testable_method(method):
                    continue
                
                # Generate different test types
                test_types = ["happy_path", "edge_case", "error_case"]
                
                for test_type in test_types:
                    test = self._generate_method_test(cls, method, test_type, framework, language)
                    if test:
                        tests.append(test)
        
        return tests
    
    def _generate_function_test(self, func: Function, test_type: str, framework: str, language: str) -> Optional[GeneratedTest]:
        """Generate a test for a specific function."""
        test_name = f"test_{func.name}_{test_type}"
        
        # Generate test data based on function signature
        test_data = self._generate_test_data(func, test_type, language)
        
        # Generate test code based on framework
        if framework == "pytest":
            test_code = self._generate_pytest_test(func, test_type, test_data)
        elif framework == "unittest":
            test_code = self._generate_unittest_test(func, test_type, test_data)
        elif framework == "jest":
            test_code = self._generate_jest_test(func, test_type, test_data)
        elif framework == "junit":
            test_code = self._generate_junit_test(func, test_type, test_data)
        else:
            test_code = self._generate_generic_test(func, test_type, test_data, language)
        
        # Generate assertions
        assertions = self._generate_assertions(func, test_type, test_data, language)
        
        return GeneratedTest(
            test_name=test_name,
            test_type=test_type,
            function_name=func.name,
            test_code=test_code,
            setup_code=self._generate_setup_code(func, test_type, language),
            teardown_code=self._generate_teardown_code(func, test_type, language),
            assertions=assertions,
            mock_objects=self._generate_mocks(func, test_type, language),
            test_data=test_data,
            coverage_lines=[func.line_number]
        )
    
    def _generate_method_test(self, cls: Class, method, test_type: str, framework: str, language: str) -> Optional[GeneratedTest]:
        """Generate a test for a class method."""
        test_name = f"test_{cls.name}_{method.name}_{test_type}"
        
        # Generate test data
        test_data = self._generate_test_data(method, test_type, language)
        
        # Generate test code
        if framework == "pytest":
            test_code = self._generate_pytest_method_test(cls, method, test_type, test_data)
        elif framework == "unittest":
            test_code = self._generate_unittest_method_test(cls, method, test_type, test_data)
        elif framework == "jest":
            test_code = self._generate_jest_method_test(cls, method, test_type, test_data)
        elif framework == "junit":
            test_code = self._generate_junit_method_test(cls, method, test_type, test_data)
        else:
            test_code = self._generate_generic_method_test(cls, method, test_type, test_data, language)
        
        # Generate assertions
        assertions = self._generate_assertions(method, test_type, test_data, language)
        
        return GeneratedTest(
            test_name=test_name,
            test_type=test_type,
            function_name=f"{cls.name}.{method.name}",
            test_code=test_code,
            setup_code=self._generate_method_setup_code(cls, method, test_type, language),
            teardown_code=self._generate_method_teardown_code(cls, method, test_type, language),
            assertions=assertions,
            mock_objects=self._generate_method_mocks(cls, method, test_type, language),
            test_data=test_data,
            coverage_lines=[method.line_number]
        )
    
    def _generate_test_data(self, func: Function, test_type: str, language: str) -> Dict[str, Any]:
        """Generate test data based on function signature and test type."""
        test_data = {}
        
        for param in func.parameters:
            param_name = param.name
            param_type = param.type_hint.lower()
            
            if test_type == "happy_path":
                test_data[param_name] = self._generate_happy_path_value(param_type, language)
            elif test_type == "edge_case":
                test_data[param_name] = self._generate_edge_case_value(param_type, language)
            elif test_type == "error_case":
                test_data[param_name] = self._generate_error_case_value(param_type, language)
            elif test_type == "null_input":
                test_data[param_name] = self._generate_null_value(language)
            elif test_type == "empty_input":
                test_data[param_name] = self._generate_empty_value(param_type, language)
            elif test_type == "boundary":
                test_data[param_name] = self._generate_boundary_value(param_type, language)
        
        return test_data
    
    def _generate_happy_path_value(self, param_type: str, language: str) -> Any:
        """Generate normal test values."""
        type_mapping = {
            "int": 42,
            "integer": 42,
            "float": 3.14,
            "double": 3.14,
            "string": '"test"',
            "str": '"test"',
            "bool": True,
            "boolean": True,
            "list": [1, 2, 3],
            "array": [1, 2, 3],
            "dict": {"key": "value"},
            "map": {"key": "value"},
            "object": '{"key": "value"}'
        }
        
        for key, value in type_mapping.items():
            if key in param_type:
                return value
        
        return "test_value"
    
    def _generate_edge_case_value(self, param_type: str, language: str) -> Any:
        """Generate edge case test values."""
        type_mapping = {
            "int": 0,
            "integer": 0,
            "float": 0.0,
            "double": 0.0,
            "string": '""',
            "str": '""',
            "bool": False,
            "boolean": False,
            "list": [],
            "array": [],
            "dict": {},
            "map": {}
        }
        
        for key, value in type_mapping.items():
            if key in param_type:
                return value
        
        return None
    
    def _generate_error_case_value(self, param_type: str, language: str) -> Any:
        """Generate error case test values."""
        if language in ["python", "dart"]:
            return None
        elif language in ["javascript", "typescript"]:
            return "undefined"
        elif language in ["java", "csharp"]:
            return None
        else:
            return None
    
    def _generate_null_value(self, language: str) -> Any:
        """Generate null value for language."""
        if language in ["python", "dart"]:
            return None
        elif language in ["javascript", "typescript"]:
            return "null"
        elif language in ["java", "csharp"]:
            return None
        else:
            return None
        elif language in ["javascript", "typescript"]:
            return "undefined"
        elif language in ["java", "csharp"]:
            return None
        elif language in ["java", "csharp"]:
            return None
        else:
            return None
        elif language in ["javascript", "typescript"]:
            return "null"
        elif language in ["java", "csharp"]:
            return None
        else:
            return None
    
    def _generate_empty_value(self, param_type: str, language: str) -> Any:
        """Generate empty value based on type."""
        if "string" in param_type or "str" in param_type:
            return '""'
        elif "list" in param_type or "array" in param_type:
            return []
        elif "dict" in param_type or "map" in param_type:
            return {}
        else:
            return None
    
    def _generate_boundary_value(self, param_type: str, language: str) -> Any:
        """Generate boundary test values."""
        if "int" in param_type:
            return [0, 1, -1, 2147483647, -2147483648]  # 32-bit int boundaries
        elif "float" in param_type or "double" in param_type:
            return [0.0, -0.0, float('inf'), float('-inf')]
        elif "string" in param_type or "str" in param_type:
            return ["", "a", "a" * 1000]  # empty, single char, long string
        else:
            return None
    
    def _generate_pytest_test(self, func: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate pytest test code."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{func.name}_{test_type}(self):\n"
        test_code += f"        # Test {test_type} for {func.name}\n"
        
        if test_type == "error_case":
            test_code += f"        with pytest.raises(Exception):\n"
            test_code += f"            result = {func.name}({args})\n"
        else:
            test_code += f"        result = {func.name}({args})\n"
            test_code += f"        assert result is not None\n"
            
            # Add specific assertions based on return type
            if func.return_type:
                if "bool" in func.return_type.lower():
                    test_code += f"        assert isinstance(result, bool)\n"
                elif "int" in func.return_type.lower():
                    test_code += f"        assert isinstance(result, int)\n"
                elif "str" in func.return_type.lower():
                    test_code += f"        assert isinstance(result, str)\n"
        
        return test_code
    
    def _generate_unittest_test(self, func: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate unittest test code."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{func.name}_{test_type}(self):\n"
        test_code += f"        # Test {test_type} for {func.name}\n"
        
        if test_type == "error_case":
            test_code += f"        with self.assertRaises(Exception):\n"
            test_code += f"            result = {func.name}({args})\n"
        else:
            test_code += f"        result = {func.name}({args})\n"
            test_code += f"        self.assertIsNotNone(result)\n"
        
        return test_code
    
    def _generate_jest_test(self, func: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate Jest test code."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    test('{func.name} {test_type}', () => {{\n"
        test_code += f"        // Test {test_type} for {func.name}\n"
        
        if test_type == "error_case":
            test_code += f"        expect(() => {{\n"
            test_code += f"            {func.name}({args});\n"
            test_code += f"        }}).toThrow();\n"
        else:
            test_code += f"        const result = {func.name}({args});\n"
            test_code += f"        expect(result).toBeDefined();\n"
        
        test_code += f"    }});\n"
        
        return test_code
    
    def _generate_junit_test(self, func: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate JUnit test code."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    @Test\n"
        test_code += f"    public void test{func.name[:1].upper()}{func.name[1:]}{test_type.title()}() {{\n"
        test_code += f"        // Test {test_type} for {func.name}\n"
        
        if test_type == "error_case":
            test_code += f"        assertThrows(Exception.class, () -> {{\n"
            test_code += f"            {func.name}({args});\n"
            test_code += f"        }});\n"
        else:
            test_code += f"        var result = {func.name}({args});\n"
            test_code += f"        assertNotNull(result);\n"
        
        test_code += f"    }}\n"
        
        return test_code
    
    def _generate_pytest_method_test(self, cls: Class, method: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate pytest test for class method."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{cls.name}_{method.name}_{test_type}(self):\n"
        test_code += f"        # Test {test_type} for {cls.name}.{method.name}\n"
        test_code += f"        instance = {cls.name}()\n"
        
        if test_type == "error_case":
            test_code += f"        with pytest.raises(Exception):\n"
            test_code += f"            result = instance.{method.name}({args})\n"
        else:
            test_code += f"        result = instance.{method.name}({args})\n"
            test_code += f"        assert result is not None\n"
        
        return test_code
    
    def _generate_unittest_method_test(self, cls: Class, method: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate unittest test for class method."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{cls.name}_{method.name}_{test_type}(self):\n"
        test_code += f"        # Test {test_type} for {cls.name}.{method.name}\n"
        test_code += f"        instance = {cls.name}()\n"
        
        if test_type == "error_case":
            test_code += f"        with self.assertRaises(Exception):\n"
            test_code += f"            result = instance.{method.name}({args})\n"
        else:
            test_code += f"        result = instance.{method.name}({args})\n"
            test_code += f"        self.assertIsNotNone(result)\n"
        
        return test_code
    
    def _generate_jest_method_test(self, cls: Class, method: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate Jest test for class method."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    test('{cls.name}.{method.name} {test_type}', () => {{\n"
        test_code += f"        // Test {test_type} for {cls.name}.{method.name}\n"
        test_code += f"        const instance = new {cls.name}();\n"
        
        if test_type == "error_case":
            test_code += f"        expect(() => {{\n"
            test_code += f"            instance.{method.name}({args});\n"
            test_code += f"        }}).toThrow();\n"
        else:
            test_code += f"        const result = instance.{method.name}({args});\n"
            test_code += f"        expect(result).toBeDefined();\n"
        
        test_code += f"    }});\n"
        
        return test_code
    
    def _generate_junit_method_test(self, cls: Class, method: Function, test_type: str, test_data: Dict[str, Any]) -> str:
        """Generate JUnit test for class method."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    @Test\n"
        test_code += f"    public void test{cls.name}{method.name[:1].upper()}{method.name[1:]}{test_type.title()}() {{\n"
        test_code += f"        // Test {test_type} for {cls.name}.{method.name}\n"
        test_code += f"        {cls.name} instance = new {cls.name}();\n"
        
        if test_type == "error_case":
            test_code += f"        assertThrows(Exception.class, () -> {{\n"
            test_code += f"            instance.{method.name}({args});\n"
            test_code += f"        }});\n"
        else:
            test_code += f"        var result = instance.{method.name}({args});\n"
            test_code += f"        assertNotNull(result);\n"
        
        test_code += f"    }}\n"
        
        return test_code
    
    def _generate_generic_test(self, func: Function, test_type: str, test_data: Dict[str, Any], language: str) -> str:
        """Generate generic test code for other languages."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{func.name}_{test_type}():\n"
        test_code += f"        # Test {test_type} for {func.name}\n"
        test_code += f"        result = {func.name}({args})\n"
        test_code += f"        assert result is not None\n"
        
        return test_code
    
    def _generate_generic_method_test(self, cls: Class, method: Function, test_type: str, test_data: Dict[str, Any], language: str) -> str:
        """Generate generic method test for other languages."""
        args = ", ".join([f"{name}={value}" for name, value in test_data.items()])
        
        test_code = f"    def test_{cls.name}_{method.name}_{test_type}():\n"
        test_code += f"        # Test {test_type} for {cls.name}.{method.name}\n"
        test_code += f"        instance = {cls.name}()\n"
        test_code += f"        result = instance.{method.name}({args})\n"
        test_code += f"        assert result is not None\n"
        
        return test_code
    
    def _generate_assertions(self, func: Function, test_type: str, test_data: Dict[str, Any], language: str) -> List[str]:
        """Generate assertions for test."""
        assertions = []
        
        if test_type == "happy_path":
            assertions.append("Result should not be None")
            if func.return_type:
                if "bool" in func.return_type.lower():
                    assertions.append("Result should be boolean")
                elif "int" in func.return_type.lower():
                    assertions.append("Result should be integer")
                elif "str" in func.return_type.lower():
                    assertions.append("Result should be string")
        
        elif test_type == "error_case":
            assertions.append("Should raise exception")
        
        elif test_type == "edge_case":
            assertions.append("Should handle edge cases gracefully")
        
        return assertions
    
    def _generate_setup_code(self, func: Function, test_type: str, language: str) -> str:
        """Generate setup code for test."""
        # Simplified - would analyze function dependencies
        return ""
    
    def _generate_teardown_code(self, func: Function, test_type: str, language: str) -> str:
        """Generate teardown code for test."""
        # Simplified - would analyze resource usage
        return ""
    
    def _generate_mocks(self, func: Function, test_type: str, language: str) -> List[str]:
        """Generate mock objects for test."""
        mocks = []
        
        # Analyze function parameters to determine what needs mocking
        for param in func.parameters:
            param_type = param.type_hint.lower()
            
            # Common types that might need mocking
            if any(mock_type in param_type for mock_type in ["database", "http", "file", "network", "api"]):
                mocks.append(f"mock_{param.name}")
        
        return mocks
    
    def _generate_method_setup_code(self, cls: Class, method: Function, test_type: str, language: str) -> str:
        """Generate setup code for method test."""
        return f"        # Setup {cls.name} instance\n"
    
    def _generate_method_teardown_code(self, cls: Class, method: Function, test_type: str, language: str) -> str:
        """Generate teardown code for method test."""
        return f"        # Teardown {cls.name} instance\n"
    
    def _generate_method_mocks(self, cls: Class, method: Function, test_type: str, language: str) -> List[str]:
        """Generate mocks for method test."""
        return self._generate_mocks(method, test_type, language)
    
    def _generate_test_imports(self, ast_result: ASTResult, framework: str, language: str) -> List[str]:
        """Generate required imports for tests."""
        imports = []
        
        if framework == "pytest":
            imports.append("import pytest")
        elif framework == "unittest":
            imports.append("import unittest")
        elif framework == "jest":
            imports.extend(["import { describe, it, expect } from '@jest/globals'"])
        elif framework == "junit":
            imports.extend(["import org.junit.Test;", "import org.junit.Before;", "import org.junit.After;"])
        
        # Add imports for the module being tested
        if ast_result.imports:
            for imp in ast_result.imports[:5]:  # Limit to avoid too many imports
                imports.append(f"import {imp.module}")
        
        return list(set(imports))  # Remove duplicates
    
    def _generate_test_fixtures(self, ast_result: ASTResult, framework: str, language: str) -> List[str]:
        """Generate test fixtures and setup."""
        fixtures = []
        
        # Common fixtures
        if framework in ["pytest", "unittest"]:
            fixtures.append("""
    @pytest.fixture
    def sample_data():
        return {"key": "value", "number": 42}
""")
        
        return fixtures
    
    def _get_suite_name(self, file_path: str) -> str:
        """Generate test suite name from file path."""
        filename = file_path.split('/')[-1].split('.')[0]
        return f"Test{filename.title()}"
    
    def _estimate_coverage(self, ast_result: ASTResult, tests: List[GeneratedTest]) -> float:
        """Estimate test coverage percentage."""
        if not ast_result.functions and not ast_result.classes:
            return 0.0
        
        # Count total testable items
        total_items = len(ast_result.functions or [])
        if ast_result.classes:
            total_items += sum(len(cls.methods) for cls in ast_result.classes)
        
        # Count tested items
        tested_functions = len(set(test.function_name for test in tests))
        coverage_percentage = (tested_functions / total_items * 100) if total_items > 0 else 0.0
        
        return min(coverage_percentage, 100.0)
    
    def _is_testable_function(self, func: Function) -> bool:
        """Check if function is suitable for testing."""
        # Skip private functions
        if func.name.startswith('_'):
            return False
        
        # Skip functions with no parameters and void return (might be utilities)
        if not func.parameters and (not func.return_type or func.return_type == "void"):
            return False
        
        return True
    
    def _is_testable_method(self, method) -> bool:
        """Check if method is suitable for testing."""
        # Skip private methods
        if method.name.startswith('_'):
            return False
        
        # Skip constructors and destructors
        if method.name in ["__init__", "__del__", "constructor", "destructor"]:
            return False
        
        return True
    
    def _is_test_class(self, cls: Class) -> bool:
        """Check if class is already a test class."""
        return "test" in cls.name.lower() or cls.name.startswith("Test")
    
    def export_test_suite(self, test_suite: TestSuite, output_path: str) -> bool:
        """Export test suite to file."""
        try:
            # Generate test file content
            template = self.framework_templates.get(test_suite.framework, "")
            
            # Generate test methods
            test_methods = []
            for test in test_suite.tests:
                test_methods.append(test.test_code)
            
            # Combine imports
            imports_str = "\n".join(test_suite.imports)
            
            # Combine fixtures
            fixtures_str = "\n".join(test_suite.fixtures)
            
            # Combine tests
            tests_str = "\n".join(test_methods)
            
            # Generate final content
            content = template.format(
                imports=imports_str,
                fixtures=fixtures_str,
                tests=tests_str,
                class_name=test_suite.suite_name.replace("Test", "")
            )
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error exporting test suite: {e}")
            return False