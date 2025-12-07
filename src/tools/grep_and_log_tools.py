"""
src/tools/grep_and_log_tools.py

Advanced grep and log analysis tools.
Provides powerful text search, log parsing, and data extraction capabilities.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter
from langchain_core.tools import tool


@tool
async def grep_advanced(
    pattern: str,
    file_path: str,
    use_regex: bool = False,
    case_sensitive: bool = False,
    context_lines: int = 0,
    invert_match: bool = False,
    count_only: bool = False,
    max_matches: int = 100,
) -> Dict:
    """
    Advanced grep with regex support, context lines, and filtering options.
    More powerful than search_in_files for complex pattern matching.

    Args:
        pattern: Search pattern (plain text or regex)
        file_path: Path to file to search in
        use_regex: If True, treat pattern as regex (default: False)
        case_sensitive: If True, match case-sensitively (default: False)
        context_lines: Number of lines to show before/after match (default: 0)
        invert_match: If True, return non-matching lines (like grep -v)
        count_only: If True, only return count of matches
        max_matches: Maximum matches to return (default: 100)

    Returns:
        Dictionary with matches, line numbers, and context
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}

        # Compile regex pattern if needed
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {"error": f"Invalid regex pattern: {str(e)}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        matches = []
        matching_line_numbers = []

        # Search for pattern
        for line_num, line in enumerate(lines, 1):
            line_content = line.rstrip("\n")

            # Check if line matches
            if use_regex:
                is_match = bool(regex.search(line_content))
            else:
                search_pattern = pattern if case_sensitive else pattern.lower()
                search_line = line_content if case_sensitive else line_content.lower()
                is_match = search_pattern in search_line

            # Apply invert match
            if invert_match:
                is_match = not is_match

            if is_match:
                matching_line_numbers.append(line_num)

                if not count_only and len(matches) < max_matches:
                    match_data = {"line_number": line_num, "line_content": line_content}

                    # Add context lines if requested
                    if context_lines > 0:
                        before_start = max(0, line_num - context_lines - 1)
                        after_end = min(len(lines), line_num + context_lines)

                        match_data["context_before"] = [
                            lines[i].rstrip("\n")
                            for i in range(before_start, line_num - 1)
                        ]
                        match_data["context_after"] = [
                            lines[i].rstrip("\n") for i in range(line_num, after_end)
                        ]

                    matches.append(match_data)

        result = {
            "file_path": str(path),
            "pattern": pattern,
            "total_matches": len(matching_line_numbers),
            "total_lines": len(lines),
        }

        if count_only:
            result["count"] = len(matching_line_numbers)
        else:
            result["matches"] = matches
            result["truncated"] = len(matching_line_numbers) > max_matches

        return result

    except UnicodeDecodeError:
        return {"error": "File is not a text file (binary content)"}
    except Exception as e:
        return {"error": f"Error searching file: {str(e)}"}


@tool
async def parse_log_file(
    file_path: str,
    log_level: Optional[str] = None,
    include_stack_traces: bool = True,
    max_entries: int = 100,
    time_format: Optional[str] = None,
) -> Dict:
    """
    Parse and analyze log files to extract errors, warnings, and stack traces.
    Supports common log formats (plain text, Python logs, JSON logs).

    Args:
        file_path: Path to log file
        log_level: Filter by level (ERROR, WARNING, INFO, DEBUG). None = all levels
        include_stack_traces: If True, capture multi-line stack traces
        max_entries: Maximum log entries to return (default: 100)
        time_format: Expected timestamp format (auto-detected if None)

    Returns:
        Dictionary with parsed log entries categorized by level
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to detect log format
        lines = content.split("\n")

        # Patterns for common log formats
        patterns = {
            "python": r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]?\d*).*?(ERROR|WARNING|INFO|DEBUG)\s*[-:]\s*(.*)",
            "standard": r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[?(ERROR|WARNING|INFO|DEBUG)\]?\s*:?\s*(.*)",
            "syslog": r"(\w+\s+\d+\s+\d{2}:\d{2}:\d{2}).*?(error|warning|info|debug)\s*:?\s*(.*)",
        }

        entries_by_level = {
            "ERROR": [],
            "WARNING": [],
            "INFO": [],
            "DEBUG": [],
            "UNKNOWN": [],
        }

        total_entries = 0
        current_entry = None
        stack_trace_lines = []

        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()

            if not line:
                continue

            # Try JSON format first
            try:
                log_entry = json.loads(line)
                if isinstance(log_entry, dict) and any(
                    k in log_entry for k in ["level", "severity", "message", "msg"]
                ):
                    level = str(
                        log_entry.get("level") or log_entry.get("severity", "UNKNOWN")
                    ).upper()
                    message = log_entry.get("message") or log_entry.get("msg", "")
                    timestamp = log_entry.get("timestamp") or log_entry.get("time", "")

                    if log_level is None or level == log_level.upper():
                        entries_by_level.get(level, entries_by_level["UNKNOWN"]).append(
                            {
                                "line_number": line_num,
                                "timestamp": timestamp,
                                "level": level,
                                "message": message,
                                "raw": line,
                            }
                        )
                        total_entries += 1
                    continue
            except (json.JSONDecodeError, ValueError):
                pass

            # Try text log formats
            matched = False
            for format_name, pattern in patterns.items():
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    # Save previous entry with stack trace
                    if current_entry and stack_trace_lines:
                        current_entry["stack_trace"] = "\n".join(stack_trace_lines)
                        stack_trace_lines = []

                    timestamp, level, message = match.groups()
                    level = level.upper()

                    current_entry = {
                        "line_number": line_num,
                        "timestamp": timestamp,
                        "level": level,
                        "message": message.strip(),
                        "format": format_name,
                    }

                    if log_level is None or level == log_level.upper():
                        entries_by_level[level].append(current_entry)
                        total_entries += 1

                    matched = True
                    break

            # If not a new log entry, might be a stack trace continuation
            if not matched and current_entry and include_stack_traces:
                # Check if line looks like a stack trace
                if any(
                    indicator in line
                    for indicator in [
                        '  File "',
                        "Traceback",
                        "at ",
                        "Exception",
                        "Error:",
                    ]
                ):
                    stack_trace_lines.append(line)

        # Add final stack trace if exists
        if current_entry and stack_trace_lines:
            current_entry["stack_trace"] = "\n".join(stack_trace_lines)

        # Limit entries
        for level in entries_by_level:
            entries_by_level[level] = entries_by_level[level][:max_entries]

        # Calculate statistics
        stats = {
            level: len(entries)
            for level, entries in entries_by_level.items()
            if entries
        }

        return {
            "file_path": str(path),
            "total_entries": total_entries,
            "statistics": stats,
            "entries_by_level": {k: v for k, v in entries_by_level.items() if v},
            "filter_applied": log_level,
        }

    except Exception as e:
        return {"error": f"Error parsing log file: {str(e)}"}


@tool
async def tail_file(file_path: str, num_lines: int = 10, follow: bool = False) -> Dict:
    """
    Read the last N lines of a file (like tail -n).
    Useful for checking recent log entries or command output.

    Args:
        file_path: Path to file
        num_lines: Number of lines from end to read (default: 10)
        follow: If True, would monitor file for changes (not implemented in async context)

    Returns:
        Dictionary with the last N lines
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        if not path.is_file():
            return {"error": f"Not a file: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Get last N lines
        tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines

        return {
            "file_path": str(path),
            "total_lines": len(lines),
            "lines_returned": len(tail_lines),
            "requested_lines": num_lines,
            "lines": [line.rstrip("\n") for line in tail_lines],
            "line_numbers": list(
                range(len(lines) - len(tail_lines) + 1, len(lines) + 1)
            ),
        }

    except UnicodeDecodeError:
        return {"error": "File is not a text file (binary content)"}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}


@tool
async def extract_json_fields(
    source: str,
    fields: List[str],
    is_file: bool = True,
    json_path: Optional[str] = None,
) -> Dict:
    """
    Parse JSON from file or string and extract specific fields.
    Useful for parsing command output or config files.

    Args:
        source: File path or JSON string
        fields: List of field names to extract (supports nested with dot notation, e.g., 'user.name')
        is_file: If True, source is a file path. If False, source is JSON string
        json_path: Optional JSONPath expression for complex queries

    Returns:
        Dictionary with extracted field values
    """
    try:
        # Get JSON content
        if is_file:
            path = Path(source).resolve()
            if not path.exists():
                return {"error": f"File not found: {source}"}

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            source_type = "file"
            source_location = str(path)
        else:
            content = source
            source_type = "string"
            source_location = "inline"

        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {str(e)}"}

        # Extract fields
        extracted = {}

        def get_nested_field(obj, field_path):
            """Extract nested field using dot notation"""
            parts = field_path.split(".")
            current = obj

            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                else:
                    return None

                if current is None:
                    return None

            return current

        for field in fields:
            value = get_nested_field(data, field)
            extracted[field] = value

        return {
            "source": source_location,
            "source_type": source_type,
            "extracted_fields": extracted,
            "fields_requested": fields,
            "success": True,
        }

    except Exception as e:
        return {"error": f"Error extracting JSON fields: {str(e)}"}


@tool
async def filter_command_output(
    output: str,
    filter_type: str = "errors",
    pattern: Optional[str] = None,
    column: Optional[int] = None,
) -> Dict:
    """
    Filter and parse shell command output.
    Useful for extracting relevant info from verbose command results.

    Args:
        output: Command output string (usually from execute_shell_command stdout/stderr)
        filter_type: Type of filtering:
            - "errors": Extract error messages
            - "warnings": Extract warnings
            - "numbers": Extract numeric values
            - "json": Try to parse as JSON
            - "pattern": Use custom pattern
            - "column": Extract specific column (whitespace-separated)
        pattern: Custom regex pattern (used with filter_type="pattern")
        column: Column number to extract (1-indexed, used with filter_type="column")

    Returns:
        Dictionary with filtered output
    """
    try:
        lines = output.split("\n")
        filtered_lines = []
        extracted_values = []

        if filter_type == "errors":
            # Extract lines with error indicators
            error_patterns = [
                r"error[:|\s]",
                r"fail(ed|ure)",
                r"exception",
                r"fatal",
                r"critical",
            ]
            for line in lines:
                if any(re.search(p, line, re.IGNORECASE) for p in error_patterns):
                    filtered_lines.append(line.strip())

        elif filter_type == "warnings":
            # Extract lines with warning indicators
            warning_patterns = [r"warn(ing)?[:|\s]", r"caution", r"deprecated"]
            for line in lines:
                if any(re.search(p, line, re.IGNORECASE) for p in warning_patterns):
                    filtered_lines.append(line.strip())

        elif filter_type == "numbers":
            # Extract all numeric values
            for line in lines:
                numbers = re.findall(r"-?\d+\.?\d*", line)
                if numbers:
                    extracted_values.extend(numbers)
                    filtered_lines.append(line.strip())

        elif filter_type == "json":
            # Try to parse as JSON
            try:
                parsed = json.loads(output)
                return {"filter_type": "json", "parsed_json": parsed, "success": True}
            except json.JSONDecodeError as e:
                return {"error": f"Output is not valid JSON: {str(e)}"}

        elif filter_type == "pattern" and pattern:
            # Use custom pattern
            try:
                regex = re.compile(pattern, re.IGNORECASE)
                for line in lines:
                    matches = regex.findall(line)
                    if matches:
                        filtered_lines.append(line.strip())
                        extracted_values.extend(matches)
            except re.error as e:
                return {"error": f"Invalid regex pattern: {str(e)}"}

        elif filter_type == "column" and column:
            # Extract specific column
            for line in lines:
                parts = line.split()
                if len(parts) >= column:
                    extracted_values.append(parts[column - 1])
                    filtered_lines.append(line.strip())

        else:
            return {"error": f"Invalid filter_type or missing required parameters"}

        return {
            "filter_type": filter_type,
            "total_input_lines": len(lines),
            "filtered_lines": filtered_lines,
            "extracted_values": extracted_values if extracted_values else None,
            "match_count": len(filtered_lines),
        }

    except Exception as e:
        return {"error": f"Error filtering output: {str(e)}"}


@tool
async def analyze_error_logs(
    file_path: str,
    categorize: bool = True,
    extract_stack_traces: bool = True,
    group_similar: bool = True,
) -> Dict:
    """
    Comprehensive error log analyzer.
    Finds, categorizes, and groups errors from log files.

    Args:
        file_path: Path to log file
        categorize: Categorize errors by type (default: True)
        extract_stack_traces: Extract full stack traces (default: True)
        group_similar: Group similar errors together (default: True)

    Returns:
        Dictionary with categorized errors, stack traces, and statistics
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return {"error": f"File not found: {file_path}"}

        # Read file
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        errors = []
        current_error = None
        stack_trace_lines = []

        # Error patterns
        error_indicators = [
            r"ERROR",
            r"Exception",
            r"Traceback",
            r"FATAL",
            r"CRITICAL",
            r"Caused by:",
            r"\w+Error:",
            r"\w+Exception:",
        ]

        error_pattern = "|".join(error_indicators)

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Check if this is an error line
            if re.search(error_pattern, line, re.IGNORECASE):
                # Save previous error if exists
                if current_error:
                    if stack_trace_lines and extract_stack_traces:
                        current_error["stack_trace"] = "\n".join(stack_trace_lines)
                    errors.append(current_error)
                    stack_trace_lines = []

                # Start new error
                current_error = {
                    "line_number": line_num,
                    "error_line": line_stripped,
                    "context_before": [
                        l.strip() for l in lines[max(0, line_num - 3) : line_num - 1]
                    ],
                }

                # Try to extract error type
                error_type_match = re.search(r"(\w+(?:Error|Exception))", line)
                if error_type_match:
                    current_error["error_type"] = error_type_match.group(1)
                else:
                    current_error["error_type"] = "Unknown"

            # Collect stack trace lines
            elif current_error and extract_stack_traces:
                if any(
                    indicator in line
                    for indicator in ['  File "', "    at ", "^", "line "]
                ):
                    stack_trace_lines.append(line_stripped)

        # Add last error
        if current_error:
            if stack_trace_lines and extract_stack_traces:
                current_error["stack_trace"] = "\n".join(stack_trace_lines)
            errors.append(current_error)

        # Categorize errors
        categories = {}
        error_types = Counter()

        if categorize:
            for error in errors:
                error_type = error.get("error_type", "Unknown")
                error_types[error_type] += 1

                if error_type not in categories:
                    categories[error_type] = []
                categories[error_type].append(error)

        # Group similar errors
        grouped_errors = {}
        if group_similar:
            for error in errors:
                # Create a simplified key for grouping
                error_line = re.sub(r"\d+", "N", error["error_line"])  # Replace numbers
                error_line = re.sub(
                    r"0x[0-9a-fA-F]+", "0xHEX", error_line
                )  # Replace hex

                if error_line not in grouped_errors:
                    grouped_errors[error_line] = {
                        "count": 0,
                        "first_occurrence": error["line_number"],
                        "example": error,
                    }
                grouped_errors[error_line]["count"] += 1

        return {
            "file_path": str(path),
            "total_errors_found": len(errors),
            "error_types": dict(error_types),
            "errors_by_category": categories if categorize else None,
            "grouped_errors": grouped_errors if group_similar else None,
            "all_errors": errors[:50],  # Limit to first 50 for output size
        }

    except UnicodeDecodeError:
        return {"error": "File is not a text file (binary content)"}
    except Exception as e:
        return {"error": f"Error analyzing error logs: {str(e)}"}
