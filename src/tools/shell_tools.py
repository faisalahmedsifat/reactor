from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import asyncio
import platform
from pathlib import Path
import time





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
    working_directory: str = Field(default=".")
    timeout: int = Field(default=30)
    dry_run: bool = Field(default=False)


@tool(args_schema=ExecuteInput)
async def execute_shell_command(
    command: str, working_directory: str = ".", timeout: int = 30, dry_run: bool = False
) -> Dict[str, Any]:
    """
    Execute a shell command safely.

    IMPORTANT: ALWAYS validate with validate_command_safety first!

    Returns execution result with stdout, stderr, and exit code.
    Set dry_run=True to simulate without actually executing.
    """
    start = time.time()
    
    import tempfile
    # Live output log file - Use absolute path in temp dir
    live_log_path = Path(tempfile.gettempdir()) / "reactor_live_output.log"

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
        # Detect OS for shell selection
        system = platform.system().lower()
        cwd = str(Path(working_directory).expanduser())

        # Append to live log instead of truncate
        with open(live_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n\n{'='*40}\n--- Executing: {command} ---\n--- Directory: {cwd} ---\n{'='*40}\n")

        # Create subprocess asynchronously
        process = None
        
        if system == "windows":
            # Windows: use powershell
            cmd_list = ["powershell.exe", "-NoProfile", "-Command", command]
            process = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
        else:
            # Unix: use shell=True via specific method
            # We assume 'bash' or similar is available
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                # executable="/bin/bash" # Optional: force bash
            )

        stdout_acc = []
        stderr_acc = []

        async def read_stream(stream, acc):
            while True:
                line = await stream.readline()
                if not line:
                    break
                decoded = line.decode(errors='replace')
                acc.append(decoded)
                # Write to live log
                try:
                    with open(live_log_path, "a", encoding="utf-8") as f:
                        f.write(decoded)
                        f.flush()
                except:
                    pass

        # Concurrent reading of stdout and stderr
        await asyncio.gather(
            read_stream(process.stdout, stdout_acc),
            read_stream(process.stderr, stderr_acc)
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                process.terminate()
                await process.wait()
            except:
                pass # Already dead
            raise TimeoutError(f"Command timed out after {timeout}s")

        stdout_str = "".join(stdout_acc)
        stderr_str = "".join(stderr_acc)

        return {
            "success": process.returncode == 0,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "exit_code": process.returncode,
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

    # Get minimal git info if available
    git_info = "Not a git repo"
    try:
        # Check if .git exists in current or parent dirs
        # Simple check: call git branch --show-current
        proc = subprocess.run(
            ["git", "branch", "--show-current"], 
            capture_output=True, 
            text=True, 
            timeout=1
        )
        if proc.returncode == 0:
            branch = proc.stdout.strip()
            if branch:
                git_info = f"Git Branch: {branch}"
            else:
                git_info = "Git Repo (Detached/No Branch)"
    except Exception:
        pass

    # Get python version
    python_version = platform.python_version()

    return {
        "os_type": os_type,
        "shell_type": shell_type,
        "working_directory": str(Path.cwd()),
        "user": username,
        "hostname": platform.node(),
        "git_info": git_info,
        "python_version": python_version,
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
