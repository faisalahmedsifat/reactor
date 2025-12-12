"""
src/reactor/auto_fixes.py

Automatic code fixing and improvement components.
"""

import re
import ast
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from src.ast.core.ast_manager import ASTManager
from src.ast.core.base_parser import Language, Import
from .config import ReactorConfig


class AutoFixResult:
    """Result of auto-fix operation"""
    
    def __init__(self):
        self.success = True
        self.fixes_applied: List[str] = []
        self.fixes_failed: List[str] = []
        self.new_content: Optional[str] = None
        self.details: Dict[str, Any] = {}


class AutoFixer:
    """Applies automatic fixes to code"""
    
    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config
    
    async def apply_auto_fixes(self, file_path: str, content: str, validation_result) -> AutoFixResult:
        """
        Apply applicable automatic fixes to file content
        
        Args:
            file_path: Path to the file
            content: File content to fix
            validation_result: Result from validation step
            
        Returns:
            AutoFixResult with applied fixes
        """
        result = AutoFixResult()
        current_content = content
        
        try:
            # Apply import fixes
            if self.config.should_auto_fix_imports():
                import_fix_result = await self._fix_imports(file_path, current_content)
                if import_fix_result.success:
                    current_content = import_fix_result.new_content or current_content
                    result.fixes_applied.extend(import_fix_result.fixes_applied)
                else:
                    result.fixes_failed.extend(import_fix_result.fixes_failed)
            
            # Apply unused import removal
            if self.config.should_remove_unused_imports():
                unused_fix_result = await self._remove_unused_imports(file_path, current_content)
                if unused_fix_result.success:
                    current_content = unused_fix_result.new_content or current_content
                    result.fixes_applied.extend(unused_fix_result.fixes_applied)
                else:
                    result.fixes_failed.extend(unused_fix_result.fixes_failed)
            
            # Apply formatting fixes (if enabled)
            if self.config.get("auto_fixes.format_code", False):
                format_fix_result = await self._format_code(file_path, current_content)
                if format_fix_result.success:
                    current_content = format_fix_result.new_content or current_content
                    result.fixes_applied.extend(format_fix_result.fixes_applied)
                else:
                    result.fixes_failed.extend(format_fix_result.fixes_failed)
            
            result.new_content = current_content
            result.details.update({
                "original_length": len(content),
                "fixed_length": len(current_content),
                "fixes_count": len(result.fixes_applied)
            })
            
        except Exception as e:
            result.success = False
            result.fixes_failed.append(f"Auto-fix error: {str(e)}")
        
        return result
    
    async def _fix_imports(self, file_path: str, content: str) -> AutoFixResult:
        """Fix import statements"""
        result = AutoFixResult()
        
        try:
            # Parse the file to get imports
            ast_result = await self.ast_manager.parse_file(file_path)
            if not ast_result.success:
                return result
            
            imports = ast_result.imports or []
            fixes_needed = []
            
            # Check for missing imports based on usage
            missing_imports = await self._detect_missing_imports(content, imports)
            if missing_imports:
                fixes_needed.append(f"Add missing imports: {', '.join(missing_imports)}")
            
            # Apply fixes
            new_content = content
            if missing_imports:
                new_content = await self._add_missing_imports(new_content, missing_imports)
                result.fixes_applied.extend([f"Added import: {imp}" for imp in missing_imports])
            
            result.new_content = new_content
            
        except Exception as e:
            result.success = False
            result.fixes_failed.append(f"Import fix error: {str(e)}")
        
        return result
    
    async def _remove_unused_imports(self, file_path: str, content: str) -> AutoFixResult:
        """Remove unused import statements"""
        result = AutoFixResult()
        
        try:
            # Parse the file to get imports
            ast_result = await self.ast_manager.parse_file(file_path)
            if not ast_result.success or not ast_result.imports:
                return result
            
            imports = ast_result.imports
            unused_imports = await self._detect_unused_imports(content, imports)
            
            if not unused_imports:
                return result
            
            # Remove unused imports
            new_content = content
            for unused_import in unused_imports:
                new_content = self._remove_import_line(new_content, unused_import)
                result.fixes_applied.append(f"Removed unused import: {unused_import}")
            
            result.new_content = new_content
            
        except Exception as e:
            result.success = False
            result.fixes_failed.append(f"Unused import removal error: {str(e)}")
        
        return result
    
    async def _format_code(self, file_path: str, content: str) -> AutoFixResult:
        """Apply basic code formatting"""
        result = AutoFixResult()
        
        try:
            new_content = content
            
            # Basic formatting fixes
            new_content = self._fix_trailing_whitespace(new_content)
            new_content = self._fix_line_endings(new_content)
            new_content = self._fix_spacing_around_operators(new_content)
            
            if new_content != content:
                result.fixes_applied.append("Applied basic code formatting")
            
            result.new_content = new_content
            
        except Exception as e:
            result.success = False
            result.fixes_failed.append(f"Code formatting error: {str(e)}")
        
        return result
    
    async def _detect_missing_imports(self, content: str, imports: List[Import]) -> List[str]:
        """Detect missing imports based on code usage"""
        missing_imports = []
        
        try:
            # Common Python modules and their usage patterns
            common_imports = {
                'os': [r'\bos\.'],
                'sys': [r'\bsys\.'],
                'json': [r'\bjson\.'],
                'datetime': [r'\bdatetime\.'],
                'typing': [r'\b(List|Dict|Optional|Union|Tuple|Any)\b'],
                'pathlib': [r'\bPath\b'],
                'asyncio': [r'\basyncio\.'],
                're': [r'\bre\.'],
                'collections': [r'\bcollections\.'],
                'itertools': [r'\bitertools\.'],
                'functools': [r'\bfunctools\.'],
                'dataclasses': [r'\bdataclass\b'],
                'enum': [r'\bEnum\b'],
            }
            
            existing_imports = {imp.module for imp in imports}
            
            for module, patterns in common_imports.items():
                if module in existing_imports:
                    continue
                
                for pattern in patterns:
                    if re.search(pattern, content):
                        missing_imports.append(module)
                        break
            
        except Exception as e:
            print(f"DEBUG: Error in detect_missing_imports: {e}")
            pass
        
        return missing_imports
    
    async def _detect_unused_imports(self, content: str, imports: List[Import]) -> List[str]:
        """Detect unused import statements"""
        unused_imports = []
        
        try:
            for imp in imports:
                import_name = imp.name or imp.module
                
                # Skip relative imports and complex cases
                if imp.is_relative or '.' in import_name:
                    continue
                
                # Check if the import is used in the code
                pattern = rf'\b{re.escape(import_name)}\b'
                if not re.search(pattern, content):
                    unused_imports.append(import_name)
            
        except Exception:
            pass
        
        return unused_imports
    
    async def _add_missing_imports(self, content: str, missing_imports: List[str]) -> str:
        """Add missing imports to the file"""
        lines = content.split('\n')
        
        # Find the best place to add imports (after existing imports or at the top)
        import_lines = []
        other_lines = []
        found_imports = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_lines.append(line)
                found_imports = True
            else:
                other_lines.append(line)
        
        # Add missing imports
        for module in missing_imports:
            import_lines.append(f'import {module}')
        
        # Reconstruct the file
        if found_imports:
            # Insert after existing imports
            result_lines = import_lines + [''] + other_lines
        else:
            # Add at the top
            result_lines = import_lines + [''] + lines
        
        return '\n'.join(result_lines)
    
    def _remove_import_line(self, content: str, import_name: str) -> str:
        """Remove an import line from content"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            # Check if this line contains the import to remove
            if (f'import {import_name}' in stripped or 
                f'from {import_name}' in stripped or
                f' as {import_name}' in stripped):
                continue  # Skip this line
            new_lines.append(line)
        
        return '\n'.join(new_lines)
    
    def _fix_trailing_whitespace(self, content: str) -> str:
        """Remove trailing whitespace"""
        lines = content.split('\n')
        return '\n'.join(line.rstrip() for line in lines)
    
    def _fix_line_endings(self, content: str) -> str:
        """Normalize line endings to \\n"""
        return content.replace('\r\n', '\n').replace('\r', '\n')
    
    def _fix_spacing_around_operators(self, content: str) -> str:
        """Fix spacing around operators"""
        # This is a very basic implementation
        # In a real implementation, this would be more sophisticated
        
        # Fix spacing around assignment operators
        content = re.sub(r'(\w+)=([^\s=])', r'\1 = \2', content)
        content = re.sub(r'(\w+)=\s+', r'\1 = ', content)
        
        # Fix spacing around comparison operators
        content = re.sub(r'(\w+)==([^\s])', r'\1 == \2', content)
        content = re.sub(r'(\w+)!=([^\s])', r'\1 != \2', content)
        content = re.sub(r'(\w+)<=([^\s])', r'\1 <= \2', content)
        content = re.sub(r'(\w+)>=([^\s])', r'\1 >= \2', content)
        content = re.sub(r'(\w+)<([^\s=])', r'\1 < \2', content)
        content = re.sub(r'(\w+)>([^=\s])', r'\1 > \2', content)
        
        return content


class SmartImportFixer:
    """More sophisticated import fixing"""
    
    def __init__(self, ast_manager: ASTManager, config: ReactorConfig):
        self.ast_manager = ast_manager
        self.config = config
    
    async def organize_imports(self, file_path: str, content: str) -> AutoFixResult:
        """Organize imports according to PEP 8 or language conventions"""
        result = AutoFixResult()
        
        try:
            # Parse imports
            ast_result = await self.ast_manager.parse_file(file_path)
            if not ast_result.success or not ast_result.imports:
                return result
            
            imports = ast_result.imports
            
            # Categorize imports
            stdlib_imports = []
            third_party_imports = []
            local_imports = []
            
            for imp in imports:
                if self._is_stdlib_import(imp.module):
                    stdlib_imports.append(imp)
                elif self._is_local_import(imp.module, file_path):
                    local_imports.append(imp)
                else:
                    third_party_imports.append(imp)
            
            # Sort imports within each category
            stdlib_imports.sort(key=lambda x: x.module)
            third_party_imports.sort(key=lambda x: x.module)
            local_imports.sort(key=lambda x: x.module)
            
            # Rebuild import section
            new_imports = []
            if stdlib_imports:
                new_imports.extend(self._format_import_group(stdlib_imports))
            if third_party_imports:
                if new_imports:
                    new_imports.append('')
                new_imports.extend(self._format_import_group(third_party_imports))
            if local_imports:
                if new_imports:
                    new_imports.append('')
                new_imports.extend(self._format_import_group(local_imports))
            
            # Replace import section in content
            new_content = self._replace_import_section(content, new_imports)
            
            if new_content != content:
                result.fixes_applied.append("Organized imports")
                result.new_content = new_content
            
        except Exception as e:
            result.success = False
            result.fixes_failed.append(f"Import organization error: {str(e)}")
        
        return result
    
    def _is_stdlib_import(self, module_name: str) -> bool:
        """Check if import is from Python standard library"""
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 'typing', 'pathlib', 'asyncio',
            're', 'collections', 'itertools', 'functools', 'dataclasses',
            'enum', 'math', 'random', 'string', 'time', 'urllib', 'http',
            'email', 'xml', 'sqlite3', 'csv', 'configparser', 'logging',
            'unittest', 'argparse', 'subprocess', 'threading', 'multiprocessing'
        }
        
        base_module = module_name.split('.')[0]
        return base_module in stdlib_modules
    
    def _is_local_import(self, module_name: str, file_path: str) -> bool:
        """Check if import is from local project"""
        # This is a simplified check
        # In a real implementation, this would check project structure
        return '.' in module_name and not self._is_stdlib_import(module_name)
    
    def _format_import_group(self, imports: List[Import]) -> List[str]:
        """Format a group of imports"""
        formatted = []
        for imp in imports:
            if imp.name:
                if imp.alias:
                    formatted.append(f"from {imp.module} import {imp.name} as {imp.alias}")
                else:
                    formatted.append(f"from {imp.module} import {imp.name}")
            else:
                formatted.append(f"import {imp.module}")
        return formatted
    
    def _replace_import_section(self, content: str, new_imports: List[str]) -> str:
        """Replace the import section in content"""
        lines = content.split('\n')
        
        # Find import section
        import_start = None
        import_end = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith('import ') or stripped.startswith('from ')) and import_start is None:
                import_start = i
            elif import_start is not None and not (stripped.startswith('import ') or stripped.startswith('from ') or stripped == ''):
                import_end = i
                break
        
        if import_start is None:
            # No imports found, add at the top
            return '\n'.join(new_imports + [''] + lines)
        
        if import_end is None:
            import_end = len(lines)
        
        # Replace import section
        new_lines = lines[:import_start] + new_imports + lines[import_end:]
        return '\n'.join(new_lines)