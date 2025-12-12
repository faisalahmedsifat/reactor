"""
src/ast/core/ast_manager.py

Central orchestration for multi-language AST parsing and caching.
"""

import asyncio
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
import time

from .base_parser import BaseParser, ASTResult, Language
from .language_detector import LanguageDetector

class ASTManager:
    """Central manager for AST operations across multiple languages"""
    
    def __init__(self):
        self.parsers: Dict[Language, BaseParser] = {}
        self.detector = LanguageDetector()
        self.cache: Dict[str, tuple[ASTResult, float]] = {}
        self.max_cache_size = 1000
        self.cache_ttl = 3600  # 1 hour in seconds
        
    def register_parser(self, language: Language, parser: BaseParser):
        """Register a parser for a specific language"""
        self.parsers[language] = parser
        
    async def parse_file(self, file_path: str, use_cache: bool = True) -> ASTResult:
        """
        Parse a single file with caching support
        
        Args:
            file_path: Path to file to parse
            use_cache: Whether to use cached result
            
        Returns:
            ASTResult with parsed structure
        """
        # Check cache first
        if use_cache:
            cached_result = self._get_cached_result(file_path)
            if cached_result:
                return cached_result
        
        # Detect language and parse
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return ASTResult(
                    success=False,
                    language=Language.PYTHON,  # Default
                    error=f"File not found: {file_path}",
                    parse_time_ms=0
                )
            
            # Read file content
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Detect language
            language = self.detector.detect_from_content(content)
            if not language:
                language = self.detector.detect_from_extension(file_path)
            
            # Default to Python if language detection fails
            if not language:
                language = Language.PYTHON
            
            # Get parser
            parser = self.parsers.get(language)
            if not parser:
                return ASTResult(
                    success=False,
                    language=language,
                    error=f"No parser available for language: {language}",
                    parse_time_ms=0
                )
            
            # Parse the file
            start_time = time.time()
            result = await parser.parse_file(file_path, content)
            parse_time_ms = int((time.time() - start_time) * 1000)
            
            # Update result with timing
            result.parse_time_ms = parse_time_ms
            
            # Cache successful results
            if use_cache and result.success:
                self._cache_result(file_path, result)
            
            return result
            
        except Exception as e:
            return ASTResult(
                success=False,
                language=Language.PYTHON,
                error=f"Parse error: {str(e)}",
                parse_time_ms=0
            )
    
    async def parse_batch(self, file_paths: List[str], use_cache: bool = True) -> List[ASTResult]:
        """
        Parse multiple files in parallel
        
        Args:
            file_paths: List of file paths to parse
            use_cache: Whether to use cached results
            
        Returns:
            List of ASTResults
        """
        tasks = []
        for file_path in file_paths:
            task = self.parse_file(file_path, use_cache)
            tasks.append(task)
        
        return await asyncio.gather(*tasks)
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash for cache key"""
        try:
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                stat = file_path_obj.stat()
                # Use file path, size, and modification time for hash
                hash_input = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
                return hashlib.md5(hash_input.encode()).hexdigest()
            else:
                return hashlib.md5(file_path.encode()).hexdigest()
        except:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    def _get_cached_result(self, file_path: str) -> Optional[ASTResult]:
        """Get cached AST result if valid"""
        cache_key = self._get_file_hash(file_path)
        
        if cache_key in self.cache:
            cached_entry = self.cache[cache_key]
            if isinstance(cached_entry, tuple) and len(cached_entry) == 2:
                cached_result, timestamp = cached_entry
                
                # Check TTL (time-to-live)
                current_time = time.time()
                if current_time - timestamp < self.cache_ttl:
                    return cached_result
                else:
                    # Expired, remove from cache
                    del self.cache[cache_key]
        
        return None
    
    def _cache_result(self, file_path: str, result: ASTResult):
        """Cache AST result with TTL"""
        cache_key = self._get_file_hash(file_path)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1] if isinstance(self.cache[k], tuple) else 0)
            del self.cache[oldest_key]
        
        # Add new entry
        self.cache[cache_key] = (result, time.time())
    
    def clear_cache(self):
        """Clear all cached AST results"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "cache_ttl_seconds": self.cache_ttl,
            "registered_languages": list(self.parsers.keys()),
            "cache_hit_ratio": "N/A"  # Would need tracking
        }
    
    async def extract_functions_from_file(self, file_path: str) -> List[str]:
        """Extract function names from a file"""
        result = await self.parse_file(file_path)
        if not result.success or not result.ast_root:
            return []
        
        parser = self.parsers.get(result.language)
        if not parser:
            return []
        
        functions = parser.extract_functions(result.ast_root)
        return [func.name for func in functions]
    
    async def extract_classes_from_file(self, file_path: str) -> List[str]:
        """Extract class names from a file"""
        result = await self.parse_file(file_path)
        if not result.success or not result.ast_root:
            return []
        
        parser = self.parsers.get(result.language)
        if not parser:
            return []
        
        classes = parser.extract_classes(result.ast_root)
        return [cls.name for cls in classes]
    
    async def extract_imports_from_file(self, file_path: str) -> List[str]:
        """Extract import statements from a file"""
        result = await self.parse_file(file_path)
        if not result.success or not result.ast_root:
            return []
        
        parser = self.parsers.get(result.language)
        if not parser:
            return []
        
        imports = parser.extract_imports(result.ast_root)
        return [f"{imp.module}.{imp.name}" if imp.name else imp.module for imp in imports]
    
    async def get_dependencies_for_file(self, file_path: str) -> Dict[str, List[str]]:
        """Get dependency mapping for a file"""
        result = await self.parse_file(file_path)
        if not result.success or not result.ast_root:
            return {}
        
        parser = self.parsers.get(result.language)
        if not parser:
            return {}
        
        imports = parser.extract_imports(result.ast_root)
        dependencies = {}
        
        for imp in imports:
            module = imp.module
            if module not in dependencies:
                dependencies[module] = []
            dependencies[module].append(file_path)
        
        return dependencies