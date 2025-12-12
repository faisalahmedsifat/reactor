"""
src/ast/core/language_detector.py

Automatic language detection from file content and extensions.
"""

import os
from pathlib import Path
from typing import Optional, List
from .base_parser import Language

class LanguageDetector:
    """Detect programming languages from files"""
    
    def __init__(self):
        # Extension to language mapping
        self.extension_map = {
            '.py': Language.PYTHON,
            '.pyx': Language.PYTHON,
            '.pyd': Language.PYTHON,
            '.js': Language.JAVASCRIPT,
            '.jsx': Language.JAVASCRIPT,
            '.mjs': Language.JAVASCRIPT,
            '.ts': Language.TYPESCRIPT,
            '.tsx': Language.TYPESCRIPT,
            '.java': Language.JAVA,
            '.kt': Language.JAVA,  # Kotlin
            '.scala': Language.JAVA,  # Scala
            '.go': Language.GO,
            '.rs': Language.RUST,
            '.cpp': Language.CPP,
            '.cc': Language.CPP,
            '.cxx': Language.CPP,
            '.c': Language.CPP,
            '.h': Language.CPP,
            '.hpp': Language.CPP,
            '.cs': Language.CSHARP,
            '.dart': Language.DART,
            '.swift': Language.CPP,  # Group with C++ for now
            '.rb': Language.PYTHON,  # Ruby - group with Python
            '.php': Language.PYTHON,  # PHP - group with Python
        }
        
        # Content-based detection patterns
        self.content_patterns = {
            Language.PYTHON: [
                'import ', 'from ', 'def ', 'class ', 'if __name__',
                '#!/usr/bin/env python', '#!/usr/bin/env python3'
            ],
            Language.JAVASCRIPT: [
                'function ', 'const ', 'let ', 'var ', '=> ', 'require(',
                'import React', 'import Vue', 'import angular',
                '#!/usr/bin/env node', 'export default'
            ],
            Language.TYPESCRIPT: [
                'interface ', 'type ', 'enum ', 'implements ',
                'import type', 'as string', ': string'
            ],
            Language.JAVA: [
                'public class ', 'import java.', 'package ',
                'System.out.println', 'public static void main',
                '@Override', '@Component'
            ],
            Language.GO: [
                'package main', 'func ', 'var ', 'go run',
                'import (', 'fmt.Println', 'http.HandleFunc'
            ],
            Language.RUST: [
                'fn main()', 'use std::', 'pub fn ',
                'impl ', 'let mut', 'match ', 'Option<',
                'extern crate', 'mod ', 'use crate::'
            ],
            Language.CPP: [
                '#include <', 'using namespace', 'std::',
                'int main(', 'cout <<', 'printf(',
                'class ', 'public:', 'private:', 'protected:'
            ],
            Language.CSHARP: [
                'using System;', 'namespace ', 'class Program',
                'public static void Main(', 'Console.WriteLine',
                'public class ', 'interface ', 'enum '
            ],
            Language.DART: [
                'void main(', 'import \'dart:io\'',
                'class ', 'extends ', 'implements ',
                'print(', 'debugPrint('
            ]
        }
        
        # Shebang patterns
        self.shebang_patterns = {
            Language.PYTHON: ['#!/usr/bin/env python', '#!/usr/bin/env python3'],
            Language.JAVASCRIPT: ['#!/usr/bin/env node'],
            Language.GO: ['#!/usr/bin/env go'],
            Language.RUST: ['#!/usr/bin/env rustc'],
            Language.CSHARP: ['#!/usr/bin/env dotnet'],
        }
    
    def detect_from_extension(self, file_path: str) -> Optional[Language]:
        """Detect language from file extension"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        return self.extension_map.get(ext)
    
    def detect_from_content(self, content: str) -> Optional[Language]:
        """Detect language from file content patterns"""
        content_lower = content.lower()
        
        # Check shebang first
        for line in content_lower.split('\n')[:5]:  # Check first 5 lines
            for language, patterns in self.shebang_patterns.items():
                for pattern in patterns:
                    if pattern in line:
                        return language
        
        # Score each language based on content patterns
        scores = {}
        for language, patterns in self.content_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in content_lower:
                    score += 1
            scores[language] = score
        
# Return language with highest score
        if scores:
            best_language = None
            best_score = 0
            
            for lang, score in scores.items():
                if score > best_score:
                    best_score = score
                    best_language = lang
            
            if best_score > 0 and best_language:
                return best_language
        
        return None
    
    def detect_from_shebang(self, content: str) -> Optional[Language]:
        """Detect language from shebang line"""
        first_line = content.split('\n')[0] if content else ''
        
        for language, patterns in self.shebang_patterns.items():
            for pattern in patterns:
                if pattern in first_line:
                    return language
        
        return None
    
    def detect_from_project_structure(self, directory: str) -> Optional[Language]:
        """Detect primary language from project structure"""
        try:
            path = Path(directory)
            if not path.exists():
                return None
            
            # Count files by extension
            file_counts = {}
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    file_counts[ext] = file_counts.get(ext, 0) + 1
            
            if not file_counts:
                return None
            
            # Find dominant language
            if file_counts:
                dominant_ext = max(file_counts, key=file_counts.get)
                dominant_language = self.extension_map.get(dominant_ext)
            else:
                dominant_language = None
            
            return dominant_language
            
        except Exception:
            return None
    
    def get_confidence_score(self, content: str, language: Language) -> float:
        """Get confidence score for language detection"""
        content_lower = content.lower()
        patterns = self.content_patterns.get(language, [])
        
        if not patterns:
            return 0.0
        
        matches = sum(1 for pattern in patterns if pattern in content_lower)
        return min(matches / len(patterns), 1.0)