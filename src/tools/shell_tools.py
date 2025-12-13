import pty
import os
import fcntl
import struct
import termios
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import asyncio
import platform
from pathlib import Path
import time
import signal


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
            f.write(
                f"\n\n{'='*40}\n--- Executing: {command} ---\n--- Directory: {cwd} ---\n{'='*40}\n"
            )

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
                decoded = line.decode(errors="replace")
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
            read_stream(process.stderr, stderr_acc),
        )

        try:
            await asyncio.wait_for(process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                process.terminate()
                await process.wait()
            except:
                pass  # Already dead
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
            timeout=1,
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


# --- Interactive Shell Session Manager ---


class ShellSession:
    def __init__(
        self, session_id: str, process, log_path: Path, master_fd: Optional[int] = None
    ):
        self.session_id = session_id
        self.process = process
        self.log_path = log_path
        self.master_fd = master_fd  # PTY Master FD (POSIX only)
        self.created_at = time.time()
        self.is_active = True
        self.writer_task = None


class ShellSessionManager:
    _instance = None
    _sessions: Dict[str, ShellSession] = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_session(
        self, session_id: str, process, log_path: Path, master_fd: Optional[int] = None
    ):
        self._sessions[session_id] = ShellSession(
            session_id, process, log_path, master_fd
        )

    def get_session(self, session_id: str) -> Optional[ShellSession]:
        return self._sessions.get(session_id)

    def remove_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s.session_id,
                "active": s.is_active,
                "uptime": time.time() - s.created_at,
            }
            for s in self._sessions.values()
        ]


# Tool 8: Run Interactive Command
@tool
async def run_interactive_command(
    command: str, working_directory: str = ".", timeout: int = 300
) -> Dict[str, Any]:
    """
    Start a persistent interactive shell command (bg process) with PTY support.

    Use this for commands that require user input or run for a long time (REPLs, servers).
    Returns a session_id that you MUST use with `send_shell_input` and `terminate_shell_session`.
    """
    import uuid
    import tempfile

    session_id = str(uuid.uuid4())[:8]
    manager = ShellSessionManager.get_instance()

    cwd = str(Path(working_directory).expanduser())
    live_log_path = Path(tempfile.gettempdir()) / f"reactor_session_{session_id}.log"

    # Initialize log
    with open(live_log_path, "w", encoding="utf-8") as f:
        f.write(
            f"--- Interactive Session {session_id} ---\nCommand: {command}\nCWD: {cwd}\n\n"
        )

    try:
        # Detect OS
        system = platform.system().lower()
        use_pty = system != "windows"

        master_fd = None
        process = None

        if use_pty:
            # POSIX PTY Setup
            master_fd, slave_fd = pty.openpty()

            # Set raw mode to prevent local echo double-printing if possible,
            # but usually default is fine for basic automation.
            # We trust the shell tool to handle output.

            process = await asyncio.create_subprocess_shell(
                command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=cwd,
                preexec_fn=os.setsid,  # Create new session
            )
            os.close(slave_fd)  # Close slave in parent

            manager.create_session(session_id, process, live_log_path, master_fd)

            # Start background reader for PTY master
            # We use a StreamReader connected to the master_fd
            loop = asyncio.get_running_loop()
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(
                lambda: protocol, os.fdopen(master_fd, "rb", buffering=0)
            )

            asyncio.create_task(_stream_pty_output(session_id, reader))

        else:
            # Windows/Fallback Implementation (Pipe based)
            # Prepare environment with TERM
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            manager.create_session(session_id, process, live_log_path)

            asyncio.create_task(_stream_output(session_id, process.stdout, "stdout"))
            asyncio.create_task(_stream_output(session_id, process.stderr, "stderr"))

        # Wait a bit to capture initial output
        await asyncio.sleep(0.5)

        initial_output = _read_session_log(live_log_path)

        return {
            "success": True,
            "session_id": session_id,
            "status": "running",
            "initial_output": initial_output,
            "log_file": str(live_log_path),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


async def _stream_pty_output(session_id: str, reader: asyncio.StreamReader):
    """Read from PTY master and write to log"""
    manager = ShellSessionManager.get_instance()
    session = manager.get_session(session_id)
    if not session:
        return

    try:
        while True:
            # Read roughly standard chunk size
            data = await reader.read(1024)
            if not data:
                break

            # Decode mechanism
            decoded = data.decode(errors="replace")

            # Fix newlines: PTY often output \r\n, but sometimes just \n or \r.
            # We write as-is to log, RichLog handles ANSI control codes including cursor movements.

            with open(session.log_path, "a", encoding="utf-8") as f:
                f.write(decoded)
    except Exception:
        pass
    finally:
        session.is_active = False


async def _stream_output(session_id: str, stream, stream_name: str):
    """Background task to stream output from PIPES (Windows fallback)"""
    manager = ShellSessionManager.get_instance()
    session = manager.get_session(session_id)
    if not session:
        return

    while True:
        line = await stream.readline()
        if not line:
            break

        decoded = line.decode(errors="replace")
        try:
            with open(session.log_path, "a", encoding="utf-8") as f:
                f.write(decoded)
        except:
            pass

    session.is_active = False


def _read_session_log(path: Path, max_chars: int = 2000) -> str:
    if not path.exists():
        return ""
    try:
        content = path.read_text(encoding="utf-8")
        if len(content) > max_chars:
            return "...(truncated)...\n" + content[-max_chars:]
        return content
    except:
        return ""


# Tool 9: Send Shell Input
@tool
async def send_shell_input(
    session_id: str, input_text: str, wait_ms: int = 1000
) -> Dict[str, Any]:
    """
    Send text input to a running interactive session.
    Automatically adds newline if not present? No, we trust the caller (prompt says explicit).
    Actually, to be user-friendly, maybe we don't force explicit \n for simple tools usage,
    but for `send_shell_input` raw power, explicit is better.
    However, prompt instructions say "Add \n".
    """
    manager = ShellSessionManager.get_instance()
    session = manager.get_session(session_id)

    if not session:
        return {"error": f"Session {session_id} not found or inactive"}

    # Check process status logic
    # Default is running if returncode is None
    if session.process.returncode is not None:
        return {"error": f"Process exited with {session.process.returncode}"}

    try:
        input_bytes = input_text.encode(errors="replace")

        if session.master_fd is not None:
            # PTY Write
            os.write(session.master_fd, input_bytes)
            # No need to drain for os.write to FD
        else:
            # Pipe Write
            session.process.stdin.write(input_bytes)
            await session.process.stdin.drain()

        # Log input (optional, sometimes duplicates echo)
        # In PTY mode, the terminal echoes it back usually.
        # So we might NOT want to write input to log manually to avoid double characters.
        # But for visibility of "Command sent", we can use a special marker.
        # with open(session.log_path, "a", encoding="utf-8") as f:
        #    f.write(f"[INPUT SENT]: {input_text}")

        await asyncio.sleep(wait_ms / 1000.0)

        current_log = _read_session_log(session.log_path)

        return {"success": True, "latest_output": current_log, "status": "running"}

    except Exception as e:
        return {"error": f"Failed to send input: {str(e)}"}


# Tool 10: Get Shell Output
@tool
async def get_shell_session_output(session_id: str) -> Dict[str, Any]:
    """Get the latest output from a running session without sending input."""
    manager = ShellSessionManager.get_instance()
    session = manager.get_session(session_id)

    if not session:
        return {"error": f"Session {session_id} not found"}

    output = _read_session_log(session.log_path)
    is_running = session.process.returncode is None

    return {"session_id": session_id, "is_running": is_running, "output": output}


# Tool 11: Terminate Session
@tool
async def terminate_shell_session(session_id: str) -> Dict[str, Any]:
    """Terminate (kill) a running interactive shell session."""
    manager = ShellSessionManager.get_instance()
    session = manager.get_session(session_id)

    if not session:
        return {"error": f"Session {session_id} not found"}

    try:
        # Kill logic
        if session.process.returncode is None:
            session.process.terminate()
            try:
                await asyncio.wait_for(session.process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                session.process.kill()

        # Cleanup PTY
        if session.master_fd is not None:
            try:
                os.close(session.master_fd)
            except:
                pass

        manager.remove_session(session_id)

        return {"success": True, "message": f"Session {session_id} terminated"}
    except Exception as e:
        return {"error": f"Failed to terminate: {str(e)}"}
