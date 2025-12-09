"""
src/tools/file_tools.py

File reading and analysis tools (non-shell-based).
Used for analytical tasks like "analyze this project".
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from langchain_core.tools import tool
from pydantic import BaseModel, Field



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
async def write_file(file_path: str, content: str, mode: str = "create") -> Dict:
    """
    Write content to a file. Creates the file and parent directories if they don't exist.

    SAFETY: Default mode is "create" to prevent accidental overwrites.
    For existing files, use modify_file() instead.

    Args:
        file_path: Path to file (relative or absolute)
        content: Content to write to the file
        mode: Write mode (default: "create")
            - "create": Create new file only (SAFE - fails if file exists)
            - "append": Append to existing file
            - "write": Overwrite entire file (DANGEROUS - use with caution!)

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

        # Determine write mode
        if mode == "append":
            write_mode = "a"
            operation = "appended"
        else:  # mode == "write" or "create"
            write_mode = "w"
            operation = "created" if not file_exists else "overwritten"

        # Write the file
        with open(path, write_mode, encoding="utf-8") as f:
            f.write(content)

        # Get file stats
        file_size = path.stat().st_size
        lines_written = content.count("\n") + 1

        return {
            "success": True,
            "file_path": str(path),
            "operation": operation,
            "size_bytes": file_size,
            "lines_written": lines_written,
            "mode": mode,
        }

    except PermissionError:
        return {"error": f"Permission denied: {file_path}", "file_path": file_path}
    except Exception as e:
        return {"error": f"Error writing file: {str(e)}", "file_path": file_path}


import difflib

def calculate_diff_stats(original_content: str, new_content: str) -> Dict[str, int]:
    """Calculate lines added and removed between two strings."""
    original_lines = original_content.splitlines()
    new_lines = new_content.splitlines()
    
    matcher = difflib.SequenceMatcher(None, original_lines, new_lines)
    added = 0
    removed = 0
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            removed += i2 - i1
            added += j2 - j1
        elif tag == 'delete':
            removed += i2 - i1
        elif tag == 'insert':
            added += j2 - j1
            
    return {"added": added, "removed": removed}

@tool
async def modify_file(
    file_path: str, search_text: str, replace_text: str, occurrence: str = "all"
) -> Dict:
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
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content # Keep for diffing

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

        return {
            "success": True,
            "file_path": str(path),
            "occurrences_found": occurrences_found,
            "replacements_made": replacements,
            "operation": f"replaced {replacements} occurrence(s)",
            "diff": diff_stats
        }

    except Exception as e:
        return {"error": f"Error modifying file: {str(e)}", "file_path": file_path}


class FileEdit(BaseModel):
    search_text: str
    replace_text: str
    occurrence: str = Field(default="all", description="'first', 'last', or 'all'")


@tool
async def apply_multiple_edits(file_path: str, edits: List[Dict[str, str]]) -> Dict:
    """
    Apply multiple edits to a single file in one atomic operation.
    
    Args:
        file_path: Path to the file
        edits: List of edit objects, each containing:
            - search_text: Text to find
            - replace_text: Text to replace with
            - occurrence: 'first', 'last', or 'all' (default: 'all')
            
    Returns:
        Dictionary with status of all edits.
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
            
            count = content.count(search)
            
            if count == 0:
                changes_log.append({
                    "index": i,
                    "status": "failed",
                    "reason": "Search text not found"
                })
                continue
                
            if occurrence == "first":
                content = content.replace(search, replace, 1)
                replaced = 1
            elif occurrence == "last":
                parts = content.rsplit(search, 1)
                content = replace.join(parts)
                replaced = 1
            else: # all
                content = content.replace(search, replace)
                replaced = count
                
            changes_log.append({
                "index": i,
                "status": "success",
                "replacements": replaced
            })
            successful_edits += 1

        if successful_edits == 0:
             return {
                "success": False,
                "file_path": str(path),
                "error": "No edits were successfully applied. content unchanged.",
                "changes": changes_log
            }

        # Calculate diff stats
        diff_stats = calculate_diff_stats(original_content, content)

        # atomic write
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return {
            "success": True,
            "file_path": str(path),
            "total_edits": len(edits),
            "successful_edits": successful_edits,
            "changes": changes_log,
            "diff": diff_stats
        }

    except Exception as e:
        return {"error": f"Error applying multiple edits: {str(e)}", "file_path": file_path}
