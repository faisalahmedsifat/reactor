"""Go language AST parser implementation."""

import asyncio
import subprocess
import tempfile
import os
import time
from typing import Dict, List, Any, Optional

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


class GoParser(BaseParser):
    """Go language parser using go/parser."""

    def __init__(self):
        super().__init__()
        self.language = Language.GO

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".go"]

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """Parse Go file and extract AST information."""
        start_time = time.time()

        try:
            # Use go/ast via a temporary Go program
            ast_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_go_ast, file_path, content
            )

            # Convert to ASTResult
            functions = self._convert_functions(ast_data.get("functions", []))
            classes = self._convert_interfaces(ast_data.get("interfaces", []))
            imports = self._convert_imports(ast_data.get("imports", []))
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
                    "package": ast_data.get("package", ""),
                    "exports": ast_data.get("exports", []),
                    "types": ast_data.get("types", []),
                    "goroutines": ast_data.get("goroutines", []),
                    "channels": ast_data.get("channels", []),
                },
                parse_time_ms=parse_time,
            )

        except Exception as e:
            parse_time = int((time.time() - start_time) * 1000)
            return ASTResult(
                success=False,
                language=self.language,
                error=str(e),
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
                async def error_result():
                    return ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Cannot read file: {str(e)}",
                    )

                tasks.append(error_result())

        return await asyncio.gather(*tasks)

    def _extract_go_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract AST information using Go's go/ast package."""
        # Create a temporary Go program to parse the file
        go_parser_code = """
package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"strings"
	"encoding/json"
)

type FunctionInfo struct {
	Name       string   `json:"name"`
	Receiver   string   `json:"receiver"`
	Parameters []ParamInfo `json:"parameters"`
	ReturnType []string `json:"return_type"`
	Line       int      `json:"line"`
	IsExported bool     `json:"is_exported"`
	Doc        string   `json:"doc"`
}

type ParamInfo struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type InterfaceInfo struct {
	Name       string         `json:"name"`
	Methods    []MethodInfo   `json:"methods"`
	Line       int            `json:"line"`
	IsExported bool           `json:"is_exported"`
	Doc        string         `json:"doc"`
}

type MethodInfo struct {
	Name       string      `json:"name"`
	Parameters []ParamInfo `json:"parameters"`
	ReturnType []string    `json:"return_type"`
}

type ImportInfo struct {
	Path     string `json:"path"`
	Alias    string `json:"alias"`
	Line     int    `json:"line"`
	IsUsed   bool   `json:"is_used"`
}

type TypeInfo struct {
	Name       string `json:"name"`
	Underlying string `json:"underlying"`
	Methods    []MethodInfo `json:"methods"`
	Line       int    `json:"line"`
	IsExported bool   `json:"is_exported"`
}

type VariableInfo struct {
	Name       string   `json:"name"`
	Type       string   `json:"type"`
	Value      string   `json:"value"`
	Line       int      `json:"line"`
	IsExported bool     `json:"is_exported"`
	IsConstant bool     `json:"is_constant"`
}

func main() {
	if len(os.Args) != 2 {
		fmt.Println("Usage: go run parser.go <filename>")
		os.Exit(1)
	}

	filename := os.Args[1]
	fset := token.NewFileSet()
	
	node, err := parser.ParseFile(fset, filename, nil, parser.ParseComments)
	if err != nil {
		fmt.Printf("Error parsing file: %v\\n", err)
		os.Exit(1)
	}

	result := map[string]interface{}{
		"package":    node.Name.Name,
		"functions":  []FunctionInfo{},
		"interfaces": []InterfaceInfo{},
		"imports":     []ImportInfo{},
		"types":       []TypeInfo{},
		"variables":   []VariableInfo{},
	}

	// Extract imports
	for _, imp := range node.Imports {
		importPath := strings.Trim(imp.Path.Value, `"`)
		alias := ""
		if imp.Name != nil {
			alias = imp.Name.Name
		}
		
		result["imports"] = append(result["imports"].([]ImportInfo), ImportInfo{
			Path:   importPath,
			Alias:  alias,
			Line:   fset.Position(imp.Pos()).Line,
			IsUsed: true,
		})
	}

	// Extract declarations
	ast.Inspect(node, func(n ast.Node) bool {
		switch decl := n.(type) {
		case *ast.FuncDecl:
			funcInfo := FunctionInfo{
				Name:       decl.Name.Name,
				Line:       fset.Position(decl.Pos()).Line,
				IsExported: decl.Name.IsExported(),
			}

			if decl.Recv != nil && len(decl.Recv.List) > 0 {
				if recv := decl.Recv.List[0]; recv != nil {
					funcInfo.Receiver = fmt.Sprintf("%v", recv.Type)
				}
			}

			if decl.Type.Params != nil {
				for _, param := range decl.Type.Params.List {
					paramType := fmt.Sprintf("%v", param.Type)
					for _, name := range param.Names {
						funcInfo.Parameters = append(funcInfo.Parameters, ParamInfo{
							Name: name.Name,
							Type: paramType,
						})
					}
				}
			}

			if decl.Type.Results != nil {
				for _, result := range decl.Type.Results.List {
					resultType := fmt.Sprintf("%v", result.Type)
					funcInfo.ReturnType = append(funcInfo.ReturnType, resultType)
				}
			}

			if decl.Doc != nil {
				funcInfo.Doc = decl.Doc.Text()
			}

			result["functions"] = append(result["functions"].([]FunctionInfo), funcInfo)

		case *ast.GenDecl:
			if decl.Tok == token.TYPE {
				for _, spec := range decl.Specs {
					if typeSpec, ok := spec.(*ast.TypeSpec); ok {
						if interfaceType, ok := typeSpec.Type.(*ast.InterfaceType); ok {
							// Handle interface
							interfaceInfo := InterfaceInfo{
								Name:       typeSpec.Name.Name,
								Line:       fset.Position(typeSpec.Pos()).Line,
								IsExported: typeSpec.Name.IsExported(),
							}

							if decl.Doc != nil {
								interfaceInfo.Doc = decl.Doc.Text()
							}

							for _, method := range interfaceType.Methods.List {
								if funcType, ok := method.Type.(*ast.FuncType); ok {
									methodInfo := MethodInfo{
										Name: method.Names[0].Name,
									}

									if funcType.Params != nil {
										for _, param := range funcType.Params.List {
											paramType := fmt.Sprintf("%v", param.Type)
											for _, name := range param.Names {
												methodInfo.Parameters = append(methodInfo.Parameters, ParamInfo{
													Name: name.Name,
													Type: paramType,
												})
											}
										}
									}

									if funcType.Results != nil {
										for _, result := range funcType.Results.List {
											resultType := fmt.Sprintf("%v", result.Type)
											methodInfo.ReturnType = append(methodInfo.ReturnType, resultType)
										}
									}

									interfaceInfo.Methods = append(interfaceInfo.Methods, methodInfo)
								}
							}

							result["interfaces"] = append(result["interfaces"].([]InterfaceInfo), interfaceInfo)
						} else {
							// Handle other types
							typeInfo := TypeInfo{
								Name:       typeSpec.Name.Name,
								Underlying: fmt.Sprintf("%v", typeSpec.Type),
								Line:       fset.Position(typeSpec.Pos()).Line,
								IsExported: typeSpec.Name.IsExported(),
							}

							result["types"] = append(result["types"].([]TypeInfo), typeInfo)
						}
					}
				}
			} else if decl.Tok == token.VAR || decl.Tok == token.CONST {
				for _, spec := range decl.Specs {
					if valueSpec, ok := spec.(*ast.ValueSpec); ok {
						varType := ""
						if valueSpec.Type != nil {
							varType = fmt.Sprintf("%v", valueSpec.Type)
						}

						varValue := ""
						if len(valueSpec.Values) > 0 {
							varValue = fmt.Sprintf("%v", valueSpec.Values[0])
						}

						for _, name := range valueSpec.Names {
							varInfo := VariableInfo{
								Name:       name.Name,
								Type:       varType,
								Value:      varValue,
								Line:       fset.Position(valueSpec.Pos()).Line,
								IsExported: name.IsExported(),
								IsConstant: decl.Tok == token.CONST,
							}
							result["variables"] = append(result["variables"].([]VariableInfo), varInfo)
						}
					}
				}
			}
		}

		return true
	})

	jsonData, _ := json.Marshal(result)
	fmt.Println(string(jsonData))
}
"""

        # Write the Go parser to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
            f.write(go_parser_code)
            parser_file = f.name

        # Write the target Go file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False) as f:
            f.write(content)
            target_file = f.name

        try:
            # Run the Go parser
            result = subprocess.run(
                ["go", "run", parser_file, target_file],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                import json

                return json.loads(result.stdout)
            else:
                raise Exception(f"Go parser failed: {result.stderr}")

        finally:
            # Clean up temporary files
            os.unlink(parser_file)
            os.unlink(target_file)

    def _convert_functions(self, functions_data: List[Dict]) -> List[Function]:
        """Convert function data to Function objects."""
        functions = []
        for func_data in functions_data:
            parameters = []
            for param_data in func_data.get("parameters", []):
                parameters.append(
                    Parameter(
                        name=param_data["name"],
                        type_hint=param_data["type"],
                        default_value=None,
                        is_optional=False,
                        docstring=None,
                    )
                )

            functions.append(
                Function(
                    name=func_data["name"],
                    parameters=parameters,
                    return_type=", ".join(func_data.get("return_type", [])),
                    decorators=[],
                    docstring=func_data.get("doc", ""),
                    line_number=func_data["line"],
                    complexity_score=1,
                    is_async=False,
                    is_method=bool(func_data.get("receiver", "")),
                    class_name=(
                        func_data.get("receiver", "")
                        if func_data.get("receiver", "")
                        else None
                    ),
                )
            )

        return functions

    def _convert_interfaces(self, interfaces_data: List[Dict]) -> List[Class]:
        """Convert interface data to Class objects."""
        classes = []
        for interface_data in interfaces_data:
            methods = []
            for method_data in interface_data.get("methods", []):
                parameters = []
                for param_data in method_data.get("parameters", []):
                    parameters.append(
                        Parameter(
                            name=param_data["name"],
                            type_hint=param_data["type"],
                            default_value=None,
                            is_optional=False,
                            docstring=None,
                        )
                    )

                methods.append(
                    Method(
                        name=method_data["name"],
                        parameters=parameters,
                        return_type=", ".join(method_data.get("return_type", [])),
                        decorators=[],
                        docstring="",
                        line_number=interface_data["line"],
                        access_level="public",
                        is_static=False,
                        is_async=False,
                    )
                )

            classes.append(
                Class(
                    name=interface_data["name"],
                    base_classes=[],
                    methods=methods,
                    properties=[],
                    decorators=[],
                    docstring=interface_data.get("doc", ""),
                    line_number=interface_data["line"],
                    is_abstract=True,
                    access_level="public",
                )
            )

        return classes

    def _convert_imports(self, imports_data: List[Dict]) -> List[Import]:
        """Convert import data to Import objects."""
        imports = []
        for import_data in imports_data:
            imports.append(
                Import(
                    module=import_data["path"],
                    name=import_data.get("alias", ""),
                    alias=import_data.get("alias", ""),
                    line_number=import_data["line"],
                    import_type="import",
                    is_relative=False,
                    is_standard_library=self._is_standard_library(import_data["path"]),
                )
            )

        return imports

    def _convert_variables(self, variables_data: List[Dict]) -> List[Variable]:
        """Convert variable data to Variable objects."""
        variables = []
        for var_data in variables_data:
            variables.append(
                Variable(
                    name=var_data["name"],
                    type_hint=var_data.get("type", ""),
                    default_value=var_data.get("value", ""),
                    line_number=var_data["line"],
                    is_global=True,
                    is_constant=var_data.get("is_constant", False),
                )
            )

        return variables

    def _is_standard_library(self, import_path: str) -> bool:
        """Check if import is from Go standard library."""
        standard_packages = {
            "fmt",
            "os",
            "io",
            "strings",
            "strconv",
            "math",
            "time",
            "net",
            "http",
            "encoding/json",
            "encoding/xml",
            "database/sql",
            "context",
            "sync",
            "reflect",
            "unsafe",
            "syscall",
            "runtime",
            "testing",
            "log",
            "bufio",
        }

        # Check if it's a standard package or starts with a standard package
        parts = import_path.split("/")
        return parts[0] in standard_packages

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
