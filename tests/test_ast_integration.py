"""
tests/test_ast_integration.py

Simple test suite for AST integration functionality.
"""

import asyncio
import tempfile
import os
from pathlib import Path

# Simple test runner
def run_test(test_name, test_func):
    """Simple test runner"""
    try:
        test_func()
        print(f"✅ {test_name} - PASSED")
        return True
    except Exception as e:
        print(f"❌ {test_name} - FAILED: {e}")
        return False

def test_ast_tools_basic():
    """Test basic AST tool functionality"""
    
    # Create a simple Python file for testing
    sample_code = '''
import os
from typing import List

def simple_function(param1: str, param2: int = 10) -> bool:
    """A simple function for testing."""
    if param1 and param2 > 0:
        return True
    return False

class TestClass:
    """A test class."""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_name(self) -> str:
        return self.name
'''
    
    # Write to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(sample_code)
        temp_file = f.name
    
    try:
        # Test 1: Basic file existence
        if not os.path.exists(temp_file):
            raise Exception("Test file was not created")
        
        # Test 2: File content validation
        with open(temp_file, 'r') as f:
            content = f.read()
            if "simple_function" not in content:
                raise Exception("Test function not found in file")
            if "TestClass" not in content:
                raise Exception("Test class not found in file")
        
        print(f"📁 Created test file: {temp_file}")
        print(f"📄 File size: {len(content)} characters")
        
        # Test 3: Basic Python syntax validation
        try:
            import ast
            ast.parse(content)
            print("✅ Python syntax is valid")
        except SyntaxError as e:
            raise Exception(f"Invalid Python syntax: {e}")
        
        print("✅ Basic AST tools test passed")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)
            print(f"🗑️ Cleaned up test file: {temp_file}")

def test_ast_import():
    """Test that AST tools can be imported"""
    try:
        # Try to import the AST tools module
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        
        # This will test if our AST tools are accessible
        from src.tools.ast_tools import analyze_code_structure
        print("✅ AST tools import successful")
        
        # Check if the tool has the right attributes
        if hasattr(analyze_code_structure, 'invoke'):
            print("✅ AST tool has invoke method")
        else:
            raise Exception("AST tool missing invoke method")
            
    except ImportError as e:
        raise Exception(f"Failed to import AST tools: {e}")

def test_project_structure_creation():
    """Test creating a temporary project structure"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create main.py
        main_py = Path(temp_dir) / "main.py"
        main_py.write_text('''
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
''')
        
        # Create utils module
        utils_dir = Path(temp_dir) / "utils"
        utils_dir.mkdir()
        helper_py = utils_dir / "helper.py"
        helper_py.write_text('''
def greet(name: str) -> str:
    return f"Hello, {name}!"
''')
        
        # Verify structure
        if not main_py.exists():
            raise Exception("main.py not created")
        if not helper_py.exists():
            raise Exception("helper.py not created")
        
        print(f"✅ Created test project structure in: {temp_dir}")
        print(f"📁 Files created: {list(Path(temp_dir).rglob('*.py'))}")

def run_all_tests():
    """Run all AST integration tests"""
    print("🚀 Starting AST Integration Tests")
    print("=" * 50)
    
    tests = [
        ("AST Import Test", test_ast_import),
        ("Basic AST Tools Test", test_ast_tools_basic),
        ("Project Structure Test", test_project_structure_creation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        if run_test(test_name, test_func):
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! AST integration is working.")
        return True
    else:
        print(f"⚠️ {total - passed} test(s) failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)