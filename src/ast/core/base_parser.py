"""
src/ast/core/base_parser.py

Abstract base interface for all language parsers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field


class Language(Enum):
    """Supported programming languages"""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"
    DART = "dart"


@dataclass
class ASTResult:
    """Result of AST parsing operation"""

    success: bool
    language: Language
    ast_root: Optional[Any] = None
    error: Optional[str] = None
    functions: Optional[List["Function"]] = None
    classes: Optional[List["Class"]] = None
    imports: Optional[List["Import"]] = None
    variables: Optional[List["Variable"]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    parse_time_ms: int = 0


@dataclass
class Parameter:
    """Function parameter representation"""

    name: str
    type_hint: str = ""
    default_value: Optional[str] = None
    is_optional: bool = False
    docstring: Optional[str] = None


@dataclass
class Function:
    """Function definition representation"""

    name: str
    line_number: int
    parameters: List[Parameter] = field(default_factory=list)
    return_type: str = ""
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    complexity_score: int = 1
    is_async: bool = False
    is_method: bool = False
    class_name: Optional[str] = None


@dataclass
class Property:
    """Class property/attribute representation"""

    name: str
    line_number: int
    type_hint: str = ""
    default_value: Optional[str] = None
    access_level: str = "public"
    docstring: Optional[str] = None
    is_property: bool = True


@dataclass
class Method:
    """Class method representation"""

    name: str
    line_number: int
    parameters: List[Parameter] = field(default_factory=list)
    return_type: str = ""
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    access_level: str = "public"
    is_static: bool = False
    is_async: bool = False
    complexity_score: int = 1


@dataclass
class Class:
    """Class definition representation"""

    name: str
    line_number: int
    base_classes: List[str] = field(default_factory=list)
    methods: List[Method] = field(default_factory=list)
    properties: List[Property] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    is_abstract: bool = False
    access_level: str = "public"


@dataclass
class Import:
    """Import statement representation"""

    module: str
    line_number: int
    name: Optional[str] = None
    alias: Optional[str] = None
    import_type: str = "import"
    is_relative: bool = False
    is_standard_library: bool = False


@dataclass
class Variable:
    """Variable definition representation"""

    name: str
    line_number: int
    type_hint: str = ""
    default_value: Optional[str] = None
    is_global: bool = False
    is_constant: bool = False


class BaseParser(ABC):
    """Abstract base class for all language parsers"""

    def __init__(self):
        self.language = None
        self.parse_count = 0

    @abstractmethod
    async def parse_file(self, file_path: str, content: str) -> ASTResult:
        """
        Parse file content into AST

        Args:
            file_path: Path to file being parsed
            content: File content as string

        Returns:
            ASTResult with parsed structure
        """
        pass

    @abstractmethod
    async def parse_batch(self, file_paths: List[str]) -> List[ASTResult]:
        """
        Parse multiple files in parallel

        Args:
            file_paths: List of file paths to parse

        Returns:
            List of ASTResults
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions"""
        pass

    @abstractmethod
    def extract_functions(self, ast_root: Any) -> List[Function]:
        """Extract function definitions from AST"""
        pass

    @abstractmethod
    def extract_classes(self, ast_root: Any) -> List[Class]:
        """Extract class definitions from AST"""
        pass

    @abstractmethod
    def extract_imports(self, ast_root: Any) -> List[Import]:
        """Extract import statements from AST"""
        pass

    @abstractmethod
    def extract_variables(self, ast_root: Any) -> List[Variable]:
        """Extract variable definitions from AST"""
        pass

    def calculate_complexity(self, node: Any) -> int:
        """
        Calculate complexity score for a node
        Default implementation can be overridden
        """
        return 1

    def get_language(self) -> Optional[Language]:
        """Get the language this parser handles"""
        return self.language
