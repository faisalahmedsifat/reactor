"""
Universal AST node types for cross-language representation.
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    """Universal AST node types"""

    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    EXPORT = "export"
    TYPE = "type"
    PROPERTY = "property"
    PARAMETER = "parameter"
    DECORATOR = "decorator"
    ANNOTATION = "annotation"
    COMMENT = "comment"
    NAMESPACE = "namespace"
    PACKAGE = "package"
    MODULE = "module"


class ASTNode:
    """Base AST node with universal properties"""

    def __init__(self, node_type: str, name: str, line_number: int, column: int = 0):
        self.node_type = node_type
        self.name = name
        self.line_number = line_number
        self.column = column
        self.children = []
        self.metadata = {}

    def add_child(self, child: "ASTNode") -> None:
        """Add a child node"""
        self.children.append(child)

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        self.metadata[key] = value


class Function(ASTNode):
    """Function definition node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.FUNCTION.value, name, line_number, **kwargs)
        self.parameters = []
        self.return_type = ""
        self.decorators = []
        self.docstring = ""
        self.complexity_score = 1
        self.is_async = False
        self.is_method = False
        self.is_exported = False
        self.receiver = ""
        self.class_name = None


class Parameter(ASTNode):
    """Function parameter node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.PARAMETER.value, name, line_number, **kwargs)
        self.param_type = ""
        self.default_value = ""
        self.is_optional = False
        self.is_varargs = False


class Class(ASTNode):
    """Class/interface definition node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.CLASS.value, name, line_number, **kwargs)
        self.methods = []
        self.properties = []
        self.base_classes = []
        self.interfaces = []
        self.decorators = []
        self.docstring = ""
        self.is_abstract = False
        self.is_interface = False
        self.is_exported = False
        self.access_level = "public"


class Property(ASTNode):
    """Class property/attribute node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.PROPERTY.value, name, line_number, **kwargs)
        self.property_type = ""
        self.default_value = ""
        self.access_level = "public"
        self.is_static = False
        self.is_readonly = False


class Import(ASTNode):
    """Import statement node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.IMPORT.value, name, line_number, **kwargs)
        self.module = ""
        self.alias = ""
        self.import_type = "import"
        self.is_used = False
        self.is_standard_library = False
        self.is_relative = False


class Variable(ASTNode):
    """Variable definition node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.VARIABLE.value, name, line_number, **kwargs)
        self.variable_type = ""
        self.default_value = ""
        self.is_global = False
        self.is_constant = False
        self.is_exported = False
        self.mutability = "mutable"


class Type(ASTNode):
    """Type definition node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.TYPE.value, name, line_number, **kwargs)
        self.underlying_type = ""
        self.type_parameters = []
        self.constraints = []
        self.is_generic = False
        self.is_exported = False


class Package(ASTNode):
    """Package/namespace node"""

    def __init__(self, name: str, line_number: int, **kwargs):
        super().__init__(NodeType.PACKAGE.value, name, line_number, **kwargs)
        self.package_path = ""
        self.exports = []
        self.imports = []


class Comment(ASTNode):
    """Comment node"""

    def __init__(self, content: str, line_number: int, **kwargs):
        super().__init__(NodeType.COMMENT.value, content, line_number, **kwargs)
        self.comment_type = "line"
        self.content = content


# Language-specific metadata keys
class MetadataKeys:
    """Common metadata keys for different languages"""

    # Universal
    LANGUAGE = "language"
    EXPORTED = "exported"
    ASYNC = "async"

    # Python
    DECORATORS = "decorators"
    TYPE_HINTS = "type_hints"

    # JavaScript/TypeScript
    EXPORT_TYPE = "export_type"
    JSX = "jsx"

    # Go
    RECEIVER = "receiver"
    GOROUTINE = "goroutine"
    CHANNEL = "channel"

    # Rust
    LIFETIMES = "lifetimes"
    TRAITS = "traits"
    MACROS = "macros"
    UNSAFE = "unsafe"

    # Java
    ANNOTATIONS = "annotations"
    GENERICS = "generics"

    # C++
    TEMPLATES = "templates"
    NAMESPACES = "namespaces"

    # C#
    ATTRIBUTES = "attributes"
    LINQ = "linq"

    # Dart
    MIXINS = "mixins"
    EXTENSIONS = "extensions"
    NULL_SAFETY = "null_safety"


# Utility functions for creating nodes
def create_function(name: str, line: int, **kwargs) -> Function:
    """Create a function node with default values"""
    return Function(name=name, line_number=line, **kwargs)


def create_class(name: str, line: int, **kwargs) -> Class:
    """Create a class node with default values"""
    return Class(name=name, line_number=line, **kwargs)


def create_interface(name: str, line: int, **kwargs) -> Class:
    """Create an interface node with default values"""
    return Class(name=name, line_number=line, is_interface=True, **kwargs)


def create_import(name: str, line: int, **kwargs) -> Import:
    """Create an import node with default values"""
    return Import(name=name, line_number=line, **kwargs)


def create_variable(name: str, line: int, **kwargs) -> Variable:
    """Create a variable node with default values"""
    return Variable(name=name, line_number=line, **kwargs)
