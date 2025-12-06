"""
src/tools/file_tools.py

File reading and analysis tools (non-shell-based).
Used for analytical tasks like "analyze this project".
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from langchain_core.tools import tool


@tool
async def list_project_files(directory: str = ".", max_depth: int = 3, ignore_patterns: Optional[List[str]] = None) -> Dict:
    """
    Recursively list all files in a directory.
    Returns structured file tree with categorization by extension.
    
    Args:
        directory: Directory to analyze (default: current directory)
        max_depth: Maximum depth to traverse (default: 3)
        ignore_patterns: Patterns to ignore (default: common ignore patterns)
    
    Returns:
        Dictionary with file counts, categories, and paths
    """
    if ignore_patterns is None:
        ignore_patterns = [
            '__pycache__', 'node_modules', '.git', '.venv', 'venv',
            'dist', 'build', '.next', '.pytest_cache', 'coverage',
            '*.pyc', '.env'
        ]
    
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    files_by_extension = {}
    all_files = []
    total_files = 0
    total_dirs = 0
    
    def should_ignore(path: Path) -> bool:
        """Check if path should be ignored"""
        for pattern in ignore_patterns:
            if pattern.startswith('*'):
                # Extension pattern
                if str(path).endswith(pattern[1:]):
                    return True
            else:
                # Directory/file name pattern
                if pattern in path.parts:
                    return True
        return False
    
    def walk_directory(path: Path, current_depth: int = 0):
        nonlocal total_files, total_dirs
        
        if current_depth > max_depth:
            return
        
        try:
            for item in path.iterdir():
                if should_ignore(item):
                    continue
                
                if item.is_file():
                    total_files += 1
                    ext = item.suffix or "(no extension)"
                    relative_path = str(item.relative_to(directory_path))
                    
                    if ext not in files_by_extension:
                        files_by_extension[ext] = []
                    files_by_extension[ext].append(relative_path)
                    all_files.append(relative_path)
                    
                elif item.is_dir():
                    total_dirs += 1
                    walk_directory(item, current_depth + 1)
        except PermissionError:
            pass  # Skip directories we can't access
    
    walk_directory(directory_path)
    
    # Categorize extensions
    categories = {
        "Python": [f for ext in ['.py', '.pyx', '.pyd'] for f in files_by_extension.get(ext, [])],
        "TypeScript/JavaScript": [f for ext in ['.ts', '.tsx', '.js', '.jsx'] for f in files_by_extension.get(ext, [])],
        "Configuration": [f for ext in ['.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'] for f in files_by_extension.get(ext, [])],
        "Documentation": [f for ext in ['.md', '.rst', '.txt'] for f in files_by_extension.get(ext, [])],
        "Styles": [f for ext in ['.css', '.scss', '.sass', '.less', '.tcss'] for f in files_by_extension.get(ext, [])],
        "Other": []
    }
    
    # Add files that don't fit categories to "Other"
    categorized_files = set()
    for files in categories.values():
        categorized_files.update(files)
    
    categories["Other"] = [f for f in all_files if f not in categorized_files]
    
    return {
        "directory": str(directory_path),
        "total_files": total_files,
        "total_directories": total_dirs,
        "files_by_extension": {k: len(v) for k, v in files_by_extension.items()},
        "files_by_category": {k: v for k, v in categories.items() if v},
        "all_files": all_files[:100]  # Limit to first 100 for output size
    }


@tool
async def read_file_content(file_path: str, max_lines: int = 500) -> Dict:
    """
    Read content of a text file.
    
    Args:
        file_path: Path to file (relative or absolute)
        max_lines: Maximum lines to read (default: 500)
    
    Returns:
        Dictionary with file content and metadata
    """
    try:
        path = Path(file_path).resolve()
        
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}
        
        # Check file size (limit to 1MB for safety)
        file_size = path.stat().st_size
        if file_size > 1_000_000:
            return {
                "error": f"File too large: {file_size} bytes (max 1MB)",
                "file_path": str(path),
                "size_bytes": file_size
            }
        
        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                if len(lines) > max_lines:
                    content = ''.join(lines[:max_lines])
                    truncated = True
                else:
                    content = ''.join(lines)
                    truncated = False
                
                return {
                    "file_path": str(path),
                    "size_bytes": file_size,
                    "total_lines": len(lines),
                    "lines_returned": min(len(lines), max_lines),
                    "truncated": truncated,
                    "content": content,
                    "extension": path.suffix
                }
        except UnicodeDecodeError:
            return {
                "error": "File is not a text file (binary content)",
                "file_path": str(path)
            }
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


@tool
async def analyze_project_structure(directory: str = ".") -> Dict:
    """
    Analyze project structure to infer project type and key files.
    Performs a depth-limited scan to find configuration and entry points.
    
    Args:
        directory: Directory to analyze (default: current directory)
    
    Returns:
        Dictionary with project type, entry points, and key configuration files
    """
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    # Configuration
    MAX_DEPTH = 3
    IGNORE_DIRS = {
        'node_modules', '.git', '.venv', 'venv', '__pycache__', 
        'dist', 'build', '.next', '.idea', '.vscode'
    }
    
    # Results containers
    project_indicators = []
    config_files = {}
    entry_points = []
    documentation = []
    source_structure = {}  # Summary of source folders
    
    # Known patterns
    TYPE_INDICATORS = {
        'pyproject.toml': 'Python (Poetry)',
        'requirements.txt': 'Python (pip)',
        'setup.py': 'Python (setuptools)',
        'Pipfile': 'Python (Pipenv)',
        'package.json': 'Node.js/JS',
        'tsconfig.json': 'TypeScript',
        'go.mod': 'Go',
        'Cargo.toml': 'Rust',
        'Gemfile': 'Ruby',
        'composer.json': 'PHP',
        'pom.xml': 'Java (Maven)',
        'build.gradle': 'Java/Kotlin (Gradle)',
        'Dockerfile': 'Docker',
        'docker-compose.yml': 'Docker Compose'
    }
    
    ENTRY_PATTERNS = {
        'main.py', 'app.py', 'wsgi.py', 'asgi.py', 'manage.py',
        'index.js', 'server.js', 'app.js',
        'index.ts', 'server.ts', 'main.go', 'main.rs'
    }

    # Walk directory
    try:
        base_depth = len(directory_path.parts)
        
        for root, dirs, files in os.walk(directory_path):
            root_path = Path(root)
            current_depth = len(root_path.parts) - base_depth
            
            # Modify dirs in-place to prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            if current_depth > MAX_DEPTH:
                # Clear dirs to stop recursion but process files in current dir (if strict depth needed we'd skip)
                # Actually os.walk continues, so we manually skip deep levels
                del dirs[:]
                continue
                
            rel_path = root_path.relative_to(directory_path)
            
            # Record structure for top 2 levels
            if current_depth <= 2 and current_depth > 0:
                parent = str(rel_path.parent) if current_depth > 1 else "."
                if parent not in source_structure:
                    source_structure[parent] = []
                source_structure[parent].append(rel_path.name + "/")

            for file in files:
                file_path = root_path / file
                rel_file_path = str(file_path.relative_to(directory_path))
                
                # Check for Indicators
                if file in TYPE_INDICATORS:
                    project_indicators.append(TYPE_INDICATORS[file])
                    config_files[file] = rel_file_path
                
                # Check for Entry Points
                if file in ENTRY_PATTERNS:
                    entry_points.append(rel_file_path)
                
                # Check for Documentation
                if file.lower().startswith('readme'):
                    documentation.append(rel_file_path)
                    
    except Exception as e:
        return {"error": f"Error scanning directory: {str(e)}"}
    
    # Deduplicate project types
    project_types = list(set(project_indicators))
    if not project_types:
        project_types = ["Unknown / Generic"]
        
    return {
        "directory": str(directory_path),
        "project_types": project_types,
        "key_config_files": config_files,
        "entry_points": entry_points,
        "documentation": documentation,
        "structure_summary": source_structure,
        "scan_depth": MAX_DEPTH
    }


@tool
async def search_in_files(pattern: str, directory: str = ".", file_extensions: Optional[List[str]] = None, max_results: int = 50) -> Dict:
    """
    Search for a text pattern in files (like grep). Use this to find where something is defined or used.
    
    Args:
        pattern: Text pattern to search for (case-insensitive substring match)
        directory: Directory to search in (default: current directory)
        file_extensions: List of file extensions to search (e.g., ['.py', '.js']). If None, searches all text files.
        max_results: Maximum number of matches to return (default: 50)
    
    Returns:
        Dictionary with matching files, lines, and line numbers
    """
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    ignore_patterns = [
        '__pycache__', 'node_modules', '.git', '.venv', 'venv',
        'dist', 'build', '.next', '.pytest_cache', 'coverage',
        '*.pyc', '.env'
    ]
    
    matches = []
    files_searched = 0
    
    def should_ignore(path: Path) -> bool:
        for pattern_str in ignore_patterns:
            if pattern_str.startswith('*'):
                if str(path).endswith(pattern_str[1:]):
                    return True
            else:
                if pattern_str in path.parts:
                    return True
        return False
    
    def search_file(file_path: Path):
        nonlocal files_searched
        
        # Check extension filter
        if file_extensions and file_path.suffix not in file_extensions:
            return
        
        # Skip binary files and very large files
        try:
            file_size = file_path.stat().st_size
            if file_size > 500_000:  # Skip files > 500KB
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                files_searched += 1
                for line_num, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        matches.append({
                            "file": str(file_path.relative_to(directory_path)),
                            "line_number": line_num,
                            "line_content": line.rstrip(),
                            "match": pattern
                        })
                        
                        if len(matches) >= max_results:
                            return True  # Stop searching
        except (UnicodeDecodeError, PermissionError):
            pass  # Skip binary files or files we can't read
        
        return False
    
    # Walk directory and search files
    def walk_and_search(path: Path, depth: int = 0):
        if depth > 5 or len(matches) >= max_results:  # Max depth 5
            return
        
        try:
            for item in path.iterdir():
                if should_ignore(item):
                    continue
                
                if item.is_file():
                    if search_file(item):
                        return  # Stop if max results reached
                elif item.is_dir():
                    walk_and_search(item, depth + 1)
        except PermissionError:
            pass
    
    walk_and_search(directory_path)
    
    return {
        "pattern": pattern,
        "directory": str(directory_path),
        "files_searched": files_searched,
        "matches_found": len(matches),
        "matches": matches,
        "truncated": len(matches) >= max_results
    }


@tool
async def write_file(file_path: str, content: str, mode: str = "write") -> Dict:
    """
    Write content to a file. Creates the file and parent directories if they don't exist.
    
    Args:
        file_path: Path to file (relative or absolute)
        content: Content to write to the file
        mode: Write mode - "write" (overwrite), "append", or "create" (fail if exists)
    
    Returns:
        Dictionary with operation status and file info
    """
    try:
        path = Path(file_path).resolve()
        
        # Check if file exists
        file_exists = path.exists()
        
        # Handle different modes
        if mode == "create" and file_exists:
            return {
                "error": f"File already exists: {file_path}",
                "file_path": str(path),
                "exists": True
            }
        
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Determine write mode
        if mode == "append":
            write_mode = 'a'
            operation = "appended"
        else:  # mode == "write" or "create"
            write_mode = 'w'
            operation = "created" if not file_exists else "overwritten"
        
        # Write the file
        with open(path, write_mode, encoding='utf-8') as f:
            f.write(content)
        
        # Get file stats
        file_size = path.stat().st_size
        lines_written = content.count('\n') + 1
        
        return {
            "success": True,
            "file_path": str(path),
            "operation": operation,
            "size_bytes": file_size,
            "lines_written": lines_written,
            "mode": mode
        }
        
    except PermissionError:
        return {
            "error": f"Permission denied: {file_path}",
            "file_path": file_path
        }
    except Exception as e:
        return {
            "error": f"Error writing file: {str(e)}",
            "file_path": file_path
        }


@tool
async def modify_file(file_path: str, search_text: str, replace_text: str, occurrence: str = "all") -> Dict:
    """
    Modify a file by searching and replacing text. Useful for targeted edits.
    
    Args:
        file_path: Path to file (relative or absolute)
        search_text: Text to search for
        replace_text: Text to replace with
        occurrence: "first", "last", or "all" (default: "all")
    
    Returns:
        Dictionary with operation status and changes made
    """
    try:
        path = Path(file_path).resolve()
        
        if not path.exists():
            return {"error": f"File not found: {file_path}"}
        
        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}
        
        # Read file
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Count occurrences
        occurrences_found = content.count(search_text)
        
        if occurrences_found == 0:
            return {
                "success": False,
                "file_path": str(path),
                "error": f"Search text not found in file",
                "occurrences_found": 0
            }
        
        # Perform replacement
        if occurrence == "first":
            new_content = content.replace(search_text, replace_text, 1)
            replacements = 1
        elif occurrence == "last":
            # Replace last occurrence
            parts = content.rsplit(search_text, 1)
            new_content = replace_text.join(parts)
            replacements = 1
        else:  # "all"
            new_content = content.replace(search_text, replace_text)
            replacements = occurrences_found
        
        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "success": True,
            "file_path": str(path),
            "occurrences_found": occurrences_found,
            "replacements_made": replacements,
            "operation": f"replaced {replacements} occurrence(s)"
        }
        
    except Exception as e:
        return {
            "error": f"Error modifying file: {str(e)}",
            "file_path": file_path
        }

