"""C# language AST parser implementation."""

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


class CSharpParser(BaseParser):
    """C# language parser using Roslyn APIs."""

    def __init__(self):
        super().__init__()
        self.language = Language.CSHARP

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return [".cs"]

    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """Parse C# file and extract AST information."""
        start_time = time.time()

        try:
            # Use Roslyn via a temporary C# program
            ast_data = await asyncio.get_event_loop().run_in_executor(
                None, self._extract_csharp_ast, file_path, content
            )

            # Convert to ASTResult
            functions = self._convert_functions(ast_data.get("methods", []))
            classes = self._convert_classes(ast_data.get("classes", []))
            imports = self._convert_using_directives(
                ast_data.get("using_directives", [])
            )
            variables = self._convert_variables(ast_data.get("fields", []))

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
                    "interfaces": ast_data.get("interfaces", []),
                    "enums": ast_data.get("enums", []),
                    "delegates": ast_data.get("delegates", []),
                    "events": ast_data.get("events", []),
                    "properties": ast_data.get("properties", []),
                    "indexers": ast_data.get("indexers", []),
                    "records": ast_data.get("records", []),
                    "attributes": ast_data.get("attributes", []),
                    "linq_expressions": ast_data.get("linq_expressions", []),
                    "async_methods": ast_data.get("async_methods", []),
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

    def _extract_csharp_ast(self, file_path: str, content: str) -> Dict[str, Any]:
        """Extract AST information using Roslyn."""
        # Create a temporary C# program to parse the file
        csharp_parser_code = """
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using System.Text.Json;

public class CSharpAstParser
{
    public class MethodInfo
    {
        public string Name { get; set; }
        public string ReturnType { get; set; }
        public List<ParameterInfo> Parameters { get; set; } = new List<ParameterInfo>();
        public int Line { get; set; }
        public bool IsPublic { get; set; }
        public bool IsPrivate { get; set; }
        public bool IsProtected { get; set; }
        public bool IsInternal { get; set; }
        public bool IsStatic { get; set; }
        public bool IsVirtual { get; set; }
        public bool IsOverride { get; set; }
        public bool IsAbstract { get; set; }
        public bool IsAsync { get; set; }
        public bool IsExtension { get; set; }
        public List<string> Attributes { get; set; } = new List<string>();
        public string Documentation { get; set; }
        public string GenericParameters { get; set; }
    }

    public class ParameterInfo
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public bool HasDefaultValue { get; set; }
        public string DefaultValue { get; set; }
        public bool IsRef { get; set; }
        public bool IsOut { get; set; }
        public bool IsParams { get; set; }
    }

    public class ClassInfo
    {
        public string Name { get; set; }
        public List<string> BaseTypes { get; set; } = new List<string>();
        public List<MethodInfo> Methods { get; set; } = new List<MethodInfo>();
        public List<PropertyInfo> Properties { get; set; } = new List<PropertyInfo>();
        public List<FieldInfo> Fields { get; set; } = new List<FieldInfo>();
        public int Line { get; set; }
        public bool IsPublic { get; set; }
        public bool IsInternal { get; set; }
        public bool IsAbstract { get; set; }
        public bool IsSealed { get; set; }
        public bool IsStatic { get; set; }
        public bool IsPartial { get; set; }
        public bool IsRecord { get; set; }
        public List<string> Attributes { get; set; } = new List<string>();
        public string Documentation { get; set; }
        public string GenericParameters { get; set; }
        public string Namespace { get; set; }
    }

    public class PropertyInfo
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public bool HasGetter { get; set; }
        public bool HasSetter { get; set; }
        public bool IsPublic { get; set; }
        public bool IsPrivate { get; set; }
        public bool IsProtected { get; set; }
        public bool IsInternal { get; set; }
        public bool IsStatic { get; set; }
        public bool IsVirtual { get; set; }
        public bool IsOverride { get; set; }
        public List<string> Attributes { get; set; } = new List<string>();
        public string Documentation { get; set; }
    }

    public class FieldInfo
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public bool IsPublic { get; set; }
        public bool IsPrivate { get; set; }
        public bool IsProtected { get; set; }
        public bool IsInternal { get; set; }
        public bool IsStatic { get; set; }
        public bool IsReadonly { get; set; }
        public bool IsConst { get; set; }
        public string DefaultValue { get; set; }
        public List<string> Attributes { get; set; } = new List<string>();
        public string Documentation { get; set; }
    }

    public class UsingDirectiveInfo
    {
        public string Name { get; set; }
        public string Alias { get; set; }
        public bool IsStatic { get; set; }
        public bool IsGlobal { get; set; }
        public int Line { get; set; }
    }

    public static void Main(string[] args)
    {
        if (args.Length != 1)
        {
            Console.WriteLine("Usage: CSharpAstParser <filename>");
            Environment.Exit(1);
        }

        string filename = args[0];
        string content = File.ReadAllText(filename);

        var tree = CSharpSyntaxTree.ParseText(content);
        var root = tree.GetCompilationUnitRoot();

        var result = new Dictionary<string, object>
        {
            ["namespaces"] = new List<string>(),
            ["classes"] = new List<ClassInfo>(),
            ["interfaces"] = new List<ClassInfo>(),
            ["enums"] = new List<ClassInfo>(),
            ["methods"] = new List<MethodInfo>(),
            ["properties"] = new List<PropertyInfo>(),
            ["fields"] = new List<FieldInfo>(),
            ["using_directives"] = new List<UsingDirectiveInfo>(),
            ["delegates"] = new List<ClassInfo>(),
            ["events"] = new List<PropertyInfo>(),
            ["indexers"] = new List<PropertyInfo>(),
            ["records"] = new List<ClassInfo>(),
            ["attributes"] = new List<string>(),
            ["linq_expressions"] = new List<string>(),
            ["async_methods"] = new List<MethodInfo>()
        };

        // Extract using directives
        foreach (var usingDirective in root.Usings)
        {
            var usingInfo = new UsingDirectiveInfo
            {
                Name = usingDirective.Name.ToString(),
                Alias = usingDirective.Alias?.ToString(),
                IsStatic = usingDirective.StaticKeyword.IsKind(SyntaxKind.StaticKeyword),
                IsGlobal = usingDirective.GlobalKeyword.IsKind(SyntaxKind.GlobalKeyword),
                Line = usingDirective.GetLocation().GetLineSpan().StartLinePosition.Line + 1
            };
            ((List<UsingDirectiveInfo>)result["using_directives"]).Add(usingInfo);
        }

        // Extract namespaces
        foreach (var member in root.Members)
        {
            if (member is NamespaceDeclarationSyntax namespaceDecl)
            {
                ((List<string>)result["namespaces"]).Add(namespaceDecl.Name.ToString());
                ProcessNamespaceMembers(namespaceDecl.Members, result, namespaceDecl.Name.ToString());
            }
            else
            {
                ProcessNamespaceMembers(new List<MemberDeclarationSyntax> { member }, result, "");
            }
        }

        var jsonOptions = new JsonSerializerOptions { WriteIndented = true };
        Console.WriteLine(JsonSerializer.Serialize(result, jsonOptions));
    }

    static void ProcessNamespaceMembers(IEnumerable<MemberDeclarationSyntax> members, Dictionary<string, object> result, string namespaceName)
    {
        foreach (var member in members)
        {
            switch (member)
            {
                case ClassDeclarationSyntax classDecl:
                    ProcessClass(classDecl, result, namespaceName);
                    break;
                case InterfaceDeclarationSyntax interfaceDecl:
                    ProcessInterface(interfaceDecl, result, namespaceName);
                    break;
                case EnumDeclarationSyntax enumDecl:
                    ProcessEnum(enumDecl, result, namespaceName);
                    break;
                case DelegateDeclarationSyntax delegateDecl:
                    ProcessDelegate(delegateDecl, result, namespaceName);
                    break;
                case MethodDeclarationSyntax methodDecl:
                    var methodInfo = ProcessMethod(methodDecl);
                    ((List<MethodInfo>)result["methods"]).Add(methodInfo);
                    break;
                case PropertyDeclarationSyntax propertyDecl:
                    var propertyInfo = ProcessProperty(propertyDecl);
                    ((List<PropertyInfo>)result["properties"]).Add(propertyInfo);
                    break;
                case FieldDeclarationSyntax fieldDecl:
                    var fieldInfos = ProcessField(fieldDecl);
                    ((List<FieldInfo>)result["fields"]).AddRange(fieldInfos);
                    break;
            }
        }
    }

    static void ProcessClass(ClassDeclarationSyntax classDecl, Dictionary<string, object> result, string namespaceName)
    {
        var classInfo = new ClassInfo
        {
            Name = classDecl.Identifier.Text,
            Line = classDecl.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
            IsPublic = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsInternal = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            IsAbstract = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.AbstractKeyword)),
            IsSealed = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.SealedKeyword)),
            IsStatic = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword)),
            IsPartial = classDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PartialKeyword)),
            IsRecord = classDecl.IsKind(SyntaxKind.RecordDeclaration),
            Namespace = namespaceName,
            Documentation = GetDocumentation(classDecl),
            GenericParameters = GetGenericParameters(classDecl.TypeParameterList)
        };

        // Extract base types
        if (classDecl.BaseList != null)
        {
            foreach (var baseType in classDecl.BaseList.Types)
            {
                classInfo.BaseTypes.Add(baseType.Type.ToString());
            }
        }

        // Extract attributes
        classInfo.Attributes = GetAttributes(classDecl.AttributeLists);

        // Process members
        foreach (var member in classDecl.Members)
        {
            switch (member)
            {
                case MethodDeclarationSyntax methodDecl:
                    var methodInfo = ProcessMethod(methodDecl);
                    classInfo.Methods.Add(methodInfo);
                    if (methodInfo.IsAsync)
                    {
                        ((List<MethodInfo>)result["async_methods"]).Add(methodInfo);
                    }
                    break;
                case PropertyDeclarationSyntax propertyDecl:
                    var propertyInfo = ProcessProperty(propertyDecl);
                    classInfo.Properties.Add(propertyInfo);
                    break;
                case FieldDeclarationSyntax fieldDecl:
                    var fieldInfos = ProcessField(fieldDecl);
                    classInfo.Fields.AddRange(fieldInfos);
                    break;
            }
        }

        if (classInfo.IsRecord)
        {
            ((List<ClassInfo>)result["records"]).Add(classInfo);
        }
        else
        {
            ((List<ClassInfo>)result["classes"]).Add(classInfo);
        }
    }

    static void ProcessInterface(InterfaceDeclarationSyntax interfaceDecl, Dictionary<string, object> result, string namespaceName)
    {
        var interfaceInfo = new ClassInfo
        {
            Name = interfaceDecl.Identifier.Text,
            Line = interfaceDecl.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
            IsPublic = interfaceDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsInternal = interfaceDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            Namespace = namespaceName,
            Documentation = GetDocumentation(interfaceDecl),
            GenericParameters = GetGenericParameters(interfaceDecl.TypeParameterList)
        };

        // Extract base interfaces
        if (interfaceDecl.BaseList != null)
        {
            foreach (var baseType in interfaceDecl.BaseList.Types)
            {
                interfaceInfo.BaseTypes.Add(baseType.Type.ToString());
            }
        }

        // Extract attributes
        interfaceInfo.Attributes = GetAttributes(interfaceDecl.AttributeLists);

        // Process members
        foreach (var member in interfaceDecl.Members)
        {
            switch (member)
            {
                case MethodDeclarationSyntax methodDecl:
                    var methodInfo = ProcessMethod(methodDecl);
                    interfaceInfo.Methods.Add(methodInfo);
                    break;
                case PropertyDeclarationSyntax propertyDecl:
                    var propertyInfo = ProcessProperty(propertyDecl);
                    interfaceInfo.Properties.Add(propertyInfo);
                    break;
            }
        }

        ((List<ClassInfo>)result["interfaces"]).Add(interfaceInfo);
    }

    static void ProcessEnum(EnumDeclarationSyntax enumDecl, Dictionary<string, object> result, string namespaceName)
    {
        var enumInfo = new ClassInfo
        {
            Name = enumDecl.Identifier.Text,
            Line = enumDecl.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
            IsPublic = enumDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsInternal = enumDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            Namespace = namespaceName,
            Documentation = GetDocumentation(enumDecl)
        };

        // Extract attributes
        enumInfo.Attributes = GetAttributes(enumDecl.AttributeLists);

        ((List<ClassInfo>)result["enums"]).Add(enumInfo);
    }

    static void ProcessDelegate(DelegateDeclarationSyntax delegateDecl, Dictionary<string, object> result, string namespaceName)
    {
        var delegateInfo = new ClassInfo
        {
            Name = delegateDecl.Identifier.Text,
            Line = delegateDecl.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
            IsPublic = delegateDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsInternal = delegateDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            Namespace = namespaceName,
            Documentation = GetDocumentation(delegateDecl),
            GenericParameters = GetGenericParameters(delegateDecl.TypeParameterList)
        };

        // Extract attributes
        delegateInfo.Attributes = GetAttributes(delegateDecl.AttributeLists);

        ((List<ClassInfo>)result["delegates"]).Add(delegateInfo);
    }

    static MethodInfo ProcessMethod(MethodDeclarationSyntax methodDecl)
    {
        var methodInfo = new MethodInfo
        {
            Name = methodDecl.Identifier.Text,
            ReturnType = methodDecl.ReturnType.ToString(),
            Line = methodDecl.GetLocation().GetLineSpan().StartLinePosition.Line + 1,
            IsPublic = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsPrivate = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PrivateKeyword)),
            IsProtected = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.ProtectedKeyword)),
            IsInternal = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            IsStatic = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword)),
            IsVirtual = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.VirtualKeyword)),
            IsOverride = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.OverrideKeyword)),
            IsAbstract = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.AbstractKeyword)),
            IsAsync = methodDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.AsyncKeyword)),
            IsExtension = IsExtensionMethod(methodDecl),
            Documentation = GetDocumentation(methodDecl),
            GenericParameters = GetGenericParameters(methodDecl.TypeParameterList)
        };

        // Extract attributes
        methodInfo.Attributes = GetAttributes(methodDecl.AttributeLists);

        // Extract parameters
        foreach (var param in methodDecl.ParameterList.Parameters)
        {
            var paramInfo = new ParameterInfo
            {
                Name = param.Identifier.Text,
                Type = param.Type?.ToString() ?? "",
                HasDefaultValue = param.Default != null,
                DefaultValue = param.Default?.Value.ToString(),
                IsRef = param.Modifiers.Any(m => m.IsKind(SyntaxKind.RefKeyword)),
                IsOut = param.Modifiers.Any(m => m.IsKind(SyntaxKind.OutKeyword)),
                IsParams = param.Modifiers.Any(m => m.IsKind(SyntaxKind.ParamsKeyword))
            };
            methodInfo.Parameters.Add(paramInfo);
        }

        return methodInfo;
    }

    static PropertyInfo ProcessProperty(PropertyDeclarationSyntax propertyDecl)
    {
        var propertyInfo = new PropertyInfo
        {
            Name = propertyDecl.Identifier.Text,
            Type = propertyDecl.Type.ToString(),
            HasGetter = propertyDecl.AccessorList?.Accessors.Any(a => a.IsKind(SyntaxKind.GetAccessorDeclaration)) ?? false,
            HasSetter = propertyDecl.AccessorList?.Accessors.Any(a => a.IsKind(SyntaxKind.SetAccessorDeclaration)) ?? false,
            IsPublic = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
            IsPrivate = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PrivateKeyword)),
            IsProtected = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.ProtectedKeyword)),
            IsInternal = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
            IsStatic = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword)),
            IsVirtual = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.VirtualKeyword)),
            IsOverride = propertyDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.OverrideKeyword)),
            Documentation = GetDocumentation(propertyDecl)
        };

        // Extract attributes
        propertyInfo.Attributes = GetAttributes(propertyDecl.AttributeLists);

        return propertyInfo;
    }

    static List<FieldInfo> ProcessField(FieldDeclarationSyntax fieldDecl)
    {
        var fieldInfos = new List<FieldInfo>();
        var type = fieldDecl.Declaration.Type.ToString();

        foreach (var variable in fieldDecl.Declaration.Variables)
        {
            var fieldInfo = new FieldInfo
            {
                Name = variable.Identifier.Text,
                Type = type,
                IsPublic = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PublicKeyword)),
                IsPrivate = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.PrivateKeyword)),
                IsProtected = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.ProtectedKeyword)),
                IsInternal = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.InternalKeyword)),
                IsStatic = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.StaticKeyword)),
                IsReadonly = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.ReadOnlyKeyword)),
                IsConst = fieldDecl.Modifiers.Any(m => m.IsKind(SyntaxKind.ConstKeyword)),
                DefaultValue = variable.Initializer?.Value.ToString(),
                Documentation = GetDocumentation(fieldDecl)
            };

            // Extract attributes
            fieldInfo.Attributes = GetAttributes(fieldDecl.AttributeLists);

            fieldInfos.Add(fieldInfo);
        }

        return fieldInfos;
    }

    static bool IsExtensionMethod(MethodDeclarationSyntax methodDecl)
    {
        return methodDecl.ParameterList.Parameters.Count > 0 &&
               methodDecl.ParameterList.Parameters[0].Modifiers.Any(m => m.IsKind(SyntaxKind.ThisKeyword));
    }

    static string GetDocumentation(SyntaxNode node)
    {
        var trivia = node.GetLeadingTrivia();
        foreach (var triviaNode in trivia)
        {
            if (triviaNode.IsKind(SyntaxKind.SingleLineDocumentationCommentTrivia) ||
                triviaNode.IsKind(SyntaxKind.MultiLineDocumentationCommentTrivia))
            {
                return triviaNode.ToFullString().Trim();
            }
        }
        return "";
    }

    static List<string> GetAttributes(SyntaxList<AttributeListSyntax> attributeLists)
    {
        var attributes = new List<string>();
        foreach (var attributeList in attributeLists)
        {
            foreach (var attribute in attributeList.Attributes)
            {
                attributes.Add(attribute.ToString());
            }
        }
        return attributes;
    }

    static string GetGenericParameters(TypeParameterListSyntax typeParameterList)
    {
        if (typeParameterList == null) return "";
        return string.Join(", ", typeParameterList.Parameters.Select(p => p.ToString()));
    }
}
"""

        # Create project file
        csproj_content = """
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <Nullable>enable</Nullable>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.CodeAnalysis.CSharp" Version="4.4.0" />
  </ItemGroup>

</Project>
"""

        # Create temporary directory for C# project
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write .csproj file
            with open(os.path.join(temp_dir, "CSharpAstParser.csproj"), "w") as f:
                f.write(csproj_content)

            # Write Program.cs
            with open(os.path.join(temp_dir, "Program.cs"), "w") as f:
                f.write(csharp_parser_code)

            # Write target C# file
            target_file = os.path.join(temp_dir, "target.cs")
            with open(target_file, "w") as f:
                f.write(content)

            try:
                # Build and run C# parser
                subprocess.run(
                    ["dotnet", "build", "-c", "Release"],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                result = subprocess.run(
                    ["dotnet", "run", "-c", "Release", "--", target_file],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    # Fallback to simpler parsing if Roslyn fails
                    return self._fallback_parse(content)

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                # Fallback to simpler parsing
                return self._fallback_parse(content)

    def _fallback_parse(self, content: str) -> Dict[str, Any]:
        """Fallback parsing using regex patterns when Roslyn is not available."""
        import re

        methods = []
        classes = []
        using_directives = []
        fields = []
        namespaces = []

        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Simple method detection
            method_match = re.match(
                r"(?:public|private|protected|internal)?\s*(?:static|virtual|override|abstract)?\s*(?:async)?\s*(\w+(?:<[^>]+>)?)\s+(\w+)\s*\([^)]*\)",
                line,
            )
            if method_match and not line.startswith("//") and not line.startswith("/*"):
                return_type = method_match.group(1)
                method_name = method_match.group(2)

                methods.append(
                    {
                        "name": method_name,
                        "return_type": return_type,
                        "line": i,
                        "is_public": "public" in line,
                        "is_private": "private" in line,
                        "is_protected": "protected" in line,
                        "is_internal": "internal" in line,
                        "is_static": "static" in line,
                        "is_virtual": "virtual" in line,
                        "is_override": "override" in line,
                        "is_abstract": "abstract" in line,
                        "is_async": "async" in line,
                        "is_extension": False,
                        "parameters": [],
                        "attributes": [],
                        "documentation": "",
                        "generic_parameters": "",
                    }
                )

            # Simple class detection
            class_match = re.match(
                r"(?:public|private|protected|internal)?\s*(?:static|abstract|sealed)?\s*(?:partial)?\s*(?:record)?\s*class\s+(\w+)",
                line,
            )
            if class_match:
                class_name = class_match.group(1)
                classes.append(
                    {
                        "name": class_name,
                        "base_types": [],
                        "methods": [],
                        "properties": [],
                        "fields": [],
                        "line": i,
                        "is_public": "public" in line,
                        "is_internal": "internal" in line,
                        "is_abstract": "abstract" in line,
                        "is_sealed": "sealed" in line,
                        "is_static": "static" in line,
                        "is_partial": "partial" in line,
                        "is_record": "record" in line,
                        "attributes": [],
                        "documentation": "",
                        "generic_parameters": "",
                        "namespace": "",
                    }
                )

            # Simple using directive detection
            using_match = re.match(r"using\s+(?:static\s+)?([^;]+)", line)
            if using_match:
                using_name = using_match.group(1).strip()
                using_directives.append(
                    {
                        "name": using_name,
                        "alias": "",
                        "is_static": "static" in line,
                        "is_global": "global" in line,
                        "line": i,
                    }
                )

            # Simple namespace detection
            namespace_match = re.match(r"namespace\s+([^\\s{]+)", line)
            if namespace_match:
                namespace_name = namespace_match.group(1)
                namespaces.append(namespace_name)

        return {
            "namespaces": namespaces,
            "classes": classes,
            "interfaces": [],
            "enums": [],
            "methods": methods,
            "properties": [],
            "fields": fields,
            "using_directives": using_directives,
            "delegates": [],
            "events": [],
            "indexers": [],
            "records": [],
            "attributes": [],
            "linq_expressions": [],
            "async_methods": [],
        }

    def _convert_functions(self, methods_data: List[Dict]) -> List[Function]:
        """Convert method data to Function objects."""
        functions = []
        for method_data in methods_data:
            parameters = []
            for param_data in method_data.get("parameters", []):
                parameters.append(
                    Parameter(
                        name=param_data["name"],
                        type_hint=param_data["type"],
                        default_value=param_data.get("default_value", ""),
                        is_optional=param_data.get("has_default_value", False),
                        docstring=None,
                    )
                )

            functions.append(
                Function(
                    name=method_data["name"],
                    parameters=parameters,
                    return_type=method_data["return_type"],
                    decorators=method_data.get("attributes", []),
                    docstring=method_data.get("documentation", ""),
                    line_number=method_data["line"],
                    complexity_score=1,
                    is_async=method_data.get("is_async", False),
                    is_method=True,
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
                            is_optional=param_data.get("has_default_value", False),
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
                        access_level=self._get_access_level(method_data),
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
                        access_level=self._get_access_level(prop_data),
                        docstring=prop_data.get("documentation", ""),
                        is_property=True,
                    )
                )

            classes.append(
                Class(
                    name=class_data["name"],
                    base_classes=class_data.get("base_types", []),
                    methods=methods,
                    properties=properties,
                    decorators=class_data.get("attributes", []),
                    docstring=class_data.get("documentation", ""),
                    line_number=class_data["line"],
                    is_abstract=class_data.get("is_abstract", False),
                    access_level=self._get_access_level(class_data),
                )
            )

        return classes

    def _convert_using_directives(self, using_data: List[Dict]) -> List[Import]:
        """Convert using directive data to Import objects."""
        imports = []
        for using_info in using_data:
            imports.append(
                Import(
                    module=using_info["name"],
                    name="",
                    alias=using_info.get("alias", ""),
                    line_number=using_info["line"],
                    import_type="using",
                    is_relative=False,
                    is_standard_library=self._is_standard_library(using_info["name"]),
                )
            )

        return imports

    def _convert_variables(self, fields_data: List[Dict]) -> List[Variable]:
        """Convert field data to Variable objects."""
        variables = []
        for field_data in fields_data:
            variables.append(
                Variable(
                    name=field_data["name"],
                    type_hint=field_data["type"],
                    default_value=field_data.get("default_value", ""),
                    line_number=field_data["line"],
                    is_global=False,  # Fields are class members
                    is_constant=field_data.get("is_const", False),
                )
            )

        return variables

    def _get_access_level(self, member_data: Dict) -> str:
        """Determine access level from member data."""
        if member_data.get("is_public", False):
            return "public"
        elif member_data.get("is_private", False):
            return "private"
        elif member_data.get("is_protected", False):
            return "protected"
        elif member_data.get("is_internal", False):
            return "internal"
        else:
            return "public"  # Default

    def _is_standard_library(self, import_name: str) -> bool:
        """Check if import is from .NET standard library."""
        std_namespaces = {
            "System",
            "Microsoft",
            "Newtonsoft",
            "Linq",
            "Collections",
            "Generic",
            "IO",
            "Text",
            "Threading",
            "Tasks",
            "Net",
            "Web",
            "Http",
            "Json",
            "Xml",
            "Data",
            "Drawing",
            "Windows",
            "Forms",
            "WPF",
            "Console",
        }

        parts = import_name.split(".")
        return parts[0] in std_namespaces

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
