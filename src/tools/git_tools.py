"""
src/tools/git_tools.py

Provides native Git operations for the Agent.
"""

import subprocess
from typing import Optional, List
from langchain_core.tools import tool

def _run_git(args: List[str], cwd: Optional[str] = None) -> str:
    """Helper to run git commands"""
    try:
        result = subprocess.run(
            ["git"] + args,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error running git {' '.join(args)}:\n{e.stderr}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@tool
def git_status() -> str:
    """
    Get the current git status (changed files, staged files, branch info).
    Useful to check the state before committing or after editing.
    """
    return _run_git(["status"])

@tool
def git_log(limit: int = 10) -> str:
    """
    View the commit history.
    Args:
        limit: Number of commits to show (default: 10)
    """
    # --oneline for brevity, --graph for structure
    return _run_git(["log", f"-{limit}", "--oneline", "--graph", "--decorate"])

@tool
def git_diff(target: Optional[str] = None) -> str:
    """
    See changes in the working directory or between commits.
    Args:
        target: The file, branch, or commit to diff against. 
                If None, shows diff of unstaged changes.
                Pass '--cached' to see staged changes.
    """
    args = ["diff"]
    if target:
        args.append(target)
    return _run_git(args)

@tool
def git_branch_list() -> str:
    """List all local branches."""
    return _run_git(["branch", "-vv"])

@tool
def git_checkout(branch: str, create_new: bool = False) -> str:
    """
    Switch to a branch or create a new one.
    Args:
        branch: Name of the branch to checkout.
        create_new: If True, treats 'branch' as a new branch name and creates it (-b).
    """
    args = ["checkout"]
    if create_new:
        args.append("-b")
    args.append(branch)
    return _run_git(args)

@tool
def git_commit(message: str, add_all: bool = False) -> str:
    """
    Commit changes.
    Args:
        message: The commit message.
        add_all: If True, stages all modified files (git add -u) before committing.
                 Does NOT add untracked files unless you ran 'git add' explicitly.
    """
    output = []
    if add_all:
        add_res = _run_git(["add", "-u"])
        if "Error" in add_res:
            return f"Failed to stage files: {add_res}"
        output.append("Staged modified files.")

    res = _run_git(["commit", "-m", message])
    output.append(res)
    return "\n".join(output)

@tool
def git_show(ref: str) -> str:
    """
    Show details of a specific commit or object.
    Args:
        ref: Commit hash, branch name, or tag.
    """
    return _run_git(["show", ref])
