"""C++ language AST parser implementation."""

import asyncio
import subprocess
import tempfile
import os
import time
import json
from typing import Dict, List, Any, Optional

from ..core.base_parser import BaseParser, ASTResult, Language, Parameter, Property, Method, Function, Class, Import, Variable


class CppParser(BaseParser):
    """C++ language parser using clang."""
    
    def __init__(self):
        super().__init__()
        self.language = Language.CPP
        
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return ['.cpp', '.cxx', '.cc', '.c++', '.hpp', '.hxx', '.hh', '.h', '.h++']
        
    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """Parse C++ file and extract AST information."""
        start_time = time.time()
        
        try:
            # Use clang via a temporary C++ program
            ast_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_cpp_ast, file_path, content
            )
            
            # Convert to ASTResult
            functions = self._convert_functions(ast_data.get("functions", []))
            classes = self._convert_classes(ast_data.get("classes", []))
            imports = self._convert_includes(ast_data.get("includes", []))
            variables = self._convert_variables(ast_data.get("variables", []))
            
            parse_time = int((time.time() - start_time) * 1000)
            
            return ASTResult(
                success=True,
                language=self.language,
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata={
                    "namespaces": ast_data.get("namespaces", []),
                    "templates": ast_data.get("templates", []),
                    "macros": ast_data.get("macros", []),
                    "typedefs": ast_data.get("typedefs", []),
                    "enums": ast_data.get("enums", []),
                    "unions": ast_data.get("unions", []),
                    "preprocessor_directives": ast_data.get("preprocessor_directives", [])
                },
                parse_time_ms=parse_time
            )
            
        except Exception as e:
            parse_time = int((time.time() - start_time) * 1000)
            return ASTResult(
                success=False,
                language=self.language,
                error=str(e),
                parse_time_ms=parse_time
            )
    
    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """Parse multiple files in parallel."""
        tasks = []
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tasks.append(self.parse_file(file_path, content))
            except Exception as e:
                async def error_result():
                    return ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Cannot read file: {str(e)}"
                    )
                tasks.append(error_result())
        
        return await asyncio.gather(*tasks)
    
    def _extract_cpp_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract AST information using clang."""
        # Create a temporary C++ program to parse the file
        cpp_parser_code = '''
#include <clang-c/Index.h>
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <fstream>
#include <sstream>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

struct FunctionInfo {
    std::string name;
    std::string return_type;
    std::vector<std::pair<std::string, std::string>> parameters; // name, type
    int line;
    bool is_exported;
    bool is_virtual;
    bool is_static;
    bool is_inline;
    bool is_const;
    bool is_template;
    std::string template_params;
    std::string doc;
    std::vector<std::string> attributes;
};

struct ClassInfo {
    std::string name;
    std::vector<std::string> base_classes;
    std::vector<FunctionInfo> methods;
    std::vector<std::pair<std::string, std::string>> fields; // name, type
    int line;
    bool is_exported;
    bool is_template;
    std::string template_params;
    std::string access_specifier;
    std::string doc;
    std::vector<std::string> attributes;
};

struct IncludeInfo {
    std::string file;
    bool is_system;
    int line;
    bool is_angled;
};

struct VariableInfo {
    std::string name;
    std::string type;
    std::string value;
    int line;
    bool is_exported;
    bool is_static;
    bool is_const;
    bool is_extern;
    std::string doc;
    std::vector<std::string> attributes;
};

std::vector<FunctionInfo> functions;
std::vector<ClassInfo> classes;
std::vector<IncludeInfo> includes;
std::vector<VariableInfo> variables;
std::vector<std::string> namespaces;
std::vector<std::string> templates;
std::vector<std::string> macros;
std::vector<std::string> typedefs;
std::vector<std::string> enums;
std::vector<std::string> unions;
std::vector<std::string> preprocessor_directives;

std::string get_type_string(CXType type) {
    CXString type_spelling = clang_getTypeSpelling(type);
    std::string result = clang_getCString(type_spelling);
    clang_disposeString(type_spelling);
    return result;
}

std::string get_cursor_string(CXCursor cursor) {
    CXString cursor_spelling = clang_getCursorSpelling(cursor);
    std::string result = clang_getCString(cursor_spelling);
    clang_disposeString(cursor_spelling);
    return result;
}

std::string get_cursor_docstring(CXCursor cursor) {
    CXString comment = clang_Cursor_getRawCommentText(cursor);
    std::string result = clang_getCString(comment);
    clang_disposeString(comment);
    return result;
}

CXChildVisitResult visitor_function(CXCursor cursor, CXCursor parent, CXClientData client_data) {
    CXCursorKind kind = clang_getCursorKind(cursor);
    
    if (kind == CXCursor_FunctionDecl || kind == CXCursor_CXXMethod || 
        kind == CXCursor_FunctionTemplate || kind == CXCursor_Constructor || 
        kind == CXCursor_Destructor) {
        
        FunctionInfo func;
        func.name = get_cursor_string(cursor);
        func.return_type = get_type_string(clang_getCursorResultType(cursor));
        func.line = clang_getCursorLocation(cursor).line;
        func.is_exported = clang_getCursorLinkage(cursor) == CXLinkage_External;
        func.is_virtual = clang_CXXMethod_isVirtual(cursor);
        func.is_static = clang_Cursor_isStatic(cursor);
        func.is_inline = clang_Cursor_isInlineBodied(cursor);
        func.is_const = false; // Would need more analysis for const methods
        func.is_template = (kind == CXCursor_FunctionTemplate);
        func.doc = get_cursor_docstring(cursor);
        
        // Get parameters
        int num_args = clang_Cursor_getNumArguments(cursor);
        for (int i = 0; i < num_args; i++) {
            CXCursor arg = clang_Cursor_getArgument(cursor, i);
            std::string param_name = get_cursor_string(arg);
            std::string param_type = get_type_string(clang_getCursorType(arg));
            func.parameters.push_back({param_name, param_type});
        }
        
        // Get template parameters
        if (func.is_template) {
            // Would need to extract template parameters
            func.template_params = "";
        }
        
        functions.push_back(func);
    }
    else if (kind == CXCursor_ClassDecl || kind == CXCursor_StructDecl || 
             kind == CXCursor_ClassTemplate) {
        
        ClassInfo cls;
        cls.name = get_cursor_string(cursor);
        cls.line = clang_getCursorLocation(cursor).line;
        cls.is_exported = clang_getCursorLinkage(cursor) == CXLinkage_External;
        cls.is_template = (kind == CXCursor_ClassTemplate);
        cls.access_specifier = "public"; // Default
        cls.doc = get_cursor_docstring(cursor);
        
        // Get base classes
        int num_bases = 0; // Would need to use clang_getNumOverloadedDecls or similar
        // For now, we'll skip base class extraction
        
        // Visit class members
        clang_visitChildren(cursor, visitor_class_member, &cls);
        
        classes.push_back(cls);
    }
    else if (kind == CXCursor_VarDecl) {
        VariableInfo var;
        var.name = get_cursor_string(cursor);
        var.type = get_type_string(clang_getCursorType(cursor));
        var.line = clang_getCursorLocation(cursor).line;
        var.is_exported = clang_getCursorLinkage(cursor) == CXLinkage_External;
        var.is_static = clang_Cursor_isStatic(cursor);
        var.is_const = clang_isConstQualifiedType(clang_getCursorType(cursor));
        var.is_extern = false; // Would need to check storage class
        var.doc = get_cursor_docstring(cursor);
        
        variables.push_back(var);
    }
    else if (kind == CXCursor_Namespace) {
        std::string ns_name = get_cursor_string(cursor);
        if (!ns_name.empty()) {
            namespaces.push_back(ns_name);
        }
    }
    else if (kind == CXCursor_InclusionDirective) {
        IncludeInfo inc;
        inc.file = get_cursor_string(cursor);
        inc.line = clang_getCursorLocation(cursor).line;
        inc.is_system = inc.file.find("<") == 0; // Simple heuristic
        inc.is_angled = inc.file.find("<") == 0;
        
        includes.push_back(inc);
    }
    
    return CXChildVisit_Recurse;
}

CXChildVisitResult visitor_class_member(CXCursor cursor, CXCursor parent, CXClientData client_data) {
    ClassInfo* cls = static_cast<ClassInfo*>(client_data);
    CXCursorKind kind = clang_getCursorKind(cursor);
    
    if (kind == CXCursor_CXXMethod || kind == CXCursor_FunctionDecl || 
        kind == CXCursor_Constructor || kind == CXCursor_Destructor) {
        
        FunctionInfo method;
        method.name = get_cursor_string(cursor);
        method.return_type = get_type_string(clang_getCursorResultType(cursor));
        method.line = clang_getCursorLocation(cursor).line;
        method.is_exported = clang_getCursorLinkage(cursor) == CXLinkage_External;
        method.is_virtual = clang_CXXMethod_isVirtual(cursor);
        method.is_static = clang_Cursor_isStatic(cursor);
        method.is_inline = clang_Cursor_isInlineBodied(cursor);
        method.is_const = false;
        method.doc = get_cursor_docstring(cursor);
        
        // Get parameters
        int num_args = clang_Cursor_getNumArguments(cursor);
        for (int i = 0; i < num_args; i++) {
            CXCursor arg = clang_Cursor_getArgument(cursor, i);
            std::string param_name = get_cursor_string(arg);
            std::string param_type = get_type_string(clang_getCursorType(arg));
            method.parameters.push_back({param_name, param_type});
        }
        
        cls->methods.push_back(method);
    }
    else if (kind == CXCursor_FieldDecl) {
        std::string field_name = get_cursor_string(cursor);
        std::string field_type = get_type_string(clang_getCursorType(cursor));
        cls->fields.push_back({field_name, field_type});
    }
    
    return CXChildVisit_Continue;
}

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return 1;
    }
    
    const char* filename = argv[1];
    
    CXIndex index = clang_createIndex(0, 0);
    CXTranslationUnit unit;
    const char* args[] = {"-std=c++17"};
    
    int error = clang_parseTranslationUnit2(
        index, filename, args, 1, nullptr, 0,
        CXTranslationUnit_None, &unit);
    
    if (error != 0) {
        std::cerr << "Error parsing translation unit" << std::endl;
        return 1;
    }
    
    CXCursor cursor = clang_getTranslationUnitCursor(unit);
    clang_visitChildren(cursor, visitor_function, nullptr);
    
    clang_disposeTranslationUnit(unit);
    clang_disposeIndex(index);
    
    // Convert to JSON
    json result;
    
    // Convert functions
    for (const auto& func : functions) {
        json j_func;
        j_func["name"] = func.name;
        j_func["return_type"] = func.return_type;
        j_func["line"] = func.line;
        j_func["is_exported"] = func.is_exported;
        j_func["is_virtual"] = func.is_virtual;
        j_func["is_static"] = func.is_static;
        j_func["is_inline"] = func.is_inline;
        j_func["is_const"] = func.is_const;
        j_func["is_template"] = func.is_template;
        j_func["template_params"] = func.template_params;
        j_func["doc"] = func.doc;
        j_func["attributes"] = func.attributes;
        
        json j_params = json::array();
        for (const auto& param : func.parameters) {
            json j_param;
            j_param["name"] = param.first;
            j_param["type"] = param.second;
            j_params.push_back(j_param);
        }
        j_func["parameters"] = j_params;
        
        result["functions"].push_back(j_func);
    }
    
    // Convert classes
    for (const auto& cls : classes) {
        json j_cls;
        j_cls["name"] = cls.name;
        j_cls["base_classes"] = cls.base_classes;
        j_cls["line"] = cls.line;
        j_cls["is_exported"] = cls.is_exported;
        j_cls["is_template"] = cls.is_template;
        j_cls["template_params"] = cls.template_params;
        j_cls["access_specifier"] = cls.access_specifier;
        j_cls["doc"] = cls.doc;
        j_cls["attributes"] = cls.attributes;
        
        json j_methods = json::array();
        for (const auto& method : cls.methods) {
            json j_method;
            j_method["name"] = method.name;
            j_method["return_type"] = method.return_type;
            j_method["line"] = method.line;
            j_method["is_exported"] = method.is_exported;
            j_method["is_virtual"] = method.is_virtual;
            j_method["is_static"] = method.is_static;
            j_method["is_inline"] = method.is_inline;
            j_method["is_const"] = method.is_const;
            j_method["doc"] = method.doc;
            j_method["attributes"] = method.attributes;
            
            json j_params = json::array();
            for (const auto& param : method.parameters) {
                json j_param;
                j_param["name"] = param.first;
                j_param["type"] = param.second;
                j_params.push_back(j_param);
            }
            j_method["parameters"] = j_params;
            
            j_methods.push_back(j_method);
        }
        j_cls["methods"] = j_methods;
        
        json j_fields = json::array();
        for (const auto& field : cls.fields) {
            json j_field;
            j_field["name"] = field.first;
            j_field["type"] = field.second;
            j_fields.push_back(j_field);
        }
        j_cls["fields"] = j_fields;
        
        result["classes"].push_back(j_cls);
    }
    
    // Convert includes
    for (const auto& inc : includes) {
        json j_inc;
        j_inc["file"] = inc.file;
        j_inc["is_system"] = inc.is_system;
        j_inc["line"] = inc.line;
        j_inc["is_angled"] = inc.is_angled;
        result["includes"].push_back(j_inc);
    }
    
    // Convert variables
    for (const auto& var : variables) {
        json j_var;
        j_var["name"] = var.name;
        j_var["type"] = var.type;
        j_var["line"] = var.line;
        j_var["is_exported"] = var.is_exported;
        j_var["is_static"] = var.is_static;
        j_var["is_const"] = var.is_const;
        j_var["is_extern"] = var.is_extern;
        j_var["doc"] = var.doc;
        j_var["attributes"] = var.attributes;
        result["variables"].push_back(j_var);
    }
    
    result["namespaces"] = namespaces;
    result["templates"] = templates;
    result["macros"] = macros;
    result["typedefs"] = typedefs;
    result["enums"] = enums;
    result["unions"] = unions;
    result["preprocessor_directives"] = preprocessor_directives;
    
    std::cout << result.dump(2) << std::endl;
    return 0;
}
'''
        
        # Create CMakeLists.txt for the parser
        cmake_content = '''
cmake_minimum_required(VERSION 3.10)
project(cpp_ast_parser)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(PkgConfig REQUIRED)
pkg_check_modules(CLANG REQUIRED libclang)

add_executable(cpp_ast_parser main.cpp)

target_include_directories(cpp_ast_parser PRIVATE ${CLANG_INCLUDE_DIRS})
target_link_libraries(cpp_ast_parser ${CLANG_LIBRARIES})

# Find nlohmann_json
find_package(nlohmann_json 3.2.0 REQUIRED)
target_link_libraries(cpp_ast_parser nlohmann_json::nlohmann_json)
'''
        
        # Create temporary directory for C++ project
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write CMakeLists.txt
            with open(os.path.join(temp_dir, 'CMakeLists.txt'), 'w') as f:
                f.write(cmake_content)
            
            # Write main.cpp
            with open(os.path.join(temp_dir, 'main.cpp'), 'w') as f:
                f.write(cpp_parser_code)
            
            # Write target C++ file
            target_file = os.path.join(temp_dir, 'target.cpp')
            with open(target_file, 'w') as f:
                f.write(content)
            
            try:
                # Build the parser
                build_dir = os.path.join(temp_dir, 'build')
                os.makedirs(build_dir)
                
                subprocess.run(
                    ['cmake', '..', '-DCMAKE_BUILD_TYPE=Release'],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                subprocess.run(
                    ['make', '-j4'],
                    cwd=build_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Run the parser
                parser_executable = os.path.join(build_dir, 'cpp_ast_parser')
                result = subprocess.run(
                    [parser_executable, target_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    # Fallback to simpler parsing if clang fails
                    return self._fallback_parse(content)
                    
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                # Fallback to simpler parsing
                return self._fallback_parse(content)
    
    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        """Fallback parsing using regex patterns when clang is not available."""
        import re
        
        functions = []
        classes = []
        includes = []
        variables = []
        namespaces = []
        
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Simple function detection
            func_match = re.match(r'(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:\{|;)', line)
            if func_match and not line.startswith('//') and not line.startswith('/*'):
                func_name = func_match.group(1)
                if func_name not in ['if', 'while', 'for', 'switch', 'catch']:
                    functions.append({
                        "name": func_name,
                        "return_type": "auto",  # Would need more complex parsing
                        "line": i,
                        "is_exported": True,
                        "is_virtual": "virtual" in line,
                        "is_static": "static" in line,
                        "is_inline": "inline" in line,
                        "is_const": "const" in line,
                        "is_template": "template" in line,
                        "parameters": [],
                        "doc": "",
                        "attributes": []
                    })
            
            # Simple class detection
            class_match = re.match(r'(?:class|struct)\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(1)
                classes.append({
                    "name": class_name,
                    "base_classes": [],
                    "methods": [],
                    "fields": [],
                    "line": i,
                    "is_exported": True,
                    "is_template": "template" in line,
                    "access_specifier": "public",
                    "doc": "",
                    "attributes": []
                })
            
            # Simple include detection
            include_match = re.match(r'#include\s*[<"]([^>"]+)[>"]', line)
            if include_match:
                include_file = include_match.group(1)
                includes.append({
                    "file": include_file,
                    "is_system": line.find('<') != -1,
                    "line": i,
                    "is_angled": line.find('<') != -1
                })
            
            # Simple namespace detection
            namespace_match = re.match(r'namespace\s+(\w+)', line)
            if namespace_match:
                namespace_name = namespace_match.group(1)
                namespaces.append(namespace_name)
        
        return {
            "functions": functions,
            "classes": classes,
            "includes": includes,
            "variables": variables,
            "namespaces": namespaces,
            "templates": [],
            "macros": [],
            "typedefs": [],
            "enums": [],
            "unions": [],
            "preprocessor_directives": []
        }
    
    def _convert_functions(self, functions_data: List[Dict]) -> List[Function]:
        """Convert function data to Function objects."""
        functions = []
        for func_data in functions_data:
            parameters = []
            for param_data in func_data.get("parameters", []):
                parameters.append(Parameter(
                    name=param_data["name"],
                    type_hint=param_data["type"],
                    default_value=None,
                    is_optional=False,
                    docstring=None
                ))
            
            functions.append(Function(
                name=func_data["name"],
                parameters=parameters,
                return_type=func_data["return_type"],
                decorators=func_data.get("attributes", []),
                docstring=func_data.get("doc", ""),
                line_number=func_data["line"],
                complexity_score=1,
                is_async=False,
                is_method=False,
                class_name=None
            ))
        
        return functions
    
    def _convert_classes(self, classes_data: List[Dict]) -> List[Class]:
        """Convert class data to Class objects."""
        classes = []
        for class_data in classes_data:
            methods = []
            for method_data in class_data.get("methods", []):
                parameters = []
                for param_data in method_data.get("parameters", []):
                    parameters.append(Parameter(
                        name=param_data["name"],
                        type_hint=param_data["type"],
                        default_value=None,
                        is_optional=False,
                        docstring=None
                    ))
                
                methods.append(Method(
                    name=method_data["name"],
                    parameters=parameters,
                    return_type=method_data["return_type"],
                    decorators=method_data.get("attributes", []),
                    docstring=method_data.get("doc", ""),
                    line_number=method_data["line"],
                    access_level=method_data.get("access_specifier", "public"),
                    is_static=method_data.get("is_static", False),
                    is_async=False
                ))
            
            properties = []
            for field_data in class_data.get("fields", []):
                properties.append(Property(
                    name=field_data["name"],
                    type_hint=field_data["type"],
                    line_number=class_data["line"],
                    default_value=None,
                    access_level="public",  # Would need more analysis
                    docstring=None,
                    is_property=True
                ))
            
            classes.append(Class(
                name=class_data["name"],
                base_classes=class_data.get("base_classes", []),
                methods=methods,
                properties=properties,
                decorators=class_data.get("attributes", []),
                docstring=class_data.get("doc", ""),
                line_number=class_data["line"],
                is_abstract=False,  # Would need more analysis
                access_level=class_data.get("access_specifier", "public")
            ))
        
        return classes
    
    def _convert_includes(self, includes_data: List[Dict]) -> List[Import]:
        """Convert include data to Import objects."""
        imports = []
        for include_data in includes_data:
            imports.append(Import(
                module=include_data["file"],
                name="",
                alias="",
                line_number=include_data["line"],
                import_type="include",
                is_relative=not include_data.get("is_system", False),
                is_standard_library=include_data.get("is_system", False)
            ))
        
        return imports
    
    def _convert_variables(self, variables_data: List[Dict]) -> List[Variable]:
        """Convert variable data to Variable objects."""
        variables = []
        for var_data in variables_data:
            variables.append(Variable(
                name=var_data["name"],
                type_hint=var_data["type"],
                default_value=var_data.get("value", ""),
                line_number=var_data["line"],
                is_global=True,
                is_constant=var_data.get("is_const", False)
            ))
        
        return variables
    
    def extract_functions(self, ast_root: Any) -> List[Function]:
        """Extract function definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.functions or []
        return []
    
    def extract_classes(self, ast_root: Any) -> List[Class]:
        """Extract class definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.classes or []
        return []
    
    def extract_imports(self, ast_root: Any) -> List[Import]:
        """Extract import statements from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.imports or []
        return []
    
    def extract_variables(self, ast_root: Any) -> List[Variable]:
        """Extract variable definitions from AST."""
        if isinstance(ast_root, ASTResult):
            return ast_root.variables or []
        return []