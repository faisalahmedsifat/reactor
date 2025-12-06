# Project Analysis Feature

## Overview

Your Reactive Shell Agent already has a powerful **analytical workflow** that can recursively analyze projects! When you ask it to "analyze this project", it automatically detects this as an analytical request and follows a specialized workflow.

## How It Works

### 1. Intent Detection
When you say phrases like:
- "analyze this project"
- "summarize the codebase"
- "what does this project do"
- "review this code"

The agent's LLM classifies this as an **analytical task** (categories: `analysis`, `information_gathering`, or `code_review`) and sets `is_analytical = true`.

### 2. Analytical Workflow

The agent then follows this specialized flow:

#### Step 1: **Discover Files** (`discover_files_node`)
- Recursively analyzes project structure using `analyze_project_structure` tool
- Lists all files up to 3 levels deep with `list_project_files` tool
- Identifies:
  - Project type (Python, TypeScript, etc.)
  - Total files and directories
  - File categories (source code, configs, docs, etc.)
  - Git repository status
  - Key configuration files
  - Entry points

#### Step 2: **Read Relevant Files** (`read_relevant_files_node`)
Intelligently selects and reads the most important files:

**Priority 1: README files** (first README found)
**Priority 2: Configuration files** (up to 3 files like `pyproject.toml`, `package.json`, `.env`)
**Priority 3: Entry points** (up to 2 files like `main.py`, `index.ts`, `app.py`)
**Priority 4: Source files** (up to 3 Python/TypeScript/JavaScript files)

**Total limit**: Up to 10 files, max 200 lines per file

#### Step 3: **Analyze and Summarize** (`analyze_and_summarize_node`)
Uses the LLM to analyze all collected information and provides:

1. **Project Purpose**: What the project does
2. **Architecture**: How it's structured, key components
3. **Technologies**: Frameworks, libraries, tools used
4. **Main Features**: Core functionalities
5. **Insights**: Design patterns, notable decisions, areas for improvement

## Example Usage

Simply run your TUI and type:

```
analyze this project
```

The agent will:
1. ✓ Discover all files in the current directory
2. ✓ Read README, config files, and main source files
3. ✓ Generate a comprehensive analysis using AI
4. ✓ Present findings in a structured markdown format

## File Tools Used

The analysis uses these specialized tools from `src/tools/file_tools.py`:

- `analyze_project_structure` - Detects project type, finds key files, identifies entry points
- `list_project_files` - Lists all files recursively with categorization
- `read_file_content` - Reads file contents with line limits for performance

## Customization

You can modify the analytical behavior in:

- **`src/nodes/analysis_nodes.py`** - Change which files are read, how many, priority order
- **`src/nodes/llm_nodes.py`** - Modify the intent detection prompt to recognize more analytical phrases
- **`src/graph.py`** - Adjust routing logic between analytical and execution flows

## Current Limitations

- Reads up to 10 files maximum (can be increased in `read_relevant_files_node`)
- Max 200 lines per file (configurable via `max_lines` parameter)
- Depth limited to 3 levels for file listing (can be adjusted in `discover_files_node`)
- File contents truncated to 1000 chars when sent to LLM (see line 158 in `analyze_and_summarize_node`)

## Performance

The analytical workflow is optimized for performance:
- Smart file selection avoids reading every file
- Line limits prevent overwhelming the LLM context
- Prioritizes high-value files (READMEs, configs, entry points)
- Categorizes files by type for intelligent selection

## Try It Now!

```powershell
poetry run python .\src\main.py
```

Then in the TUI, type:
```
analyze this project
```

Watch as the agent recursively explores your codebase and provides intelligent insights! 🚀
