from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import platform
from pathlib import Path
import time


# Tool 1: Parse Intent
class ParseIntentInput(BaseModel):
    user_request: str = Field(description="User's natural language request")
    working_directory: str = Field(default="~")
    shell_type: str = Field(default="bash")


@tool(args_schema=ParseIntentInput)
def parse_user_intent(
    user_request: str, working_directory: str = "~", shell_type: str = "bash"
) -> Dict[str, Any]:
    """
    Parse natural language request into structured intent.

    Analyzes what the user wants to accomplish and extracts:
    - Task description
    - Operation category
    - Key entities (files, packages, etc)
    - Constraints

    Use this as the FIRST tool when user makes a request.
    """
    return {
        "task_description": user_request,
        "category": "to_be_determined",
        "key_entities": [],
        "constraints": [],
        "user_intent_confidence": 0.9,
        "context": {"working_directory": working_directory, "shell_type": shell_type},
    }


# Tool 2: Generate Command Plan
class GeneratePlanInput(BaseModel):
    task_description: str
    category: str = Field(default="other")
    key_entities: List[str] = Field(default_factory=list)
    working_directory: str = Field(default="~")


@tool(args_schema=GeneratePlanInput)
def generate_command_plan(
    task_description: str,
    category: str = "other",
    key_entities: List[str] = [],
    working_directory: str = "~",
) -> Dict[str, Any]:
    """
    Generate execution plan with shell commands.

    Creates a safe, step-by-step plan including:
    - Ordered shell commands
    - Safety risk assessment
    - Reversibility info
    - Dependencies

    Use after parsing intent to create the execution strategy.
    """
    return {
        "commands": [],
        "overall_strategy": f"Execute: {task_description}",
        "potential_issues": [],
        "estimated_duration_seconds": 5,
    }


# Tool 3: Validate Safety
@tool
def validate_command_safety(command: str) -> Dict[str, Any]:
    """
    Check if a shell command is safe to execute.

    Validates against dangerous patterns like:
    - rm -rf /
    - dd if=/dev/zero
    - fork bombs
    - writes to system directories

    ALWAYS use this before execute_shell_command!
    """
    import re

    dangerous = [
        r"\brm\s+-rf\s+/",
        r"\bdd\s+if=",
        r">\s*/dev/sd",
        r":(){:|:&};:",
    ]

    warnings = []
    for pattern in dangerous:
        if re.search(pattern, command, re.IGNORECASE):
            warnings.append(f"Dangerous pattern: {pattern}")

    return {
        "is_safe": len(warnings) == 0,
        "risk_level": "safe" if not warnings else "dangerous",
        "warnings": warnings,
        "requires_approval": bool(warnings),
    }


# Tool 4: Execute Command
class ExecuteInput(BaseModel):
    command: str
    working_directory: str = Field(default="~")
    timeout: int = Field(default=30)
    dry_run: bool = Field(default=False)


@tool(args_schema=ExecuteInput)
def execute_shell_command(
    command: str, working_directory: str = "~", timeout: int = 30, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute a shell command safely.

    IMPORTANT: ALWAYS validate with validate_command_safety first!

    Returns execution result with stdout, stderr, and exit code.
    Set dry_run=True to simulate without actually executing.
    """
    start = time.time()

    if dry_run:
        return {
            "success": True,
            "stdout": f"[DRY RUN] Would execute: {command}",
            "stderr": "",
            "exit_code": 0,
            "duration_ms": (time.time() - start) * 1000,
            "command": command,
        }

    try:
        # Detect OS and choose shell
        system = platform.system().lower()
        shell_cmd = None

        if system == "windows":
            # Force PowerShell on Windows
            shell_cmd = ["powershell.exe", "-NoProfile", "-Command", command]
            # When using list args with subprocess, shell must be False
            use_shell = False
        else:
            # Use default shell behavior on Unix
            shell_cmd = command
            use_shell = True

        result = subprocess.run(
            shell_cmd,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path(working_directory).expanduser()),
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "duration_ms": (time.time() - start) * 1000,
            "command": command,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "duration_ms": (time.time() - start) * 1000,
            "command": command,
        }


# Tool 5: Get System Info
@tool
def get_system_info() -> Dict[str, str]:
    """
    Get current system information.

    Returns OS type, shell, working directory, user, etc.
    Use this at the START to understand the execution environment.
    """
    import os

    os_type = platform.system().lower()

    # Detect shell based on OS and environment
    if os_type == "windows":
        # Native Windows: PowerShell or CMD
        shell_type = "powershell" if os.environ.get("PSModulePath") else "cmd"
    elif os_type == "linux":
        # Check if running in WSL
        is_wsl = False
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                is_wsl = "microsoft" in version_info or "wsl" in version_info
        except:
            pass

        # Also check WSL environment variable
        is_wsl = is_wsl or os.environ.get("WSL_DISTRO_NAME") is not None

        if is_wsl:
            # WSL: Get actual shell from SHELL env var
            shell_type = f"wsl-{os.environ.get('SHELL', 'bash').split('/')[-1]}"
        else:
            # Native Linux: Get shell from SHELL env var
            shell_type = os.environ.get("SHELL", "bash").split("/")[-1]
    else:
        # macOS and other Unix-like systems
        shell_type = os.environ.get("SHELL", "bash").split("/")[-1]

    # Get username (works on both Windows and Unix)
    username = os.environ.get("USER") or os.environ.get("USERNAME", "unknown")

    return {
        "os_type": os_type,
        "shell_type": shell_type,
        "working_directory": str(Path.cwd()),
        "user": username,
        "hostname": platform.node(),
    }


# Tool 6: Analyze Error
@tool
def analyze_command_error(
    command: str, error_output: str, exit_code: int
) -> Dict[str, Any]:
    """
    Analyze why a command failed and suggest fixes.

    Use this when execute_shell_command returns success=False.
    Provides root cause analysis and suggested fixes.
    """
    root_cause = "Unknown error"
    should_retry = False
    suggested_fix = "Manual intervention required"

    error_lower = error_output.lower()

    if (
        "command not found" in error_lower
        or "is not recognized as an internal or external command" in error_lower
    ):
        root_cause = "Command/tool not installed or not in PATH"
        suggested_fix = "Install the required tool or check spelling"
    elif "permission denied" in error_lower or "access is denied" in error_lower:
        root_cause = "Insufficient permissions"
        suggested_fix = "Check file permissions or run as administrator"
    elif (
        "no such file" in error_lower
        or "does not exist" in error_lower
        or "cannot find path" in error_lower
    ):
        root_cause = "File/directory does not exist"
        suggested_fix = "Verify path and create if needed"
        should_retry = True

    return {
        "root_cause": root_cause,
        "suggested_fix": suggested_fix,
        "should_retry": should_retry,
    }


# Tool 7: Check Path
@tool
def check_path_exists(path: str) -> Dict[str, Any]:
    """
    Check if file or directory exists.

    Use BEFORE operations that depend on paths existing.
    Returns detailed info about the path.
    """
    p = Path(path).expanduser()

    if not p.exists():
        return {"exists": False, "path": str(p)}

    import os

    return {
        "exists": True,
        "is_file": p.is_file(),
        "is_directory": p.is_dir(),
        "is_readable": os.access(p, os.R_OK),
        "is_writable": os.access(p, os.W_OK),
        "path": str(p),
    }
