"""
src/nodes/analysis_nodes.py

Analysis workflow nodes for file-based analytical tasks.
Used when user asks to "analyze project", "summarize codebase", etc.
"""

from src.state import ShellAgentState
from langchain_core.messages import AIMessage
from src.tools import file_tools
import json


async def discover_files_node(state: ShellAgentState) -> ShellAgentState:
    """
    Discover all files in the project using file tools.
    """
    system_info = state["system_info"]
    working_dir = system_info["working_directory"]
    
    # Use file tools to discover project structure
    # NOTE: analyze_project_structure removed as it was unreliable.
    # We rely on raw file listing now.
    file_listing = await file_tools.list_project_files.ainvoke({"directory": working_dir, "max_depth": 3})
    
    # Store in state for later use
    state["analysis_data"] = {
        "project_structure": {"project_types": ["Detected via extension"], "key_files": {}}, # Skeleton for compatibility
        "file_listing": file_listing
    }
    
    # Create user-facing message
    total_files = file_listing.get("total_files", 0)
    total_dirs = file_listing.get("total_directories", 0)
    
    categories_summary = "\n".join([
        f"- **{cat}**: {len(files)} files" 
        for cat, files in file_listing.get("files_by_category", {}).items()
        if files
    ])
    
    msg = f"""🔍 **File Discovery Complete**

**Location**: `{working_dir}`
**Files**: {total_files} files across {total_dirs} directories

**File Categories**:
{categories_summary}

Now reading key files..."""
    
    state["messages"].append(AIMessage(content=msg))
    return state


async def read_relevant_files_node(state: ShellAgentState) -> ShellAgentState:
    """
    Read content of key files (README, config files, main code files).
    """
    analysis_data = state.get("analysis_data", {})
    project_structure = analysis_data.get("project_structure", {})
    file_listing = analysis_data.get("file_listing", {})
    
    files_to_read = []
    file_contents = {}
    
    # Priority 1: README files
    readme_files = project_structure.get("readme_files", [])
    files_to_read.extend(readme_files[:1])  # Read first README
    
    # Priority 2: Key configuration files
    key_files = project_structure.get("key_files", {})
    files_to_read.extend(list(key_files.values())[:3])  # Read up to 3 config files
    
    # Priority 3: Entry points
    entry_points = project_structure.get("entry_points", [])
    files_to_read.extend(entry_points[:2])  # Read up to 2 entry points
    
    # Priority 4: Main source files from categories
    files_by_category = file_listing.get("files_by_category", {})
    
    # Read a few Python files
    python_files = files_by_category.get("Python", [])
    for py_file in python_files[:3]:  # Read up to 3 Python files
        if py_file not in files_to_read:
            files_to_read.append(py_file)
    
    # Read a few TypeScript/JavaScript files
    ts_files = files_by_category.get("TypeScript/JavaScript", [])
    for ts_file in ts_files[:3]:  # Read up to 3 TS/JS files
        if ts_file not in files_to_read:
            files_to_read.append(ts_file)
    
    # Limit total files to read (performance)
    files_to_read = files_to_read[:10]
    
    # Read files
    files_read = []
    total_lines = 0
    
    for file_path in files_to_read:
        result = await file_tools.read_file_content.ainvoke({"file_path": file_path, "max_lines": 200})
        
        if "error" not in result:
            file_contents[file_path] = result["content"]
            files_read.append(file_path)
            total_lines += result["lines_returned"]
    
    # Store file contents in state
    if "analysis_data" not in state:
        state["analysis_data"] = {}
    state["analysis_data"]["file_contents"] = file_contents
    
    # Create user-facing message
    files_list = "\n".join([f"- `{f}`" for f in files_read])
    
    msg = f"""📖 **File Reading Complete**

**Files Read**: {len(files_read)}
**Total Lines**: {total_lines}

**Files Analyzed**:
{files_list}

Analyzing contents and generating summary..."""
    
    state["messages"].append(AIMessage(content=msg))
    return state


async def analyze_and_summarize_node(state: ShellAgentState) -> ShellAgentState:
    """
    Use LLM to analyze file contents and provide comprehensive summary.
    """
    from src.nodes.llm_nodes import get_llm_client
    from langchain_core.messages import SystemMessage, HumanMessage
    
    llm_client = get_llm_client()
    analysis_data = state.get("analysis_data", {})
    
    project_structure = analysis_data.get("project_structure", {})
    file_listing = analysis_data.get("file_listing", {})
    file_contents = analysis_data.get("file_contents", {})
    
    # Build context for LLM
    project_types = ", ".join(project_structure.get("project_types", ["Unknown"]))
    total_files = file_listing.get("total_files", 0)
    
    # Format file contents for LLM
    files_context = []
    for file_path, content in file_contents.items():
        files_context.append(f"### {file_path}\n```\n{content[:1000]}\n```\n")  # Truncate to 1000 chars per file
    
    files_context_str = "\n\n".join(files_context)
    
    system_prompt = """You are an expert software analyst. Analyze the provided project files and provide a comprehensive summary.

Focus on:
1. **Project Purpose**: What does this project do?
2. **Architecture**: How is it structured? Key components?
3. **Technologies**: What frameworks, libraries, tools are used?
4. **Main Features**: What are the core functionalities?
5. **Insights**: Any notable patterns, design decisions, or areas for improvement?

Be concise but thorough. Use markdown formatting."""

    user_prompt = f"""Analyze this project:

**Project Type**: {project_types}
**Total Files**: {total_files}

**File Contents**:

{files_context_str}

Provide a comprehensive analysis of what this project does and how it works."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    # Invoke LLM
    response = await llm_client.ainvoke(messages)
    
    # Format final analysis message
    analysis_msg = f"""💭 **Project Analysis**

{response.content}

---

*Analysis based on {len(file_contents)} files from the project.*"""
    
    state["messages"].append(AIMessage(content=analysis_msg))
    return state
