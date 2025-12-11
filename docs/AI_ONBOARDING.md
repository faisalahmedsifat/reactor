# AI Agent Onboarding Guide for ReACTOR

> **Quick Reference**: This document provides everything an AI agent needs to understand, navigate, and contribute to the ReACTOR project.

---

## 📋 Table of Contents

1. [Project Identity](#project-identity)
2. [Quick Navigation](#quick-navigation)
3. [Architecture Overview](#architecture-overview)
4. [Folder Structure](#folder-structure)
5. [Core Concepts](#core-concepts)
6. [Key Modules Deep Dive](#key-modules-deep-dive)
7. [Data Flow](#data-flow)
8. [Configuration System](#configuration-system)
9. [Tool System](#tool-system)
10. [TUI System](#tui-system)
11. [Development Setup](#development-setup)
12. [Common Tasks & Patterns](#common-tasks--patterns)
13. [Feature Implementation Guide](#feature-implementation-guide)
14. [Testing](#testing)
15. [Current Status & Roadmap](#current-status--roadmap)

---

## Project Identity

| Property | Value |
|----------|-------|
| **Name** | ReACTOR (Reactive Shell Agent) |
| **Type** | LLM-powered shell automation agent |
| **Version** | 0.2.0 |
| **Python** | 3.10+ |
| **Package Manager** | Poetry |
| **Main Frameworks** | LangGraph, LangChain, Textual |
| **LLM Providers** | Anthropic (Claude), OpenAI (GPT), Google (Gemini), Ollama |
| **Entry Point** | `reactor` CLI command or `src/main.py` |

---

## Quick Navigation

### Essential Files

| File | Purpose | Path |
|------|---------|------|
| **Entry Point** | CLI/TUI launcher | [src/main.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/main.py) |
| **Graph Definition** | LangGraph workflow | [src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py) |
| **Agent State** | TypedDict for state | [src/state.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/state.py) |
| **Models** | Pydantic data models | [src/models.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/models.py) |
| **System Prompts** | Centralized prompts (YAML) | [src/prompts/system_prompts.yaml](file:///home/faisal/Workspace/Dev/Personal/reactor/src/prompts/system_prompts.yaml) |
| **Dependencies** | Poetry config | [pyproject.toml](file:///home/faisal/Workspace/Dev/Personal/reactor/pyproject.toml) |

### Node Files

| Node | Purpose | Path |
|------|---------|------|
| **Thinking Node** | Pure reasoning, planning | [src/nodes/thinking_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/thinking_nodes.py) |
| **Agent Node** | Tool selection & execution | [src/nodes/agent_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/agent_nodes.py) |

### Tool Files

| Tool Module | Purpose | Path |
|-------------|---------|------|
| **Shell Tools** | Command execution, safety | [src/tools/shell_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/shell_tools.py) |
| **File Tools** | Read/write/search files | [src/tools/file_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/file_tools.py) |
| **Web Tools** | Web search, crawling | [src/tools/web_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/web_tools.py) |
| **Git Tools** | Git operations | [src/tools/git_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/git_tools.py) |
| **Todo Tools** | Task management | [src/tools/todo_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/todo_tools.py) |
| **Grep/Log Tools** | Advanced search, log parsing | [src/tools/grep_and_log_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/grep_and_log_tools.py) |

### TUI Files

| Component | Purpose | Path |
|-----------|---------|------|
| **Main App** | Textual app class | [src/tui/app.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/app.py) |
| **Bridge** | LangGraph ↔ TUI connector | [src/tui/bridge.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/bridge.py) |
| **Styles** | Cyberpunk CSS (TCSS) | [src/tui/styles.tcss](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/styles.tcss) |
| **Agent UI Widget** | Main dashboard widget | [src/tui/widgets/agent_ui.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/widgets/agent_ui.py) |

### LLM Files

| Component | Purpose | Path |
|-----------|---------|------|
| **Factory** | Multi-provider LLM factory | [src/llm/factory.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/llm/factory.py) |
| **Client** | LLM client getter | [src/llm/client.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/llm/client.py) |

---

## Architecture Overview

ReACTOR uses a **Simplified ReAct Loop** implemented with LangGraph:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  THINKING   │────▶│   AGENT     │────▶│   TOOLS     │
│   (Brain)   │     │   (Hands)   │     │  (Actions)  │
│             │◀────│             │◀────│             │
│ Pure reason │     │ Tool select │     │  Execute    │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       └───────────────────┴─────────▶ END
                  (when complete)
```

### Design Philosophy

1. **Thinking (Brain)**: Pure reasoning node. Analyzes state, plans next steps. Does NOT call tools directly.
2. **Agent (Hands)**: Execution node. Binds tools to LLM and executes based on thinking output.
3. **Tools (Actions)**: Actual execution layer (shell, file I/O, web, git).

### Flow Pattern

```
User Input → Thinking → Agent → Tools → Thinking → Agent → ... → END
```

---

## Folder Structure

```
reactor/
├── src/                          # Main source code
│   ├── main.py                   # Entry point (CLI args, env config)
│   ├── graph.py                  # LangGraph workflow definition
│   ├── state.py                  # ShellAgentState TypedDict
│   ├── models.py                 # Pydantic models (Intent, Plan, Result)
│   ├── logger.py                 # Logging configuration
│   │
│   ├── nodes/                    # LangGraph nodes
│   │   ├── __init__.py
│   │   ├── thinking_nodes.py     # Pure reasoning node
│   │   └── agent_nodes.py        # Tool execution node
│   │
│   ├── tools/                    # LangChain tools
│   │   ├── __init__.py           # Tool exports
│   │   ├── shell_tools.py        # execute_shell_command, get_system_info, etc.
│   │   ├── file_tools.py         # read_file, write_file, modify_file, search_in_files
│   │   ├── web_tools.py          # web_search, recursive_crawl
│   │   ├── git_tools.py          # git_status, git_log, git_diff, etc.
│   │   ├── todo_tools.py         # create_todo, complete_todo, list_todos
│   │   └── grep_and_log_tools.py # grep_advanced, parse_log_file, etc.
│   │
│   ├── tui/                      # Textual TUI
│   │   ├── __init__.py
│   │   ├── app.py                # ShellAgentTUI main app
│   │   ├── bridge.py             # AgentBridge (LangGraph ↔ TUI)
│   │   ├── state.py              # TUI state management
│   │   ├── styles.tcss           # Cyberpunk styling
│   │   └── widgets/              # Custom widgets
│   │       ├── agent_ui.py       # AgentDashboard, LogViewer, ChatInput
│   │       ├── chat_widgets.py   # Chat-related widgets
│   │       ├── code_viewer.py    # Code display widget
│   │       ├── diff_viewer.py    # Diff display widget
│   │       ├── file_tree.py      # File explorer
│   │       ├── modals.py         # FuzzyFinder, CommandPalette
│   │       ├── file_autocomplete.py
│   │       ├── file_reference_modal.py
│   │       └── todo_panel.py     # Todo list widget
│   │
│   ├── llm/                      # LLM integration
│   │   ├── __init__.py
│   │   ├── factory.py            # LLMFactory (multi-provider)
│   │   ├── client.py             # get_llm_client()
│   │   ├── base.py               # Base LLM classes
│   │   └── langchain_client.py   # LangChain adapter
│   │
│   ├── prompts/                  # Prompt management
│   │   ├── __init__.py           # get_prompt() function
│   │   └── system_prompts.yaml   # Centralized prompts
│   │
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── conversation_compactor.py  # Token management
│
├── tests/                        # Test suite
│   ├── __init__.py
│   └── test_smoke.py             # Basic smoke tests
│
├── .github/                      # GitHub config
│   ├── workflows/                # CI/CD
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── pyproject.toml                # Poetry config & dependencies
├── poetry.lock                   # Locked dependencies
├── README.md                     # User documentation
├── DOCUMENTATION.md              # Technical documentation
├── CONTRIBUTING.md               # Contribution guidelines
├── CODE_OF_CONDUCT.md            # Code of conduct
├── LICENSE                       # MIT License
├── .env.example                  # Environment template
└── shell_agent_graph_simple.png  # Architecture diagram
```

---

## Core Concepts

### 1. ShellAgentState

The central state object passed between all nodes (defined in [src/state.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/state.py)):

```python
class ShellAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]  # Conversation history
    user_input: str                                            # Current user request
    system_info: Optional[dict]                                 # OS, shell, CWD info
    intent: Optional[CommandIntent]                             # Parsed intent
    execution_plan: Optional[ExecutionPlan]                     # Command plan
    current_command_index: int                                  # Execution progress
    results: List[ExecutionResult]                              # Command results
    retry_count: int                                            # Current retry attempts
    requires_approval: bool                                     # Needs user approval?
    approved: bool                                              # User approved?
    error: Optional[str]                                        # Error message
    execution_mode: Literal["sequential", "parallel"]           # Execution strategy
    max_retries: int                                            # Max retry limit (default: 3)
    analysis_data: Optional[Dict[str, Any]]                     # Analytical data
```

### 2. Dual-Mode Architecture

- **Analytical Mode**: Read-only operations (file reading, project analysis, code understanding)
- **Execution Mode**: Shell command execution with safety checks and approval workflows

### 3. Safety Levels

Commands are categorized by risk:
- **✅ Safe**: Auto-execute (e.g., `ls`, `pwd`, `echo`)
- **⚠️ Moderate**: Require approval (e.g., `touch`, `mkdir`)
- **🔴 Dangerous**: Require explicit approval (e.g., `rm`, `chmod`, `sudo`)

---

## Key Modules Deep Dive

### 1. Graph Workflow ([src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py))

The `create_shell_agent()` function builds the LangGraph workflow:

```python
def create_shell_agent():
    workflow = StateGraph(ShellAgentState)
    
    # Add nodes
    workflow.add_node("thinking", thinking_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(all_tools))
    
    # Set edges
    workflow.set_entry_point("thinking")
    workflow.add_edge("thinking", "agent")
    workflow.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "thinking": "thinking",
        "end": END
    })
    workflow.add_edge("tools", "thinking")
    
    return workflow.compile(checkpointer=MemorySaver())
```

### 2. Thinking Node ([src/nodes/thinking_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/thinking_nodes.py))

Pure reasoning without tool execution:
- Refreshes system info
- Loads system prompt from YAML
- Auto-compacts conversation if too long (>50k tokens)
- Produces reasoning text for the Agent node

### 3. Agent Node ([src/nodes/agent_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/agent_nodes.py))

Tool selection and execution:
- Binds all tools to LLM
- Constructs context-aware system prompt
- Invokes LLM to call tools or provide final answer

### 4. TUI Bridge ([src/tui/bridge.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/bridge.py))

Connects LangGraph to Textual TUI:
- `process_request()`: Runs agent with streaming
- `handle_thinking_node()`: Updates UI with reasoning
- `handle_agent_node()`: Shows tool calls
- `handle_tools_node()`: Displays tool results

---

## Data Flow

### Request Processing Flow

```
1. User types message in TUI Input
   └── src/tui/app.py::on_chat_input_submitted()

2. Message sent to Bridge
   └── src/tui/bridge.py::process_request()

3. Initial state created with HumanMessage
   └── Passed to LangGraph workflow

4. Thinking Node analyzes
   └── src/nodes/thinking_nodes.py::thinking_node()
   └── Produces reasoning text

5. Agent Node selects tools
   └── src/nodes/agent_nodes.py::agent_node()
   └── LLM decides: call tool OR respond

6. If tool_calls:
   └── Tools Node executes
   └── Results added to messages
   └── Loop back to Thinking

7. If no tool_calls with content:
   └── END - Response shown in TUI
```

### State Updates Flow

```
State flows through nodes:
┌─────────────────────────────────────────────────────────────┐
│ Initial State                                                │
│ - messages: [HumanMessage(user_input)]                      │
│ - system_info: None                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ After Thinking Node                                          │
│ - messages: [..., AIMessage(reasoning)]                      │
│ - system_info: {os, shell, cwd, git_info, python_version}   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ After Agent Node                                             │
│ - messages: [..., AIMessage(tool_calls=[...])]              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ After Tools Node                                             │
│ - messages: [..., ToolMessage(result)]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration System

### Environment Variables

The project uses `.env` for configuration. Key variables:

```env
# LLM Provider Selection
LLM_PROVIDER=anthropic    # Options: anthropic, openai, google, ollama

# Model Selection
LLM_MODEL=claude-sonnet-4-20250514  # Provider-specific model name

# API Keys (one per provider)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...

# Optional
LOG_LEVEL=INFO
```

### CLI Configuration

Override via command line:

```bash
reactor --provider google --model gemini-2.5-flash --api-key YOUR_KEY
```

Configuration is automatically saved to `.env` for persistence.

### Configuration Flow

```
1. CLI args parsed (src/main.py::parse_args)
2. Environment configured (src/main.py::configure_environment)
   - Provider auto-detection from available keys
   - Model alignment with provider
3. Config saved to .env (src/main.py::save_configuration)
4. Validation (src/main.py::validate_config)
5. LLM Factory creates client (src/llm/factory.py)
```

---

## Tool System

### Tool Definition Pattern

All tools use `@tool` decorator from `langchain_core.tools`:

```python
from langchain_core.tools import tool

@tool
def example_tool(param: str, optional: int = 10) -> dict:
    """
    Brief description of tool purpose.
    
    Args:
        param: Description of parameter
        optional: Description with default
        
    Returns:
        Dictionary with operation result
    """
    # Implementation
    return {"success": True, "result": ...}
```

### Available Tools

#### Shell Tools ([src/tools/shell_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/shell_tools.py))
- `get_system_info()`: OS, shell, CWD, permissions
- `execute_shell_command(command, working_directory, timeout, dry_run)`: Run commands
- `validate_command_safety(command)`: Risk assessment
- `analyze_command_error(command, error_output, exit_code)`: Error analysis
- `check_path_exists(path)`: Path validation
- `parse_user_intent(user_request)`: Intent parsing
- `generate_command_plan(task_description)`: Plan generation

#### File Tools ([src/tools/file_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/file_tools.py))
- `list_project_files(directory, max_depth, ignore_patterns)`: Directory tree
- `read_file_content(file_path, max_lines)`: Read files
- `write_file(file_path, content, mode)`: Create files (mode="create" default)
- `modify_file(file_path, search_text, replace_text, occurrence)`: Edit files
- `search_in_files(pattern, directory, file_extensions, max_results)`: Grep-like search

#### Git Tools ([src/tools/git_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/git_tools.py))
- `git_status()`: Repository status
- `git_log()`: Commit history
- `git_diff()`: Show changes
- `git_branch_list()`: List branches
- `git_checkout(branch)`: Switch branches
- `git_commit(message)`: Create commits
- `git_show(commit)`: Show commit details

#### Web Tools ([src/tools/web_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/web_tools.py))
- `web_search(query)`: DuckDuckGo search
- `recursive_crawl(url, max_depth)`: Website crawling

#### Todo Tools ([src/tools/todo_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/todo_tools.py))
- `create_todo(title, description)`: Create task
- `complete_todo(todo_id)`: Mark complete
- `list_todos()`: List all tasks
- `update_todo(todo_id, title, description)`: Update task

#### Advanced Search Tools ([src/tools/grep_and_log_tools.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/grep_and_log_tools.py))
- `grep_advanced(pattern, path, options)`: Advanced grep
- `tail_file(file_path, lines)`: File tail
- `parse_log_file(file_path, format)`: Log parsing
- `extract_json_fields(json_path, fields)`: JSON extraction
- `filter_command_output(command, filter_pattern)`: Output filtering
- `analyze_error_logs(log_path)`: Error analysis

### Adding New Tools

1. Create tool function with `@tool` decorator
2. Add to appropriate file in `src/tools/`
3. Export in `src/tools/__init__.py`
4. Add to `all_tools` list in:
   - [src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py#L28-L57)
   - [src/nodes/agent_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/agent_nodes.py#L30-L52)

---

## TUI System

### Widget Hierarchy

```
ShellAgentTUI (App)
├── Header (title bar)
├── Container#main-layout
│   ├── Vertical#col-files (left sidebar)
│   │   └── FileExplorer
│   ├── Vertical#col-agent (center)
│   │   └── AgentDashboard
│   │       ├── LogViewer (conversation display)
│   │       └── ChatInput (user input)
│   └── Vertical#col-context (right panel)
│       ├── CodeViewer
│       └── TodoPanel
└── StatusBar (footer)
```

### Key Bindings

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit (double-press to confirm) |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+X` | Toggle context panel |
| `Ctrl+P` | Fuzzy file finder |
| `Ctrl+K` | Command palette |
| `Escape` | Cancel running agent |
| `Ctrl+L` | Clear logs |

### Slash Commands

| Command | Action |
|---------|--------|
| `/clear` | Clear conversation log |
| `/help` | Show help message |
| `/compact` | Manually compact conversation history |

### Message Types & Styling

Messages are styled based on content prefix:

| Prefix | Title | Color | Use Case |
|--------|-------|-------|----------|
| `💡` | 🧠 Understanding | Gold | Intent explanation |
| `🛠️` | Activity | Default | Tool usage |
| `⚡` | Progress | Green | Execution updates |
| `💬` | User | Purple | User messages |
| - | Thinking | Slate Blue | Reasoning |
| - | Agent | Cyan | Agent responses |
| - | Error | Red | Error messages |

---

## Development Setup

### Prerequisites

- Python 3.10+
- Poetry (recommended) or pip

### Installation

```bash
# Clone repository
git clone https://github.com/faisalahmedsifat/reactor.git
cd reactor

# Install with Poetry (recommended)
poetry install

# Or with pip
pip install -e .
```

### Environment Setup

```bash
# Copy example env
cp .env.example .env

# Edit .env with your API key
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
```

### Running

```bash
# TUI mode (default)
reactor
# or
poetry run reactor

# CLI mode
reactor --cli

# Debug mode (enables logging)
reactor --debug

# With specific provider
reactor --provider google --model gemini-2.5-flash
```

### Development Commands

```bash
# Run tests
poetry run pytest

# Format code
poetry run black src/ tests/

# Type checking (if added)
poetry run mypy src/
```

---

## Common Tasks & Patterns

### 1. Adding a New LLM Provider

1. Add config to [src/llm/factory.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/llm/factory.py#L28-L53):
```python
configs = {
    # ... existing providers
    "new_provider": {
        "model": model or "default-model",
        "api_key": os.getenv("NEW_PROVIDER_API_KEY"),
        "import": "langchain_new_provider",
        "class": "ChatNewProvider",
    },
}
```

2. Update CLI choices in [src/main.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/main.py#L32-L35)
3. Add key mapping in `configure_environment()` and `save_configuration()`

### 2. Adding a New Tool

1. Create function in appropriate `src/tools/*.py` file:
```python
@tool
def my_new_tool(param: str) -> dict:
    """Tool description."""
    return {"success": True}
```

2. Export in [src/tools/__init__.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tools/__init__.py)

3. Add to `all_tools` in:
   - [src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py) (around line 28-57)
   - [src/nodes/agent_nodes.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/nodes/agent_nodes.py) (around line 30-52)

### 3. Modifying System Prompts

Edit [src/prompts/system_prompts.yaml](file:///home/faisal/Workspace/Dev/Personal/reactor/src/prompts/system_prompts.yaml):

```yaml
thinking:
  system: |
    Your prompt here with {placeholders}
    
agent:
  system: |
    Agent prompt with {os_type}, {shell_type}, etc.
```

Placeholders are filled by `get_prompt()` function.

### 4. Adding a TUI Widget

1. Create widget in `src/tui/widgets/`:
```python
from textual.widgets import Static

class MyWidget(Static):
    def compose(self):
        # Widget composition
        ...
```

2. Add styles in [src/tui/styles.tcss](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/styles.tcss)

3. Import and use in [src/tui/app.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/tui/app.py)

### 5. Modifying the Graph Workflow

Edit [src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py):

```python
# Add new node
workflow.add_node("my_node", my_node_function)

# Add edges
workflow.add_edge("thinking", "my_node")
workflow.add_conditional_edges("my_node", my_condition, {...})
```

---

## Feature Implementation Guide

### Pattern for New Features

1. **Define State Fields** (if needed): Add to `ShellAgentState` in [src/state.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/state.py)

2. **Create/Modify Tools**: Add tool functions in `src/tools/`

3. **Update Prompts**: Modify [src/prompts/system_prompts.yaml](file:///home/faisal/Workspace/Dev/Personal/reactor/src/prompts/system_prompts.yaml)

4. **Update Graph** (if needed): Modify workflow in [src/graph.py](file:///home/faisal/Workspace/Dev/Personal/reactor/src/graph.py)

5. **Update TUI** (if needed): Add widgets/handlers in `src/tui/`

6. **Add Tests**: Create tests in `tests/`

### Example: Adding Semantic Search Feature

1. Add state field:
```python
# src/state.py
embeddings_db: Optional[str]  # Path to embeddings database
```

2. Create tools:
```python
# src/tools/search_tools.py
@tool
def semantic_search(query: str, top_k: int = 5) -> dict:
    """Search for semantically similar content."""
    ...
```

3. Update prompts to inform agent about new capability

4. Wire up in graph and agent_nodes

---

## Testing

### Current Test Setup

- Framework: pytest
- Location: `tests/`
- Smoke tests: [tests/test_smoke.py](file:///home/faisal/Workspace/Dev/Personal/reactor/tests/test_smoke.py)

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_smoke.py
```

### Test Patterns

```python
# tests/test_new_feature.py
import pytest
from src.tools.my_tools import my_tool

def test_my_tool_basic():
    result = my_tool("input")
    assert result["success"] is True
```

---

## Current Status & Roadmap

### ✅ Completed Features

- LangGraph workflow with Thinking → Agent → Tools loop
- Dual-mode architecture (analytical + execution)
- Multi-provider LLM support (Anthropic, OpenAI, Google, Ollama)
- File and shell tools
- Git integration
- Cyberpunk TUI with file explorer, chat, and code viewer
- Conversation compaction for long sessions
- Centralized prompt management (YAML)
- CLI argument configuration with auto-save

### 🚧 In Progress

- Parallel execution (UI toggle exists, implementation incomplete)
- Conversation persistence across restarts

### 📋 Planned Features

- Semantic code search
- Plugin system for custom tools
- Multi-step task planning
- Export conversation history
- VSCode extension
- API server mode

---

## Quick Reference

### Important Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `create_shell_agent()` | src/graph.py | Creates LangGraph workflow |
| `thinking_node()` | src/nodes/thinking_nodes.py | Pure reasoning step |
| `agent_node()` | src/nodes/agent_nodes.py | Tool selection/execution |
| `get_llm_client()` | src/llm/client.py | Returns configured LLM |
| `get_prompt()` | src/prompts/__init__.py | Loads prompts from YAML |
| `run_tui()` | src/tui/app.py | Starts TUI application |
| `AgentBridge.process_request()` | src/tui/bridge.py | Processes user requests |

### State Fields Quick Reference

| Field | Type | Purpose |
|-------|------|---------|
| `messages` | `Sequence[BaseMessage]` | Conversation history |
| `user_input` | `str` | Current user request |
| `system_info` | `dict` | OS, shell, CWD info |
| `execution_mode` | `Literal["sequential", "parallel"]` | Execution strategy |
| `results` | `List[ExecutionResult]` | Command results |
| `retry_count` | `int` | Current retry attempts |
| `max_retries` | `int` | Max allowed retries |

---

**Last Updated**: December 9, 2024  
**Version**: 0.2.0
