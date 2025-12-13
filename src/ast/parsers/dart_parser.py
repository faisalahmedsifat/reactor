"""Dart language AST parser implementation."""

import asyncio
import subprocess
import tempfile
import os
import time
import json
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


class DartParser(BaseParser):
    """Dart language parser using analyzer."""

    def __init__(self):
        super().__init__()
        self.language = Language.DART

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".dart"]

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """Parse Dart file and extract AST information."""
        start_time = time.time()

        try:
            # Use analyzer via a temporary Dart program
            ast_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_dart_ast, file_path, content
            )

            # Convert to ASTResult
            functions = self._convert_functions(ast_data.get("functions", []))
            classes = self._convert_classes(ast_data.get("classes", []))
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
                    "libraries": ast_data.get("libraries", []),
                    "mixins": ast_data.get("mixins", []),
                    "extensions": ast_data.get("extensions", []),
                    "enums": ast_data.get("enums", []),
                    "typedefs": ast_data.get("typedefs", []),
                    "top_level_variables": ast_data.get("top_level_variables", []),
                    "top_level_functions": ast_data.get("top_level_functions", []),
                    "null_safety": ast_data.get("null_safety", False),
                    "async_functions": ast_data.get("async_functions", []),
                    "generators": ast_data.get("generators", []),
                    "widgets": ast_data.get("widgets", []),
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

                async def error_result():
                    return ASTResult(
                        success=False,
                        language=self.language,
                        error=f"Cannot read file: {str(e)}",
                    )

                tasks.append(error_result())

        return await asyncio.gather(*tasks)

    def _extract_dart_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract AST information using Dart analyzer."""
        # Create a temporary Dart program to parse the file
        dart_parser_code = """
import 'dart:io';
import 'dart:convert';
import 'package:analyzer/dart/analysis/analysis_context_collection.dart';
import 'package:analyzer/dart/analysis/results.dart';
import 'package:analyzer/dart/ast/ast.dart';
import 'package:analyzer/dart/ast/visitor.dart';
import 'package:analyzer/file_system/physical_file_system.dart';

void main(List<String> args) async {
  if (args.length != 1) {
    print('Usage: dart run parser.dart <filename>');
    exit(1);
  }

  String filename = args[0];
  String content = await File(filename).readAsString();

  // Create analysis context
  var collection = AnalysisContextCollection(
    includedPaths: [Directory.current.path],
    resourceProvider: PhysicalResourceProvider.INSTANCE,
  );

  var context = collection.contextFor(filename);
  var session = context.currentSession;
  
  // Parse the file
  var parseResult = await session.getParsedUnit(filename);
  if (parseResult is! ParsedUnitResult) {
    print('Error parsing file');
    exit(1);
  }

  var unit = parseResult.unit;
  var extractor = DartAstExtractor();
  unit.accept(extractor);

  var result = {
    'functions': extractor.functions,
    'classes': extractor.classes,
    'imports': extractor.imports,
    'variables': extractor.variables,
    'libraries': extractor.libraries,
    'mixins': extractor.mixins,
    'extensions': extractor.extensions,
    'enums': extractor.enums,
    'typedefs': extractor.typedefs,
    'top_level_variables': extractor.topLevelVariables,
    'top_level_functions': extractor.topLevelFunctions,
    'null_safety': extractor.nullSafety,
    'async_functions': extractor.asyncFunctions,
    'generators': extractor.generators,
    'widgets': extractor.widgets,
  };

  print(JsonEncoder.withIndent('  ').convert(result));
}

class DartAstExtractor extends RecursiveAstVisitor<void> {
  List<Map<String, dynamic>> functions = [];
  List<Map<String, dynamic>> classes = [];
  List<Map<String, dynamic>> imports = [];
  List<Map<String, dynamic>> variables = [];
  List<String> libraries = [];
  List<Map<String, dynamic>> mixins = [];
  List<Map<String, dynamic>> extensions = [];
  List<Map<String, dynamic>> enums = [];
  List<Map<String, dynamic>> typedefs = [];
  List<Map<String, dynamic>> topLevelVariables = [];
  List<Map<String, dynamic>> topLevelFunctions = [];
  bool nullSafety = false;
  List<Map<String, dynamic>> asyncFunctions = [];
  List<Map<String, dynamic>> generators = [];
  List<Map<String, dynamic>> widgets = [];

  @override
  void visitFunctionDeclaration(FunctionDeclaration node) {
    var function = <String, dynamic>{
      'name': node.name.lexeme,
      'return_type': node.returnType?.toString() ?? 'void',
      'line': node.offset,
      'is_exported': node.isGetter || node.isSetter,
      'is_async': node.body?.isAsynchronous ?? false,
      'is_generator': node.body?.isGenerator ?? false,
      'is_getter': node.isGetter,
      'is_setter': node.isSetter,
      'parameters': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Extract parameters
    if (node.parameters != null) {
      for (var param in node.parameters.parameters) {
        function['parameters'].add({
          'name': param.name?.lexeme ?? '',
          'type': param.type?.toString() ?? 'dynamic',
          'is_optional': param.isOptional,
          'has_default': param.defaultValue != null,
          'default_value': param.defaultValue?.toString() ?? '',
        });
      }
    }

    functions.add(function);

    if (function['is_async']) {
      asyncFunctions.add(function);
    }
    if (function['is_generator']) {
      generators.add(function);
    }

    super.visitFunctionDeclaration(node);
  }

  @override
  void visitClassDeclaration(ClassDeclaration node) {
    var classInfo = <String, dynamic>{
      'name': node.name.lexeme,
      'line': node.offset,
      'is_exported': true, // Classes are public by default unless marked with _
      'is_abstract': node.abstractKeyword != null,
      'extends': node.extendsClause?.superclass.toString() ?? '',
      'implements': node.implementsClause?.interfaces.map((i) => i.toString()).toList() ?? [],
      'with': node.withClause?.mixinTypes.map((m) => m.toString()).toList() ?? [],
      'methods': [],
      'properties': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Check for null safety
    if (node.typeParameters?.typeParameters.any((tp) => tp.bound != null) ?? false) {
      nullSafety = true;
    }

    // Extract members
    for (var member in node.members) {
      if (member is MethodDeclaration) {
        var method = <String, dynamic>{
          'name': member.name.lexeme,
          'return_type': member.returnType?.toString() ?? 'void',
          'line': member.offset,
          'is_static': member.isStatic,
          'is_abstract': member.isAbstract,
          'is_async': member.body?.isAsynchronous ?? false,
          'is_generator': member.body?.isGenerator ?? false,
          'is_getter': member.isGetter,
          'is_setter': member.isSetter,
          'parameters': [],
          'documentation': _getDocumentation(member),
          'attributes': _getAttributes(member),
        };

        // Extract parameters
        if (member.parameters != null) {
          for (var param in member.parameters.parameters) {
            method['parameters'].add({
              'name': param.name?.lexeme ?? '',
              'type': param.type?.toString() ?? 'dynamic',
              'is_optional': param.isOptional,
              'has_default': param.defaultValue != null,
              'default_value': param.defaultValue?.toString() ?? '',
            });
          }
        }

        classInfo['methods'].add(method);
      } else if (member is FieldDeclaration) {
        for (var field in member.fields.variables) {
          var property = <String, dynamic>{
            'name': field.name.lexeme,
            'type': member.type?.toString() ?? 'dynamic',
            'line': field.offset,
            'is_static': member.isStatic,
            'is_final': member.isFinal,
            'is_late': member.isLate,
            'documentation': _getDocumentation(member),
            'attributes': _getAttributes(member),
          };
          classInfo['properties'].add(property);
        }
      }
    }

    // Check if it's a Flutter widget
    if (_isWidget(classInfo)) {
      widgets.add(classInfo);
    }

    classes.add(classInfo);
    super.visitClassDeclaration(node);
  }

  @override
  void visitMixinDeclaration(MixinDeclaration node) {
    var mixin = <String, dynamic>{
      'name': node.name.lexeme,
      'line': node.offset,
      'is_exported': true,
      'on': node.onClause?.superclassConstraints.map((c) => c.toString()).toList() ?? [],
      'implements': node.implementsClause?.interfaces.map((i) => i.toString()).toList() ?? [],
      'methods': [],
      'properties': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Extract members
    for (var member in node.members) {
      if (member is MethodDeclaration) {
        var method = <String, dynamic>{
          'name': member.name.lexeme,
          'return_type': member.returnType?.toString() ?? 'void',
          'line': member.offset,
          'is_static': member.isStatic,
          'is_abstract': member.isAbstract,
          'parameters': [],
          'documentation': _getDocumentation(member),
          'attributes': _getAttributes(member),
        };
        mixin['methods'].add(method);
      }
    }

    mixins.add(mixin);
    super.visitMixinDeclaration(node);
  }

  @override
  void visitExtensionDeclaration(ExtensionDeclaration node) {
    var extension = <String, dynamic>{
      'name': node.name?.lexeme ?? '',
      'extended_type': node.extendedType.toString(),
      'line': node.offset,
      'methods': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Extract members
    for (var member in node.members) {
      if (member is MethodDeclaration) {
        var method = <String, dynamic>{
          'name': member.name.lexeme,
          'return_type': member.returnType?.toString() ?? 'void',
          'line': member.offset,
          'is_static': member.isStatic,
          'parameters': [],
          'documentation': _getDocumentation(member),
          'attributes': _getAttributes(member),
        };
        extension['methods'].add(method);
      }
    }

    extensions.add(extension);
    super.visitExtensionDeclaration(node);
  }

  @override
  void visitEnumDeclaration(EnumDeclaration node) {
    var enumInfo = <String, dynamic>{
      'name': node.name.lexeme,
      'line': node.offset,
      'constants': node.constants.map((c) => c.name.lexeme).toList(),
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    enums.add(enumInfo);
    super.visitEnumDeclaration(node);
  }

  @override
  void visitFunctionTypeAlias(FunctionTypeAlias node) {
    var typedef = <String, dynamic>{
      'name': node.name.lexeme,
      'return_type': node.returnType.toString(),
      'line': node.offset,
      'parameters': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Extract parameters
    if (node.parameters != null) {
      for (var param in node.parameters.parameters) {
        typedef['parameters'].add({
          'name': param.name?.lexeme ?? '',
          'type': param.type?.toString() ?? 'dynamic',
        });
      }
    }

    typedefs.add(typedef);
    super.visitFunctionTypeAlias(node);
  }

  @override
  void visitImportDirective(ImportDirective node) {
    var importInfo = <String, dynamic>{
      'uri': node.uri.stringValue ?? '',
      'prefix': node.prefix?.name ?? '',
      'show_combinators': node.combinators.whereType<ShowCombinator>().map((c) => c.shownNames.map((n) => n.name).join(',')).toList(),
      'hide_combinators': node.combinators.whereType<HideCombinator>().map((c) => c.hiddenNames.map((n) => n.name).join(',')).toList(),
      'line': node.offset,
      'is_deferred': node.deferredKeyword != null,
    };

    imports.add(importInfo);
    super.visitImportDirective(node);
  }

  @override
  void visitTopLevelVariableDeclaration(TopLevelVariableDeclaration node) {
    for (var variable in node.variables.variables) {
      var varInfo = <String, dynamic>{
        'name': variable.name.lexeme,
        'type': node.type?.toString() ?? 'dynamic',
        'line': variable.offset,
        'is_final': node.isFinal,
        'is_const': node.isConst,
        'is_late': node.isLate,
        'value': variable.initializer?.toString() ?? '',
        'documentation': _getDocumentation(node),
        'attributes': _getAttributes(node),
      };

      variables.add(varInfo);
      topLevelVariables.add(varInfo);
    }
    super.visitTopLevelVariableDeclaration(node);
  }

  @override
  void visitTopLevelFunctionDeclaration(TopLevelFunctionDeclaration node) {
    var function = <String, dynamic>{
      'name': node.name.lexeme,
      'return_type': node.returnType?.toString() ?? 'void',
      'line': node.offset,
      'is_exported': !node.name.lexeme.startsWith('_'),
      'is_async': node.body?.isAsynchronous ?? false,
      'is_generator': node.body?.isGenerator ?? false,
      'is_getter': node.isGetter,
      'is_setter': node.isSetter,
      'parameters': [],
      'documentation': _getDocumentation(node),
      'attributes': _getAttributes(node),
    };

    // Extract parameters
    if (node.parameters != null) {
      for (var param in node.parameters.parameters) {
        function['parameters'].add({
          'name': param.name?.lexeme ?? '',
          'type': param.type?.toString() ?? 'dynamic',
          'is_optional': param.isOptional,
          'has_default': param.defaultValue != null,
          'default_value': param.defaultValue?.toString() ?? '',
        });
      }
    }

    functions.add(function);
    topLevelFunctions.add(function);

    if (function['is_async']) {
      asyncFunctions.add(function);
    }
    if (function['is_generator']) {
      generators.add(function);
    }

    super.visitTopLevelFunctionDeclaration(node);
  }

  String _getDocumentation(AstNode node) {
    // Extract documentation comments
    // This is a simplified implementation
    return '';
  }

  List<String> _getAttributes(AstNode node) {
    // Extract metadata annotations
    // This is a simplified implementation
    return [];
  }

  bool _isWidget(Map<String, dynamic> classInfo) {
    // Check if class extends or implements Widget
    var className = classInfo['name'] as String;
    var extends = classInfo['extends'] as String;
    var implements = classInfo['implements'] as List<String>;

    return className.contains('Widget') ||
           extends.contains('Widget') ||
           implements.any((i) => i.contains('Widget'));
  }
}
"""

        # Create pubspec.yaml
        pubspec_content = """
name: dart_ast_parser
description: A Dart AST parser for extracting code structure
version: 1.0.0

environment:
  sdk: '>=2.17.0 <4.0.0'

dependencies:
  analyzer: ^6.0.0

dev_dependencies:
  lints: ^3.0.0
"""

        # Create temporary directory for Dart project
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write pubspec.yaml
            with open(os.path.join(temp_dir, "pubspec.yaml"), "w") as f:
                f.write(pubspec_content)

            # Write parser.dart
            with open(os.path.join(temp_dir, "bin", "parser.dart"), "w") as f:
                f.write(dart_parser_code)

            # Write target Dart file
            target_file = os.path.join(temp_dir, "target.dart")
            with open(target_file, "w") as f:
                f.write(content)

            try:
                # Get dependencies
                subprocess.run(
                    ["dart", "pub", "get"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Run Dart parser
                result = subprocess.run(
                    ["dart", "run", "bin/parser.dart", target_file],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    # Fallback to simpler parsing if analyzer fails
                    return self._fallback_parse(content)

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                # Fallback to simpler parsing
                return self._fallback_parse(content)

    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        """Fallback parsing using regex patterns when analyzer is not available."""
        import re

        functions = []
        classes = []
        imports = []
        variables = []

        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Simple function detection
            func_match = re.match(
                r"(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:async\s*)?(?:\{|=>)", line
            )
            if func_match and not line.startswith("//") and not line.startswith("/*"):
                func_name = func_match.group(1)
                if func_name not in ["if", "while", "for", "switch", "catch"]:
                    functions.append(
                        {
                            "name": func_name,
                            "return_type": "dynamic",  # Would need more complex parsing
                            "line": i,
                            "is_exported": not func_name.startswith("_"),
                            "is_async": "async" in line,
                            "is_generator": "sync*" in line or "async*" in line,
                            "is_getter": "get " in line,
                            "is_setter": "set " in line,
                            "parameters": [],
                            "documentation": "",
                            "attributes": [],
                        }
                    )

            # Simple class detection
            class_match = re.match(r"(?:abstract\s+)?class\s+(\w+)", line)
            if class_match:
                class_name = class_match.group(1)
                classes.append(
                    {
                        "name": class_name,
                        "line": i,
                        "is_exported": not class_name.startswith("_"),
                        "is_abstract": "abstract" in line,
                        "extends": "",
                        "implements": [],
                        "with": [],
                        "methods": [],
                        "properties": [],
                        "documentation": "",
                        "attributes": [],
                    }
                )

            # Simple import detection
            import_match = re.match(r'import\s+[\'"]([^\'"]+)[\'"]', line)
            if import_match:
                import_uri = import_match.group(1)
                imports.append(
                    {
                        "uri": import_uri,
                        "prefix": "",
                        "show_combinators": [],
                        "hide_combinators": [],
                        "line": i,
                        "is_deferred": "deferred" in line,
                    }
                )

            # Simple variable detection
            var_match = re.match(r"(?:final|const|var|late)?\s*(\w+)\s+(\w+)", line)
            if var_match:
                var_type = var_match.group(1)
                var_name = var_match.group(2)
                variables.append(
                    {
                        "name": var_name,
                        "type": var_type,
                        "line": i,
                        "is_final": "final" in line,
                        "is_const": "const" in line,
                        "is_late": "late" in line,
                        "value": "",
                        "documentation": "",
                        "attributes": [],
                    }
                )

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "variables": variables,
            "libraries": [],
            "mixins": [],
            "extensions": [],
            "enums": [],
            "typedefs": [],
            "top_level_variables": variables,
            "top_level_functions": functions,
            "null_safety": False,
            "async_functions": [],
            "generators": [],
            "widgets": [],
        }

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
                        default_value=param_data.get("default_value", ""),
                        is_optional=param_data.get("is_optional", False),
                        docstring=None,
                    )
                )

            functions.append(
                Function(
                    name=func_data["name"],
                    parameters=parameters,
                    return_type=func_data["return_type"],
                    decorators=func_data.get("attributes", []),
                    docstring=func_data.get("documentation", ""),
                    line_number=func_data["line"],
                    complexity_score=1,
                    is_async=func_data.get("is_async", False),
                    is_method=False,
                    class_name=None,
                )
            )

        return functions

    def _convert_classes(self, classes_data: List[Dict]) -> List[Class]:
        """Convert class data to Class objects."""
        classes = []
        for class_data in classes_data:
            methods = []
            for method_data in class_data.get("methods", []):
                parameters = []
                for param_data in method_data.get("parameters", []):
                    parameters.append(
                        Parameter(
                            name=param_data["name"],
                            type_hint=param_data["type"],
                            default_value=param_data.get("default_value", ""),
                            is_optional=param_data.get("is_optional", False),
                            docstring=None,
                        )
                    )

                methods.append(
                    Method(
                        name=method_data["name"],
                        parameters=parameters,
                        return_type=method_data["return_type"],
                        decorators=method_data.get("attributes", []),
                        docstring=method_data.get("documentation", ""),
                        line_number=method_data["line"],
                        access_level=(
                            "public"
                            if method_data.get("is_exported", True)
                            else "private"
                        ),
                        is_static=method_data.get("is_static", False),
                        is_async=method_data.get("is_async", False),
                    )
                )

            properties = []
            for prop_data in class_data.get("properties", []):
                properties.append(
                    Property(
                        name=prop_data["name"],
                        type_hint=prop_data["type"],
                        line_number=prop_data["line"],
                        default_value=None,
                        access_level=(
                            "public"
                            if prop_data.get("is_exported", True)
                            else "private"
                        ),
                        docstring=prop_data.get("documentation", ""),
                        is_property=True,
                    )
                )

            classes.append(
                Class(
                    name=class_data["name"],
                    base_classes=(
                        [class_data.get("extends", "")]
                        if class_data.get("extends")
                        else []
                    ),
                    methods=methods,
                    properties=properties,
                    decorators=class_data.get("attributes", []),
                    docstring=class_data.get("documentation", ""),
                    line_number=class_data["line"],
                    is_abstract=class_data.get("is_abstract", False),
                    access_level=(
                        "public" if class_data.get("is_exported", True) else "private"
                    ),
                )
            )

        return classes

    def _convert_imports(self, imports_data: List[Dict]) -> List[Import]:
        """Convert import data to Import objects."""
        imports = []
        for import_data in imports_data:
            imports.append(
                Import(
                    module=import_data["uri"],
                    name="",
                    alias=import_data.get("prefix", ""),
                    line_number=import_data["line"],
                    import_type="import",
                    is_relative=import_data["uri"].startswith("."),
                    is_standard_library=self._is_standard_library(import_data["uri"]),
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
                    type_hint=var_data["type"],
                    default_value=var_data.get("value", ""),
                    line_number=var_data["line"],
                    is_global=True,
                    is_constant=var_data.get("is_const", False),
                )
            )

        return variables

    def _is_standard_library(self, import_uri: str) -> bool:
        """Check if import is from Dart standard library."""
        std_libraries = {
            "dart:",
            "dart:async",
            "dart:collection",
            "dart:convert",
            "dart:core",
            "dart:io",
            "dart:isolate",
            "dart:math",
            "dart:mirrors",
            "dart:typed_data",
            "dart:ffi",
        }

        return any(import_uri.startswith(lib) for lib in std_libraries)

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
