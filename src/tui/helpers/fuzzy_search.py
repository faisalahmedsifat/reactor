"""
Fuzzy search helpers for autocomplete
"""

from pathlib import Path
import os
from typing import List


def fuzzy_match(query: str, text: str) -> bool:
    """Simple fuzzy matching - all query chars must appear in order in text"""
    query = query.lower()
    text = text.lower()

    query_idx = 0
    for char in text:
        if query_idx < len(query) and char == query[query_idx]:
            query_idx += 1

    return query_idx == len(query)


def get_command_suggestions(query: str) -> List[str]:
    """Get command suggestions based on query"""
    commands = [
        "/help",
        "/clear",
        "/compact",
        "/agents",
        "/agent",
        "/skills",
        "/skill",
        "/running",
        "/result",
        "/new-agent",
        "/edit-agent",
        "/view-agent",
        "/delete-agent",
    ]

    if not query:
        return commands

    # Fuzzy match
    return [cmd for cmd in commands if fuzzy_match(query, cmd[1:])]


def get_file_suggestions(query: str) -> List[str]:
    """Get file suggestions based on query with fuzzy search"""
    files = []

    try:
        # Get all files from current directory recursively (but limit depth)
        for root, dirs, filenames in os.walk(".", topdown=True):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            # Limit depth to 3 levels
            depth = root.count(os.sep)
            if depth > 3:
                dirs[:] = []
                continue

            for filename in filenames:
                if filename.startswith("."):
                    continue

                filepath = os.path.join(root, filename)
                # Make relative path
                rel_path = os.path.relpath(filepath, ".")
                files.append(rel_path)

        # If query is empty, just return all files (sorted, limited)
        if not query:
            return sorted(files)[:50]

        # Fuzzy match against query
        matches = [f for f in files if fuzzy_match(query, f)]
        return sorted(matches)[:50]

    except Exception:
        return []
