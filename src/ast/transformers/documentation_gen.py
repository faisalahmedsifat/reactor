"""Documentation generation from AST."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class DocumentationSection:
    """Represents a section of generated documentation."""
    title: str
    content: str
    section_type: str  # overview, api, examples, etc.
    order: int


@dataclass
class GeneratedDocumentation:
    """Complete generated documentation."""
    title: str
    description: str
    sections: List[DocumentationSection]
    format: str  # markdown, html, etc.
    generation_date: datetime
    metadata: Dict[str, Any]


class DocumentationGenerator:
    """Generates documentation from AST analysis."""
    
    def __init__(self):
        self.templates = self._initialize_templates()
    
    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize documentation templates."""
        return {
            "function_doc": """
### {name}

{description}

**Signature:**
```{language}
{signature}
```

**Parameters:**
{parameters}

**Returns:**
- {return_type}

**Example:**
```{language}
{example}
```

{notes}
""",
            "class_doc": """
## {name}

{description}

{base_classes}

**Properties:**
{properties}

**Methods:**
{methods}

{examples}
""",
            "module_doc": """
# {module_name}

{description}

## Overview

{overview}

## Classes

{classes}

## Functions

{functions}

## Constants

{constants}

## Usage Examples

{examples}

---
*Generated on {date}*
"""
        }
    
    def generate_documentation(self, ast_result: ASTResult, file_path: str, content: str, 
                           format_type: str = "markdown") -> GeneratedDocumentation:
        """Generate documentation from AST result."""
        
        # Extract module information
        module_info = self._extract_module_info(ast_result, file_path, content)
        
        # Generate sections
        sections = []
        
        # Overview section
        sections.append(DocumentationSection(
            title="Overview",
            content=self._generate_overview(module_info, ast_result),
            section_type="overview",
            order=1
        ))
        
        # API documentation
        if ast_result.classes:
            sections.append(DocumentationSection(
                title="Classes",
                content=self._generate_classes_documentation(ast_result.classes, format_type),
                section_type="api",
                order=2
            ))
        
        if ast_result.functions:
            sections.append(DocumentationSection(
                title="Functions",
                content=self._generate_functions_documentation(ast_result.functions, format_type),
                section_type="api",
                order=3
            ))
        
        # Examples section
        sections.append(DocumentationSection(
            title="Examples",
            content=self._generate_examples(ast_result, content, format_type),
            section_type="examples",
            order=4
        ))
        
        # Changelog section
        sections.append(DocumentationSection(
            title="API Reference",
            content=self._generate_api_reference(ast_result, format_type),
            section_type="reference",
            order=5
        ))
        
        return GeneratedDocumentation(
            title=module_info["name"],
            description=module_info["description"],
            sections=sections,
            format=format_type,
            generation_date=datetime.now(),
            metadata={
                "file_path": file_path,
                "language": ast_result.language.value if hasattr(ast_result.language, 'value') else str(ast_result.language),
                "total_classes": len(ast_result.classes or []),
                "total_functions": len(ast_result.functions or []),
                "total_imports": len(ast_result.imports or [])
            }
        )
    
    def _extract_module_info(self, ast_result: ASTResult, file_path: str, content: str) -> Dict[str, Any]:
        """Extract module information from AST and content."""
        # Extract module name from file path
        module_name = file_path.split('/')[-1].split('.')[0]
        
        # Look for module description in comments
        description = ""
        lines = content.split('\n')
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            if re.search(r'(module|package|namespace)', line, re.IGNORECASE):
                # Extract description from following comments
                if i + 1 < len(lines):
                    desc_line = lines[i + 1].strip()
                    if desc_line.startswith(('#', '//', '/*', '*')):
                        description = desc_line.lstrip('#/ *').strip()
                        break
        
        return {
            "name": module_name,
            "description": description or f"Documentation for {module_name}",
            "file_path": file_path,
            "language": ast_result.language.value if hasattr(ast_result.language, 'value') else str(ast_result.language)
        }
    
    def _generate_overview(self, module_info: Dict[str, Any], ast_result: ASTResult) -> str:
        """Generate overview section."""
        overview = f"# {module_info['name']}\n\n"
        overview += f"{module_info['description']}\n\n"
        
        # Add statistics
        overview += "## Statistics\n\n"
        overview += f"- **Language:** {module_info['language']}\n"
        overview += f"- **Classes:** {len(ast_result.classes or [])}\n"
        overview += f"- **Functions:** {len(ast_result.functions or [])}\n"
        overview += f"- **Imports:** {len(ast_result.imports or [])}\n\n"
        
        # Add purpose
        overview += "## Purpose\n\n"
        if ast_result.classes:
            overview += f"This module provides {len(ast_result.classes)} classes for "
            if any(cls.name.lower().endswith('service') for cls in ast_result.classes):
                overview += "service-oriented architecture. "
            elif any(cls.name.lower().endswith('controller') for cls in ast_result.classes):
                overview += "web application controllers. "
            elif any(cls.name.lower().endswith('model') for cls in ast_result.classes):
                overview += "data modeling. "
            else:
                overview += "general functionality. "
        
        if ast_result.functions:
            overview += f"It includes {len(ast_result.functions)} utility functions for "
            overview += "common operations and data processing.\n\n"
        
        return overview
    
    def _generate_classes_documentation(self, classes: List[Class], format_type: str) -> str:
        """Generate documentation for classes."""
        if not classes:
            return "No classes found in this module.\n"
        
        doc = "## Classes\n\n"
        
        for cls in classes:
            doc += self._generate_class_doc(cls, format_type)
        
        return doc
    
    def _generate_class_doc(self, cls: Class, format_type: str) -> str:
        """Generate documentation for a single class."""
        doc = f"### {cls.name}\n\n"
        
        if cls.docstring:
            doc += f"{cls.docstring}\n\n"
        
        # Class signature
        doc += "**Class Definition:**\n"
        if format_type == "markdown":
            doc += f"```python\nclass {cls.name}"
            if cls.base_classes:
                doc += f"({', '.join(cls.base_classes)})"
            doc += "\n```\n\n"
        
        # Properties
        if cls.properties:
            doc += "**Properties:**\n"
            for prop in cls.properties:
                doc += f"- `{prop.name}` ({prop.type_hint})"
                if prop.docstring:
                    doc += f": {prop.docstring}"
                doc += "\n"
            doc += "\n"
        
        # Methods
        if cls.methods:
            doc += "**Methods:**\n"
            for method in cls.methods:
                doc += self._generate_function_doc(method, format_type, is_class_method=True)
        
        return doc
    
    def _generate_functions_documentation(self, functions: List[Function], format_type: str) -> str:
        """Generate documentation for functions."""
        if not functions:
            return "No functions found in this module.\n"
        
        doc = "## Functions\n\n"
        
        for func in functions:
            doc += self._generate_function_doc(func, format_type)
        
        return doc
    
    def _generate_function_doc(self, func, format_type: str, is_class_method: bool = False) -> str:
        """Generate documentation for a single function."""
        doc = f"#### {func.name}\n\n"
        
        if func.docstring:
            doc += f"{func.docstring}\n\n"
        
        # Function signature
        doc += "**Signature:**\n"
        if format_type == "markdown":
            params = []
            for param in func.parameters:
                param_str = param.name
                if param.type_hint:
                    param_str += f": {param.type_hint}"
                if param.default_value:
                    param_str += f" = {param.default_value}"
                params.append(param_str)
            
            signature = f"{func.name}({', '.join(params)})"
            if func.return_type and func.return_type != "void":
                signature += f" -> {func.return_type}"
            
            doc += f"```python\n{signature}\n```\n\n"
        
        # Parameters
        if func.parameters:
            doc += "**Parameters:**\n"
            for param in func.parameters:
                doc += f"- `{param.name}`"
                if param.type_hint:
                    doc += f" ({param.type_hint})"
                if param.docstring:
                    doc += f": {param.docstring}"
                doc += "\n"
            doc += "\n"
        
        # Return value
        if func.return_type and func.return_type != "void":
            doc += f"**Returns:** {func.return_type}\n\n"
        
        # Additional info
        if func.is_async:
            doc += "**Note:** This is an async function.\n\n"
        
        if func.decorators:
            doc += f"**Decorators:** {', '.join(func.decorators)}\n\n"
        
        return doc
    
    def _generate_method_doc(self, method, format_type: str, is_class_method: bool = True) -> str:
        """Generate documentation for a method."""
        doc = f"- `{method.name}`"
        
        if method.return_type and method.return_type != "void":
            doc += f" -> {method.return_type}"
        
        doc += "\n"
        
        if method.docstring:
            doc += f"  {method.docstring}\n"
        
        if method.parameters:
            doc += "  **Parameters:** "
            params = []
            for param in method.parameters:
                param_str = param.name
                if param.type_hint:
                    param_str += f": {param.type_hint}"
                params.append(param_str)
            doc += f"{', '.join(params)}\n"
        
        return doc
    
    def _generate_examples(self, ast_result: ASTResult, content: str, format_type: str) -> str:
        """Generate usage examples."""
        examples = "## Usage Examples\n\n"
        
        # Generate examples based on classes and functions
        if ast_result.classes:
            examples += "### Class Usage\n\n"
            for cls in ast_result.classes[:2]:  # Limit to first 2 classes
                examples += f"```python\n# Create instance of {cls.name}\n"
                examples += f"instance = {cls.name}()\n\n"
                
                # Show method usage
                if cls.methods:
                    method = cls.methods[0]
                    examples += f"# Call method: {method.name}\n"
                    if method.parameters:
                        params = ', '.join([f"'{p.name}'" for p in method.parameters[:2]])  # Limit params
                        examples += f"result = instance.{method.name}({params})\n"
                    else:
                        examples += f"result = instance.{method.name}()\n"
                    examples += "```\n\n"
        
        if ast_result.functions:
            examples += "### Function Usage\n\n"
            for func in ast_result.functions[:2]:  # Limit to first 2 functions
                examples += f"```python\n# Call function: {func.name}\n"
                if func.parameters:
                    params = ', '.join([f"'{p.name}'" for p in func.parameters[:2]])  # Limit params
                    examples += f"result = {func.name}({params})\n"
                else:
                    examples += f"result = {func.name}()\n"
                examples += "```\n\n"
        
        return examples
    
    def _generate_api_reference(self, ast_result: ASTResult, format_type: str) -> str:
        """Generate comprehensive API reference."""
        reference = "## API Reference\n\n"
        
        # Imports
        if ast_result.imports:
            reference += "### Imports\n\n"
            for imp in ast_result.imports:
                reference += f"- `{imp.module}`"
                if imp.alias:
                    reference += f" as `{imp.alias}`"
                reference += f" (line {imp.line_number})\n"
            reference += "\n"
        
        # Detailed class reference
        if ast_result.classes:
            reference += "### Detailed Class Reference\n\n"
            for cls in ast_result.classes:
                reference += self._generate_detailed_class_reference(cls, format_type)
        
        # Detailed function reference
        if ast_result.functions:
            reference += "### Detailed Function Reference\n\n"
            for func in ast_result.functions:
                reference += self._generate_detailed_function_reference(func, format_type)
        
        return reference
    
    def _generate_detailed_class_reference(self, cls: Class, format_type: str) -> str:
        """Generate detailed reference for a class."""
        ref = f"#### {cls.name}\n\n"
        
        # Class information
        ref += f"- **Line:** {cls.line_number}\n"
        ref += f"- **Access Level:** {cls.access_level}\n"
        if cls.is_abstract:
            ref += "- **Abstract Class**\n"
        if cls.base_classes:
            ref += f"- **Inherits from:** {', '.join(cls.base_classes)}\n"
        ref += "\n"
        
        # Detailed properties
        if cls.properties:
            ref += "**Properties:**\n"
            for prop in cls.properties:
                ref += f"- `{prop.name}` ({prop.type_hint}) - {prop.access_level} access\n"
                # Static and readonly properties would need additional attributes
            ref += "\n"
        
        # Detailed methods
        if cls.methods:
            ref += "**Methods:**\n"
            for method in cls.methods:
                ref += f"- `{method.name}` ({method.return_type})\n"
                ref += f"  - Line: {method.line_number}\n"
                ref += f"  - Access: {method.access_level}\n"
                if method.is_static:
                    ref += "  - Static method\n"
                if method.is_async:
                    ref += "  - Async method\n"
                if method.parameters:
                    ref += f"  - Parameters: {len(method.parameters)}\n"
                if method.docstring:
                    ref += f"  - {method.docstring}\n"
            ref += "\n"
        
        return ref
    
    def _generate_detailed_function_reference(self, func: Function, format_type: str) -> str:
        """Generate detailed reference for a function."""
        ref = f"#### {func.name}\n\n"
        
        # Function information
        ref += f"- **Line:** {func.line_number}\n"
        ref += f"- **Return Type:** {func.return_type}\n"
        ref += f"- **Complexity Score:** {func.complexity_score}\n"
        if func.is_async:
            ref += "- **Async Function**\n"
        if func.is_method:
            ref += "- **Method**\n"
        ref += "\n"
        
        # Detailed parameters
        if func.parameters:
            ref += "**Parameters:**\n"
            for param in func.parameters:
                ref += f"- `{param.name}` ({param.type_hint})"
                if param.is_optional:
                    ref += " - Optional"
                if param.default_value:
                    ref += f" - Default: {param.default_value}"
                ref += "\n"
            ref += "\n"
        
        # Additional details
        if func.decorators:
            ref += f"**Decorators:** {', '.join(func.decorators)}\n\n"
        
        if func.docstring:
            ref += f"**Documentation:** {func.docstring}\n\n"
        
        return ref
    
    def export_documentation(self, documentation: GeneratedDocumentation, output_path: str) -> bool:
        """Export documentation to file."""
        try:
            # Combine all sections
            content = f"# {documentation.title}\n\n"
            content += f"{documentation.description}\n\n"
            
            # Sort sections by order
            sorted_sections = sorted(documentation.sections, key=lambda x: x.order)
            for section in sorted_sections:
                content += f"{section.content}\n\n"
            
            # Add metadata
            content += "---\n"
            content += f"*Generated on {documentation.generation_date.strftime('%Y-%m-%d %H:%M:%S')}*\n"
            content += f"*Language: {documentation.metadata.get('language', 'Unknown')}*\n"
            content += f"*Total Classes: {documentation.metadata.get('total_classes', 0)}*\n"
            content += f"*Total Functions: {documentation.metadata.get('total_functions', 0)}*\n"
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error exporting documentation: {e}")
            return False
    
    def generate_changelog(self, ast_result: ASTResult, previous_version: Optional[str] = None) -> str:
        """Generate changelog based on AST changes."""
        changelog = "# Changelog\n\n"
        
        if previous_version:
            changelog += f"## Changes since {previous_version}\n\n"
        else:
            changelog += "## Initial Release\n\n"
        
        # Categorize changes
        if ast_result.classes:
            changelog += "### Added Classes\n\n"
            for cls in ast_result.classes:
                changelog += f"- Added `{cls.name}` class"
                if cls.base_classes:
                    changelog += f" inheriting from {', '.join(cls.base_classes)}"
                changelog += "\n"
            changelog += "\n"
        
        if ast_result.functions:
            changelog += "### Added Functions\n\n"
            for func in ast_result.functions:
                changelog += f"- Added `{func.name}` function"
                if func.return_type and func.return_type != "void":
                    changelog += f" returning {func.return_type}"
                changelog += "\n"
            changelog += "\n"
        
        # Breaking changes (simplified)
        breaking_changes = []
        if ast_result.classes:
            for cls in ast_result.classes:
                if cls.is_abstract:
                    breaking_changes.append(f"Abstract class `{cls.name}` requires implementation")
        
        if breaking_changes:
            changelog += "### Breaking Changes\n\n"
            for change in breaking_changes:
                changelog += f"- {change}\n"
            changelog += "\n"
        
        return changelog