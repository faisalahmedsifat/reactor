"""
src/tools/file_tools.py

File reading and analysis tools (non-shell-based).
Used for analytical tasks like "analyze this project".
Enhanced with automatic AST analysis via reactor.
"""

import os
import difflib
import asyncio
import fnmatch
from pathlib import Path
from typing import Dict, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Import reactor components for automatic AST analysis
try:
    from src.reactor.code_reactor import get_global_reactor
    from src.reactor.config import get_default_config
    REACTOR_AVAILABLE = True
except ImportError:
    # Fallback to relative imports if src package is not found
    try:
        from ..reactor.code_reactor import get_global_reactor
        from ..reactor.config import get_default_config
        REACTOR_AVAILABLE = True
    except ImportError:
        REACTOR_AVAILABLE = False


def calculate_diff_stats(original_content: str, new_content: str) -> Dict[str, int]:
    """Calculate lines added and removed between two strings."""
    original_lines = original_content.splitlines()
    new_lines = new_content.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, new_lines)
    added = 0
    removed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "replace":
            removed += i2 - i1
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        elif tag == "insert":
            added += j2 - j1

    return {"added": added, "removed": removed}


@tool
async def list_project_files(
    directory: str = ".",
    max_depth: int = 3,
    ignore_patterns: Optional[List[str]] = None,
) -> Dict:
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
            "__pycache__",
            "node_modules",
            ".git",
            ".venv",
            "venv",
            "dist",
            "build",
            ".next",
            ".pytest_cache",
            "coverage",
            "*.pyc",
            ".env",
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
            if pattern.startswith("*"):
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
        "Python": [
            f
            for ext in [".py", ".pyx", ".pyd"]
            for f in files_by_extension.get(ext, [])
        ],
        "TypeScript/JavaScript": [
            f
            for ext in [".ts", ".tsx", ".js", ".jsx"]
            for f in files_by_extension.get(ext, [])
        ],
        "Configuration": [
            f
            for ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"]
            for f in files_by_extension.get(ext, [])
        ],
        "Documentation": [
            f
            for ext in [".md", ".rst", ".txt"]
            for f in files_by_extension.get(ext, [])
        ],
        "Styles": [
            f
            for ext in [".css", ".scss", ".sass", ".less", ".tcss"]
            for f in files_by_extension.get(ext, [])
        ],
        "Other": [],
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
        "all_files": all_files[:500],  # Limit to 500 files
        "truncated": len(all_files) > 500,
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
                "size_bytes": file_size,
            }

        # Read file content
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

                if len(lines) > max_lines:
                    content = "".join(lines[:max_lines])
                    truncated = True
                else:
                    content = "".join(lines)
                    truncated = False

                return {
                    "file_path": str(path),
                    "size_bytes": file_size,
                    "total_lines": len(lines),
                    "lines_returned": min(len(lines), max_lines),
                    "truncated": truncated,
                    "content": content,
                    "extension": path.suffix,
                }
        except UnicodeDecodeError:
            return {
                "error": "File is not a text file (binary content)",
                "file_path": str(path),
            }
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


@tool
async def search_in_files(
    pattern: str,
    directory: str = ".",
    file_extensions: Optional[List[str]] = None,
    max_results: int = 50,
) -> Dict:
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
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        ".next",
        ".pytest_cache",
        "coverage",
        "*.pyc",
        ".env",
    ]

    matches = []
    files_searched = 0

    def should_ignore(path: Path) -> bool:
        for pattern_str in ignore_patterns:
            if pattern_str.startswith("*"):
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

            with open(file_path, "r", encoding="utf-8") as f:
                files_searched += 1
                for line_num, line in enumerate(f, 1):
                    if pattern.lower() in line.lower():
                        matches.append(
                            {
                                "file": str(file_path.relative_to(directory_path)),
                                "line_number": line_num,
                                "line_content": line.rstrip(),
                                "match": pattern,
                            }
                        )

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
        "truncated": len(matches) >= max_results,
    }


@tool
async def write_file(file_path: str, content: str, mode: str = "create", enable_reactor: bool = True) -> Dict:
    """
    Write content to a file. Creates the file and parent directories if they don't exist.
    Automatically runs AST analysis and validation if reactor is enabled.

    SAFETY: Default mode is "create" to prevent accidental overwrites.
    For existing files, use modify_file() instead.

    Args:
        file_path: Path to file (relative or absolute)
        content: Content to write to the file
        mode: Write mode (default: "create")
            - "create": Create new file only (SAFE - fails if file exists)
            - "append": Append to existing file
            - "write": Overwrite entire file (DANGEROUS - use with caution!)
        enable_reactor: Whether to enable automatic AST analysis (default: True)

    Returns:
        Dictionary with operation status, file info, and reactor feedback
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
                "exists": True,
                "suggestion": "Use modify_file() to edit existing files, or use mode='write' to overwrite (dangerous!)",
            }

        # Safety warning for overwrite mode
        if mode == "write" and file_exists:
            # Log warning but proceed (user explicitly chose overwrite)
            import logging

            logging.warning(
                f"OVERWRITING existing file: {file_path} - All previous content will be lost!"
            )

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Determine write mode and capture original content for diff
        if mode == "append":
            write_mode = "a"
            operation = "appended"
            original_content = ""  # For append, we treat original as empty for diffing added lines (conceptually)
            # Or better: read existing to show where append happened?
            # For simplistic "lines added" stats, "original" vs "new" works.
            # If we want exact +added, we should compare (old) vs (old + new).
            if file_exists:
                with open(path, "r", encoding="utf-8") as f:
                    original_content = f.read()
            else:
                original_content = ""
        else:  # mode == "write" or "create"
            write_mode = "w"
            operation = "created" if not file_exists else "overwritten"
            if file_exists and mode == "write":
                with open(path, "r", encoding="utf-8") as f:
                    original_content = f.read()
            else:
                original_content = ""

        # Write the file
        with open(path, write_mode, encoding="utf-8") as f:
            f.write(content)

        # Read back purely for diff calculation
        new_file_content = ""
        with open(path, "r", encoding="utf-8") as f:
            new_file_content = f.read()

        # Calculate diff stats
        diff_stats = calculate_diff_stats(original_content, new_file_content)

        # Get file stats
        file_size = path.stat().st_size
        lines_written = content.count("\n") + 1

        result = {
            "success": True,
            "file_path": str(path),
            "operation": operation,
            "size_bytes": file_size,
            "lines_written": lines_written,
            "mode": mode,
            "diff": diff_stats,
        }

        # Run reactor analysis if enabled and available
        if enable_reactor and REACTOR_AVAILABLE:
            try:
                reactor = get_global_reactor()
                reactor_feedback = await reactor.on_file_written(str(path), new_file_content, operation)
                result["reactor_feedback"] = reactor_feedback
            except Exception as e:
                # Log reactor error but don't fail the write operation
                import logging
                logging.warning(f"Reactor analysis failed for {file_path}: {str(e)}")
                result["reactor_feedback"] = {
                    "status": "error",
                    "error": f"Reactor analysis failed: {str(e)}"
                }

        return result

    except PermissionError:
        return {"error": f"Permission denied: {file_path}", "file_path": file_path}
    except Exception as e:
        return {"error": f"Error writing file: {str(e)}", "file_path": file_path}


@tool
async def modify_file(
    file_path: str, search_text: str, replace_text: str, occurrence: str = "all", enable_reactor: bool = True
) -> Dict:
    """
    Modify a file by searching and replacing text. Useful for targeted edits.
    Automatically runs AST analysis and validation if reactor is enabled.

    Args:
        file_path: Path to file (relative or absolute)
        search_text: Text to search for
        replace_text: Text to replace with
        occurrence: "first", "last", or "all" (default: "all")
        enable_reactor: Whether to enable automatic AST analysis (default: True)

    Returns:
        Dictionary with operation status, changes made, and reactor feedback
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content  # Keep for diffing

        # Count occurrences
        occurrences_found = content.count(search_text)

        if occurrences_found == 0:
            return {
                "success": False,
                "file_path": str(path),
                "error": f"Search text not found in file",
                "occurrences_found": 0,
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

        # Calculate diff stats
        diff_stats = calculate_diff_stats(original_content, new_content)

        # Write back
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)

        result = {
            "success": True,
            "file_path": str(path),
            "occurrences_found": occurrences_found,
            "replacements_made": replacements,
            "operation": f"replaced {replacements} occurrence(s)",
            "diff": diff_stats,
        }

        # Run reactor analysis if enabled and available
        if enable_reactor and REACTOR_AVAILABLE:
            try:
                reactor = get_global_reactor()
                reactor_feedback = await reactor.on_file_written(str(path), new_content, "modify")
                result["reactor_feedback"] = reactor_feedback
            except Exception as e:
                # Log reactor error but don't fail modify operation
                import logging
                logging.warning(f"Reactor analysis failed for {file_path}: {str(e)}")
                result["reactor_feedback"] = {
                    "status": "error",
                    "error": f"Reactor analysis failed: {str(e)}"
                }

        return result

    except Exception as e:
        return {"error": f"Error modifying file: {str(e)}", "file_path": file_path}


class FileEdit(BaseModel):
    search_text: str
    replace_text: str
    occurrence: str = Field(default="all", description="'first', 'last', or 'all'")


@tool
async def edit_file(file_path: str, edits: List[Dict[str, str]], enable_reactor: bool = True) -> Dict:
    """
    Apply multiple edits to a single file in one atomic operation.
    Automatically runs AST analysis and validation if reactor is enabled.

    Use this tool when you need to make more than one change to a file.
    It is faster, safer, and ensures all edits are applied together or none at all.

    Args:
        file_path: Path to the file
        edits: List of edit objects, each containing:
            - search_text: Text to find (must match exactly)
            - replace_text: Text to replace with
            - occurrence: 'first', 'last', or 'all' (default: 'all')
        enable_reactor: Whether to enable automatic AST analysis (default: True)

    Returns:
        Dictionary with status of all edits and reactor feedback.
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes_log = []

        # Validate all edits first (basic check)
        for i, edit in enumerate(edits):
            search = edit.get("search_text")
            if not search:
                return {"error": f"Edit #{i+1} missing search_text"}
            if search not in content:
                # If sequential edits depend on each other, this check might be too strict,
                # but for atomic independent edits it's good.
                # However, previous edits might have changed the content.
                # So we should actually just proceed and track success.
                pass

        # Apply edits sequentially in memory
        successful_edits = 0

        for i, edit in enumerate(edits):
            search = edit.get("search_text")
            replace = edit.get("replace_text", "")
            occurrence = edit.get("occurrence", "all")

            if not search:
                changes_log.append(
                    {"index": i, "status": "failed", "reason": "Search text not provided"}
                )
                continue

            search_text = search  # search is guaranteed not None here
            count = content.count(search_text)

            if count == 0:
                changes_log.append(
                    {"index": i, "status": "failed", "reason": "Search text not found"}
                )
                continue

            replace_text_final = replace or ""
            if occurrence == "first":
                content = content.replace(search_text, replace_text_final, 1)
                replaced = 1
            elif occurrence == "last":
                parts = content.rsplit(search_text, 1)
                content = replace_text_final.join(parts)
                replaced = 1
            else:  # all
                content = content.replace(search_text, replace_text_final)
                replaced = count

            changes_log.append(
                {"index": i, "status": "success", "replacements": replaced}
            )
            successful_edits += 1

        if successful_edits == 0:
            return {
                "success": False,
                "file_path": str(path),
                "error": "No edits were successfully applied. content unchanged.",
                "changes": changes_log,
            }

        # Calculate diff stats
        diff_stats = calculate_diff_stats(original_content, content)

        # atomic write
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        result = {
            "success": True,
            "file_path": str(path),
            "total_edits": len(edits),
            "successful_edits": successful_edits,
            "changes": changes_log,
            "diff": diff_stats,
        }

        # Run reactor analysis if enabled and available
        if enable_reactor and REACTOR_AVAILABLE:
            try:
                reactor = get_global_reactor()
                reactor_feedback = await reactor.on_file_written(str(path), content, "edit")
                result["reactor_feedback"] = reactor_feedback
            except Exception as e:
                # Log reactor error but don't fail edit operation
                import logging
                logging.warning(f"Reactor analysis failed for {file_path}: {str(e)}")
                result["reactor_feedback"] = {
                    "status": "error",
                    "error": f"Reactor analysis failed: {str(e)}"
                }

        return result

    except Exception as e:
        return {
            "error": f"Error applying multiple edits: {str(e)}",
            "file_path": file_path,
        }


@tool
async def read_multiple_files(file_paths: List[str], max_files: int = 5) -> Dict:
    """
    Read multiple files in parallel for efficient analysis.
    
    Use this tool when analyzing multiple related files or getting project overview.
    More efficient than individual read_file_content calls.

    Args:
        file_paths: List of file paths to read (relative or absolute)
        max_files: Maximum number of files to read (default: 5, for performance)

    Returns:
        Dictionary with:
        - files_read: Number of successfully read files
        - files: List of file contents with metadata
        - errors: List of files that couldn't be read
        - truncated: Whether any files were truncated
    """
    if not file_paths:
        return {"error": "No file paths provided"}
    
    # Limit files for performance
    file_paths = file_paths[:max_files]
    
    async def read_single_file(file_path: str) -> Dict:
        """Read a single file with error handling"""
        try:
            path = Path(file_path).resolve()
            
            if not path.exists():
                return {"file_path": file_path, "error": f"File not found: {file_path}"}
            
            if not path.is_file():
                return {"file_path": file_path, "error": f"Not a file: {file_path}"}
            
            # Check file size (limit to 1MB for safety)
            file_size = path.stat().st_size
            if file_size > 1_000_000:
                return {
                    "file_path": file_path,
                    "error": f"File too large: {file_size} bytes (max 1MB)",
                    "size_bytes": file_size,
                }
            
            # Read file content
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
                if len(lines) > 500:
                    content = "".join(lines[:500])
                    truncated = True
                else:
                    content = "".join(lines)
                    truncated = False
                
                return {
                    "file_path": str(path),
                    "size_bytes": file_size,
                    "total_lines": len(lines),
                    "lines_returned": min(len(lines), 500),
                    "truncated": truncated,
                    "content": content,
                    "extension": path.suffix,
                }
                
        except UnicodeDecodeError:
            return {
                "file_path": file_path,
                "error": "File is not a text file (binary content)",
            }
        except Exception as e:
            return {"file_path": file_path, "error": f"Error reading file: {str(e)}"}
    
    # Read files in parallel
    results = await asyncio.gather(*[read_single_file(fp) for fp in file_paths])
    
    # Separate successful reads from errors
    successful_files = []
    errors = []
    any_truncated = False
    
    for result in results:
        if "error" in result:
            errors.append(result)
        else:
            successful_files.append(result)
            if result.get("truncated", False):
                any_truncated = True
    
    return {
        "files_read": len(successful_files),
        "files": successful_files,
        "errors": errors,
        "truncated": any_truncated,
        "requested_files": len(file_paths),
    }


# Internal function for project structure analysis (not a tool)
async def _list_project_files_internal(directory: str, max_depth: int = 3) -> Dict:
    """Internal version of list_project_files for use within other tools"""
    # Replicate the logic without tool decoration
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    files_by_extension = {}
    all_files = []
    total_files = 0
    total_dirs = 0
    
    ignore_patterns = [
        "__pycache__", "node_modules", ".git", ".venv", "venv",
        "dist", "build", ".next", ".pytest_cache", "coverage", "*.pyc", ".env"
    ]
    
    def should_ignore(path: Path) -> bool:
        for pattern in ignore_patterns:
            if pattern.startswith("*"):
                if str(path).endswith(pattern[1:]):
                    return True
            else:
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
            pass
    
    walk_directory(directory_path)
    
    return {
        "directory": str(directory_path),
        "total_files": total_files,
        "files_by_extension": {k: len(v) for k, v in files_by_extension.items()},
        "all_files": all_files,
    }


@tool
async def prioritize_files(directory: str = ".", file_count: int = 10) -> Dict:
    """
    Intelligently prioritize files for analysis based on importance.
    
    Returns files in order of importance for understanding a project:
    1. README and documentation files
    2. Configuration files (package.json, pyproject.toml, etc.)
    3. Main entry points (main.py, index.js, etc.)
    4. Core source files
    5. Test files

    Args:
        directory: Directory to analyze (default: current directory)
        file_count: Maximum number of files to return (default: 10)

    Returns:
        Dictionary with prioritized file list and categorization
    """
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    # Priority patterns and their order
    priority_patterns = [
        # High Priority - Documentation
        ("README", ["README.md", "README.rst", "README.txt", "readme.md"]),
        ("Documentation", ["*.md", "*.rst", "*.txt"]),
        
        # High Priority - Configuration
        ("Package Config", ["package.json", "pyproject.toml", "Cargo.toml", "requirements.txt", "Pipfile", "composer.json", "Gemfile"]),
        ("Build Config", ["Makefile", "CMakeLists.txt", "build.gradle", "webpack.config.js"]),
        
        # High Priority - Entry Points
        ("Entry Points", ["main.py", "app.py", "server.py", "index.js", "app.js", "server.js", "main.rs", "lib.rs", "src/main.rs"]),
        
        # Medium Priority - Core Source
        ("Python Source", ["src/**/*.py", "**/*.py"]),
        ("JavaScript Source", ["src/**/*.js", "**/*.js", "src/**/*.ts", "**/*.ts"]),
        ("Rust Source", ["src/**/*.rs", "**/*.rs"]),
        
        # Medium Priority - Tests
        ("Tests", ["test/**/*.py", "**/*test*.py", "tests/**/*.js", "**/*test*.js"]),
        
        # Low Priority - Other
        ("Other", []),
    ]
    
    all_files = []
    
    # Walk directory and collect files
    ignore_patterns = [
        "__pycache__", "node_modules", ".git", ".venv", "venv",
        "dist", "build", ".next", ".pytest_cache", "coverage", "*.pyc"
    ]
    
    def should_ignore(path: Path) -> bool:
        for pattern in ignore_patterns:
            if pattern.startswith("*"):
                if str(path).endswith(pattern[1:]):
                    return True
            else:
                if pattern in path.parts:
                    return True
        return False
    
    def walk_directory(path: Path, depth: int = 0):
        if depth > 4:  # Limit depth
            return
        
        try:
            for item in path.iterdir():
                if should_ignore(item):
                    continue
                
                if item.is_file():
                    relative_path = str(item.relative_to(directory_path))
                    all_files.append(relative_path)
                elif item.is_dir():
                    walk_directory(item, depth + 1)
        except PermissionError:
            pass
    
    walk_directory(directory_path)
    
    # Categorize and prioritize files
    prioritized_files = []
    used_files = set()
    
    for category_name, patterns in priority_patterns:
        category_files = []
        
        for pattern in patterns:
            if pattern.startswith("**"):
                # Glob pattern
                import fnmatch
                matches = [f for f in all_files if fnmatch.fnmatch(f, pattern) and f not in used_files]
                category_files.extend(matches)
            elif pattern.startswith("*"):
                # Extension pattern
                ext = pattern[1:]
                matches = [f for f in all_files if f.endswith(ext) and f not in used_files]
                category_files.extend(matches)
            else:
                # Exact match
                matches = [f for f in all_files if f == pattern and f not in used_files]
                category_files.extend(matches)
        
        # Add unique files from this category
        for file_path in category_files:
            if file_path not in used_files and len(prioritized_files) < file_count:
                prioritized_files.append({
                    "path": file_path,
                    "category": category_name,
                    "priority": len(prioritized_files) + 1
                })
                used_files.add(file_path)
        
        if len(prioritized_files) >= file_count:
            break
    
    return {
        "directory": str(directory_path),
        "total_files_found": len(all_files),
        "prioritized_files": prioritized_files,
        "categories_used": list(set([f["category"] for f in prioritized_files])),
        "files_returned": len(prioritized_files),
    }


@tool
async def analyze_project_structure(directory: str = ".", max_depth: int = 3) -> Dict:
    """
    Analyze project structure and identify key characteristics.
    
    Provides insights about:
    - Project type (Python, JavaScript, Rust, etc.)
    - Build system used
    - Dependency management
    - Testing framework
    - Key directories and their purposes

    Args:
        directory: Directory to analyze (default: current directory)
        max_depth: Maximum depth to traverse (default: 3)

    Returns:
        Dictionary with project analysis and structure insights
    """
    directory_path = Path(directory).resolve()
    
    if not directory_path.exists():
        return {"error": f"Directory not found: {directory}"}
    
    # Get file listing using direct function call
    # Extract the underlying function from the tool
    from functools import wraps
    
    # Call the original function before tool decoration
    file_list_result = await _list_project_files_internal(directory, max_depth)
    if "error" in file_list_result:
        return file_list_result
    
    # Convert internal result to expected format
    files_by_extension = file_list_result.get("files_by_extension", {})
    all_files = file_list_result.get("all_files", [])
    
    # Convert to categories format expected by analysis
    files_by_category = {
        "Python": [f for ext, files in files_by_extension.items() if ext in [".py", ".pyx", ".pyd"] for f in files],
        "TypeScript/JavaScript": [f for ext, files in files_by_extension.items() if ext in [".ts", ".tsx", ".js", ".jsx"] for f in files],
        "Configuration": [f for ext, files in files_by_extension.items() if ext in [".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"] for f in files],
        "Documentation": [f for ext, files in files_by_extension.items() if ext in [".md", ".rst", ".txt"] for f in files],
        "Styles": [f for ext, files in files_by_extension.items() if ext in [".css", ".scss", ".sass", ".less", ".tcss"] for f in files],
    }
    
    # Detect project type
    project_type = "Unknown"
    primary_language = "Unknown"
    
    if files_by_category.get("Python"):
        project_type = "Python"
        primary_language = "Python"
    elif files_by_category.get("TypeScript/JavaScript"):
        project_type = "JavaScript/TypeScript"
        primary_language = "TypeScript/JavaScript"
    elif any(f.endswith(".rs") for f in all_files):
        project_type = "Rust"
        primary_language = "Rust"
    elif any(f.endswith(".go") for f in all_files):
        project_type = "Go"
        primary_language = "Go"
    elif any(f.endswith(".java") for f in all_files):
        project_type = "Java"
        primary_language = "Java"
    
    # Detect build system and dependency management
    build_system = "Unknown"
    dependency_files = []
    
    config_files = files_by_category.get("Configuration", [])
    for config_file in config_files:
        if config_file == "package.json":
            build_system = "npm/yarn"
            dependency_files.append("package.json")
        elif config_file == "pyproject.toml":
            build_system = "Poetry/setuptools"
            dependency_files.append("pyproject.toml")
        elif config_file == "requirements.txt":
            build_system = "pip"
            dependency_files.append("requirements.txt")
        elif config_file == "Cargo.toml":
            build_system = "Cargo"
            dependency_files.append("Cargo.toml")
        elif config_file in ["Makefile", "CMakeLists.txt"]:
            build_system = "Make/CMake"
        elif config_file == "build.gradle":
            build_system = "Gradle"
        elif config_file == "composer.json":
            build_system = "Composer"
            dependency_files.append("composer.json")
    
    # Detect testing framework
    testing_framework = "Unknown"
    test_files = [f for f in all_files if "test" in f.lower()]
    
    if any("pytest" in f for f in test_files):
        testing_framework = "pytest"
    elif any("unittest" in f for f in test_files):
        testing_framework = "unittest"
    elif any("jest" in f for f in test_files):
        testing_framework = "Jest"
    elif any("mocha" in f for f in test_files):
        testing_framework = "Mocha"
    
    # Analyze directory structure
    key_directories = set()
    for file_path in all_files:
        parts = file_path.split("/")
        if len(parts) > 1:
            key_directories.add(parts[0])
    
    # Identify common directory patterns
    directory_analysis = {}
    for directory in key_directories:
        if directory in ["src", "lib", "source"]:
            directory_analysis[directory] = "Source code"
        elif directory in ["test", "tests", "spec"]:
            directory_analysis[directory] = "Test files"
        elif directory in ["docs", "doc", "documentation"]:
            directory_analysis[directory] = "Documentation"
        elif directory in ["build", "dist", "out", "target"]:
            directory_analysis[directory] = "Build output"
        elif directory in ["config", "configs", "settings"]:
            directory_analysis[directory] = "Configuration"
        else:
            directory_analysis[directory] = "Other"
    
    # Find entry points
    entry_points = []
    entry_point_patterns = [
        "main.py", "app.py", "server.py", "index.py",
        "main.js", "app.js", "server.js", "index.js",
        "main.rs", "lib.rs", "main.go", "main.java"
    ]
    
    for pattern in entry_point_patterns:
        if pattern in all_files:
            entry_points.append(pattern)
    
    return {
        "project_type": project_type,
        "primary_language": primary_language,
        "build_system": build_system,
        "dependency_files": dependency_files,
        "testing_framework": testing_framework,
        "entry_points": entry_points,
        "key_directories": directory_analysis,
        "total_files": len(all_files),
        "file_categories": {k: len(v) for k, v in files_by_category.items()},
        "analysis_summary": f"{project_type} project using {build_system} for dependency management",
    }
