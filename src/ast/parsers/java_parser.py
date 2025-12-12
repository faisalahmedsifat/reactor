"""
src/ast/parsers/java_parser.py

Java AST parser using regex-based parsing with fallback support.
"""

import re
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from src.ast.core.base_parser import BaseParser, ASTResult, Language, Function, Class, Import, Variable, Parameter


class JavaASTParser(BaseParser):
    """Java AST parser using regex-based parsing"""
    
    def __init__(self):
        super().__init__()
        self.language = Language.JAVA
        
    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """
        Parse Java file content into AST
        
        Args:
            file_path: Path to the Java file
            content: File content as string
            
        Returns:
            ASTResult with parsed structure
        """
        try:
            return self._parse_with_regex(file_path, content)
                
        except Exception as e:
            return ASTResult(
                success=False,
                language=Language.JAVA,
                error=f"Parse error: {str(e)}",
                parse_time_ms=0
            )
    
    def _parse_with_regex(self, file_path: str, content: str) -> ASTResult:
        """Parse using regex for Java code analysis"""
        try:
            # Extract package declaration
            package_match = re.search(r'package\s+([\w.]+)\s*;', content)
            package_name = package_match.group(1) if package_match else ""
            
            # Extract classes
            classes = self._extract_classes(content)
            
            # Extract functions (methods outside classes)
            functions = self._extract_functions(content)
            
            # Extract imports
            imports = self._extract_imports(content)
            
            # Extract variables (fields and global variables)
            variables = self._extract_variables(content)
            
            # Build metadata
            metadata = {
                "file_path": file_path,
                "encoding": "utf-8",
                "parser": "regex_based",
                "node_count": len(classes) + len(functions) + len(variables),
                "complexity_score": sum(f.complexity_score for f in functions),
                "package": package_name
            }
            
            return ASTResult(
                success=True,
                language=Language.JAVA,
                ast_root=None,  # No actual AST in regex parsing
                functions=functions,
                classes=classes,
                imports=imports,
                variables=variables,
                metadata=metadata,
                parse_time_ms=0
            )
            
        except Exception as e:
            return ASTResult(
                success=False,
                language=Language.JAVA,
                error=f"Regex parse error: {str(e)}",
                parse_time_ms=0
            )
    
    def _extract_classes(self, content: str) -> List[Class]:
        """Extract class definitions using regex"""
        classes = []
        
        # Enhanced class pattern with better handling of modifiers and generics
        class_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)(?:<[^>]+>)?(?:\s+extends\s+(\w+)(?:<[^>]+>)?)?(?:\s+implements\s+([^{]+))?'
        
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            class_name = match.group(1)
            extends = match.group(2) if match.group(2) else None
            implements = match.group(3) if match.group(3) else None
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Extract class content
            class_start = match.start()
            brace_count = 0
            class_end = class_start
            
            for i, char in enumerate(content[class_start:], class_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i + 1
                        break
            
            class_content = content[class_start:class_end]
            
            # Extract methods from class
            methods = self._extract_class_methods(class_content, line_num)
            
            # Extract fields from class
            properties = self._extract_class_fields(class_content, line_num)
            
            # Build inheritance list
            inheritance = []
            if extends:
                inheritance.append(extends)
            if implements:
                # Clean up implements clause
                impl_list = [impl.strip() for impl in implements.split(',')]
                inheritance.extend(impl_list)
            
            # Check if abstract
            is_abstract = 'abstract' in match.group(0)
            
            # Determine access level
            access_level = "public"
            if 'private' in match.group(0):
                access_level = "private"
            elif 'protected' in match.group(0):
                access_level = "protected"
            
            classes.append(Class(
                name=class_name,
                line_number=line_num,
                base_classes=inheritance,
                methods=methods,
                properties=properties,
                decorators=[],
                docstring="",
                is_abstract=is_abstract,
                access_level=access_level
            ))
        
        return classes
    
    def _extract_class_methods(self, class_content: str, class_line: int) -> List[Dict[str, Any]]:
        """Extract methods from class content"""
        methods = []
        
        # Enhanced method pattern
        method_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:native\s+)?(?:abstract\s+)?(?:\w+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w\s,]+)?\s*(?:{|;)'
        
        for match in re.finditer(method_pattern, class_content):
            method_name = match.group(1)
            
            # Skip constructors and common non-method patterns
            if method_name in ['class', 'interface', 'enum', 'if', 'for', 'while', 'switch', 'try', 'catch']:
                continue
            
            # Get line number relative to class
            line_offset = class_content[:match.start()].count('\n')
            line_num = class_line + line_offset
            
            # Extract parameters
            params_str = match.group(2).strip()
            parameters = []
            if params_str:
                for param in params_str.split(','):
                    param = param.strip()
                    if param:
                        # Parse parameter type and name
                        param_parts = param.split()
                        if len(param_parts) >= 2:
                            param_type = ' '.join(param_parts[:-1])
                            param_name = param_parts[-1]
                        else:
                            param_type = param
                            param_name = param
                        
                        parameters.append({
                            "name": param_name,
                            "type": param_type
                        })
            
            # Extract return type (simplified)
            full_match = match.group(0)
            return_type = "void"
            if not full_match.strip().endswith(';'):  # Not an abstract method without body
                # Look for return type before method name
                type_match = re.search(r'(\w+(?:<[^>]+>)?(?:\[\])*)\s+' + re.escape(method_name) + r'\s*\(', full_match)
                if type_match:
                    return_type = type_match.group(1)
            
            # Determine modifiers
            is_static = 'static' in full_match
            is_public = 'public' in full_match
            is_private = 'private' in full_match
            is_protected = 'protected' in full_match
            is_final = 'final' in full_match
            is_abstract = 'abstract' in full_match
            
            # Calculate complexity (simplified)
            complexity = 1
            method_body_start = class_content.find('{', match.end())
            if method_body_start != -1:
                # Find matching closing brace
                brace_count = 1
                method_body_end = method_body_start + 1
                for i, char in enumerate(class_content[method_body_start:], method_body_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            method_body_end = i + 1
                            break
                
                method_body = class_content[method_body_start:method_body_end]
                # Count control structures
                complexity += method_body.count('if')
                complexity += method_body.count('for')
                complexity += method_body.count('while')
                complexity += method_body.count('switch')
                complexity += method_body.count('try')
                complexity += method_body.count('catch')
            
            methods.append({
                "name": method_name,
                "line": line_num,
                "parameters": parameters,
                "return_type": return_type,
                "is_static": is_static,
                "is_public": is_public,
                "is_private": is_private,
                "is_protected": is_protected,
                "is_final": is_final,
                "is_abstract": is_abstract,
                "complexity": complexity
            })
        
        return methods
    
    def _extract_class_fields(self, class_content: str, class_line: int) -> List[Dict[str, Any]]:
        """Extract field declarations from class content"""
        fields = []
        
        # Field pattern (excluding methods)
        field_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:\w+(?:<[^>]+>)?(?:\[\])*)\s+(\w+(?:\s*,\s*\w+)*)\s*(?:=|;)'
        
        for match in re.finditer(field_pattern, class_content):
            # Skip if this looks like a method declaration
            if '(' in match.group(0)[:match.group(0).find(match.group(1))]:
                continue
            
            field_names = match.group(1).split(',')
            field_type = match.group(0).split(match.group(1))[0].strip()
            
            # Get line number
            line_offset = class_content[:match.start()].count('\n')
            line_num = class_line + line_offset
            
            for field_name in field_names:
                field_name = field_name.strip()
                if field_name:
                    # Determine modifiers
                    full_match = match.group(0)
                    is_static = 'static' in full_match
                    is_public = 'public' in full_match
                    is_private = 'private' in full_match
                    is_protected = 'protected' in full_match
                    is_final = 'final' in full_match
                    
                    # Determine access level
                    access_level = "package-private"
                    if is_public:
                        access_level = "public"
                    elif is_private:
                        access_level = "private"
                    elif is_protected:
                        access_level = "protected"
                    
                    fields.append({
                        "name": field_name,
                        "line": line_num,
                        "type": field_type,
                        "is_static": is_static,
                        "is_public": is_public,
                        "is_private": is_private,
                        "is_protected": is_protected,
                        "is_final": is_final,
                        "access_level": access_level
                    })
        
        return fields
    
    def _extract_functions(self, content: str) -> List[Function]:
        """Extract standalone functions (methods outside classes)"""
        functions = []
        
        # Look for methods outside classes
        # First, find all class blocks to exclude them
        class_blocks = []
        class_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+\w+[^{]*\{'
        
        for match in re.finditer(class_pattern, content):
            class_start = match.start()
            brace_count = 0
            class_end = class_start
            
            for i, char in enumerate(content[class_start:], class_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i + 1
                        break
            
            class_blocks.append((class_start, class_end))
        
        # Function pattern for methods outside classes
        function_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:synchronized\s+)?(?:native\s+)?(?:abstract\s+)?(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[\w\s,]+)?\s*(?:{|;)'
        
        for match in re.finditer(function_pattern, content):
            func_name = match.group(1)
            
            # Skip if inside a class
            inside_class = False
            for class_start, class_end in class_blocks:
                if class_start <= match.start() < class_end:
                    inside_class = True
                    break
            
            if inside_class:
                continue
            
            # Skip common non-function patterns
            if func_name in ['class', 'interface', 'enum', 'if', 'for', 'while', 'switch', 'try', 'catch']:
                continue
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            # Extract parameters
            params_str = re.search(r'\(([^)]*)\)', match.group(0))
            parameters = []
            if params_str:
                param_str = params_str.group(1).strip()
                if param_str:
                    for param in param_str.split(','):
                        param = param.strip()
                        if param:
                            param_parts = param.split()
                            if len(param_parts) >= 2:
                                param_type = ' '.join(param_parts[:-1])
                                param_name = param_parts[-1]
                            else:
                                param_type = param
                                param_name = param
                            
                            parameters.append(Parameter(
                                name=param_name,
                                type_hint=param_type
                            ))
            
            # Extract return type
            full_match = match.group(0)
            return_type = "void"
            type_match = re.search(r'(\w+(?:<[^>]+>)?(?:\[\])*)\s+' + re.escape(func_name) + r'\s*\(', full_match)
            if type_match:
                return_type = type_match.group(1)
            
            # Determine modifiers
            is_static = 'static' in full_match
            is_async = False  # Java doesn't have async in the same way
            
            # Calculate complexity
            complexity = 1
            if '{' in full_match:
                # Find method body and count control structures
                body_start = content.find('{', match.end())
                if body_start != -1:
                    brace_count = 1
                    body_end = body_start + 1
                    for i, char in enumerate(content[body_start:], body_start):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                body_end = i + 1
                                break
                    
                    method_body = content[body_start:body_end]
                    complexity += method_body.count('if')
                    complexity += method_body.count('for')
                    complexity += method_body.count('while')
                    complexity += method_body.count('switch')
                    complexity += method_body.count('try')
                    complexity += method_body.count('catch')
            
            functions.append(Function(
                name=func_name,
                line_number=line_num,
                parameters=parameters,
                return_type=return_type,
                decorators=[],
                docstring="",
                complexity_score=complexity,
                is_async=is_async,
                is_method=False
            ))
        
        return functions
    
    def _extract_imports(self, content: str) -> List[Import]:
        """Extract import statements"""
        imports = []
        
        # Import pattern
        import_pattern = r'import\s+(?:static\s+)?([\w.*]+)(?:\.\*)?;'
        
        for match in re.finditer(import_pattern, content):
            import_name = match.group(1).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            # Determine if it's a static import
            is_static = 'static' in match.group(0)
            
            # Extract module and name
            if '.' in import_name:
                parts = import_name.split('.')
                module = '.'.join(parts[:-1])
                name = parts[-1]
            else:
                module = import_name
                name = import_name
            
            imports.append(Import(
                module=module,
                name=name,
                line_number=line_num,
                import_type="static_import" if is_static else "import"
            ))
        
        return imports
    
    def _extract_variables(self, content: str) -> List[Variable]:
        """Extract variable declarations (fields outside classes)"""
        variables = []
        
        # Find class blocks to exclude them
        class_blocks = []
        class_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+\w+[^{]*\{'
        
        for match in re.finditer(class_pattern, content):
            class_start = match.start()
            brace_count = 0
            class_end = class_start
            
            for i, char in enumerate(content[class_start:], class_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        class_end = i + 1
                        break
            
            class_blocks.append((class_start, class_end))
        
        # Variable pattern
        variable_pattern = r'(?:public\s+)?(?:private\s+)?(?:protected\s+)?(?:static\s+)?(?:final\s+)?(?:\w+(?:<[^>]+>)?(?:\[\])*)\s+(\w+(?:\s*,\s*\w+)*)\s*(?:=|;)'
        
        for match in re.finditer(variable_pattern, content):
            # Skip if inside a class
            inside_class = False
            for class_start, class_end in class_blocks:
                if class_start <= match.start() < class_end:
                    inside_class = True
                    break
            
            if inside_class:
                continue
            
            # Skip if this looks like a method declaration
            if '(' in match.group(0)[:match.group(0).find(match.group(1))]:
                continue
            
            var_names = match.group(1).split(',')
            var_type = match.group(0).split(match.group(1))[0].strip()
            
            # Get line number
            line_num = content[:match.start()].count('\n') + 1
            
            for var_name in var_names:
                var_name = var_name.strip()
                if var_name:
                    # Determine modifiers
                    full_match = match.group(0)
                    is_static = 'static' in full_match
                    is_final = 'final' in full_match
                    
                    variables.append(Variable(
                        name=var_name,
                        line_number=line_num,
                        type_hint=var_type,
                        is_global=True,
                        is_constant=is_final
                    ))
        
        return variables
    
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        return ['.java']
    
    def extract_functions(self, ast_root: Any) -> List[Function]:
        """Extract function definitions from AST"""
        # Since we're using regex parsing, ast_root is None
        # This method would need the original content to work
        return []
    
    def extract_classes(self, ast_root: Any) -> List[Class]:
        """Extract class definitions from AST"""
        # Since we're using regex parsing, ast_root is None
        # This method would need the original content to work
        return []
    
    def extract_imports(self, ast_root: Any) -> List[Import]:
        """Extract import statements from AST"""
        # Since we're using regex parsing, ast_root is None
        # This method would need the original content to work
        return []
    
    def extract_variables(self, ast_root: Any) -> List[Variable]:
        """Extract variable definitions from AST"""
        # Since we're using regex parsing, ast_root is None
        # This method would need the original content to work
        return []
    
    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """Parse multiple files in parallel"""
        import asyncio
        tasks = []
        for file_path in file_paths:
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
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
                final_results.append(ASTResult(
                    success=False,
                    language=Language.JAVA,
                    error=f"Failed to parse {file_paths[i]}: {str(result)}",
                    parse_time_ms=0
                ))
            elif hasattr(result, 'success'):
                final_results.append(result)
            else:
                # Dummy task result
                final_results.append(ASTResult(
                    success=False,
                    language=Language.JAVA,
                    error=f"Could not read file: {file_paths[i]}",
                    parse_time_ms=0
                ))
        
        return final_results