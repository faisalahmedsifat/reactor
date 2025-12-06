# Plan for Implementing Web Searching Features

## 1. Objective
Integrate web searching capabilities into the shell agent to allow it to gather external information, answer questions requiring up-to-date data, and enhance its problem-solving abilities.

## 2. Chosen Web Search API
For this plan, we will assume the use of a generic `web_search` tool. In a real implementation, this would be backed by a specific API like:
*   **Google Search API**: For general web searches.
*   **SerpAPI/Serper API**: Provides structured search results from various search engines.
*   **Custom Scraper**: For highly specific or niche information if public APIs are insufficient.

**Recommendation**: Start with a wrapper around a service like SerpAPI or Serper API due to their ease of use and structured output.

## 3. Implementation Steps

### 3.1. Create a New Tool Module (`src/tools/web_tools.py`)

*   **File**: `src/tools/web_tools.py`
*   **Content**:
    *   Define a function, e.g., `web_search(query: str) -> str`.
    *   This function will:
        *   Take a `query` string as input.
        *   Make an API call to the chosen web search service (e.g., SerpAPI).
        *   Parse the relevant information from the API response (e.g., top N results, snippets).
        *   Return a concise string summary of the search results.
    *   **Error Handling**: Implement robust error handling for API failures, network issues, and empty results.
    *   **Configuration**: The API key for the web search service should be loaded from environment variables (e.g., `SERPAPI_API_KEY` or `GOOGLE_SEARCH_API_KEY`).

### 3.2. Integrate the New Tool into the Agent Workflow

*   **File**: `src/graph_simple.py`
*   **Modifications**:
    1.  **Import the new tool**:
        ```python
        from src.tools import shell_tools, file_tools, web_tools # Add web_tools
        ```
    2.  **Add `web_search` to `all_tools` list**:
        Locate the `all_tools` list within `create_simple_shell_agent` and `agent_node` and add `web_tools.web_search` to it.
        ```python
        all_tools = [
            # ... existing tools ...
            file_tools.search_in_files,
            web_tools.web_search, # Add this line
        ]
        ```
    3.  **Update System Message (in `agent_node`)**:
        Modify the `AIMessage` content to inform the LLM about the new `web_search` tool. This is crucial for the LLM to know when and how to use it.
        ```python
        system_message = AIMessage(content=f"""You are the **EXECUTION UNIT** of the shell agent.
        ...
        Available Tools:
        1. **Shell Commands**: execute_shell_command - Run any shell command
        2. **File Reading**: read_file_content - Read file contents
        3. **File Writing**: write_file - Create or modify files
        4. **File Editing**: modify_file - Search and replace within files
        5. **File Search**: search_in_files - Find text in files (grep-like, case-insensitive)
        6. **Project Analysis**: list_project_files
        7. **Web Search**: web_search - Search the internet for information (e.g., current events, documentation, solutions to errors) # Add this line

        **CRITICAL RULES**:
        ...
        """)
        ```

### 3.3. Update `src/tools/__init__.py` (Optional but Recommended)

*   **File**: `src/tools/__init__.py`
*   **Modifications**: Add `from . import web_tools` to ensure `web_tools` is part of the `tools` package.

## 4. Testing

*   **Unit Tests**: Create unit tests for `web_tools.py` to ensure the web search function correctly handles various queries, parses results, and manages errors.
*   **Integration Tests**: Test the agent's ability to use the `web_search` tool within the `run_simple_agent` workflow.
    *   Example test cases:
        *   "What is the current weather in London?"
        *   "How do I use `os.path.join` in Python?"
        *   "Search for recent news about AI."
        *   "Find documentation for LangGraph `ToolNode`."

## 5. Future Considerations

*   **Rate Limiting**: Implement rate limiting for the web search API calls to avoid exceeding quotas.
*   **Caching**: Cache search results for frequently asked queries to reduce API calls and improve performance.
*   **Result Summarization**: For long search results, consider using an LLM to summarize the findings before presenting them to the agent or user.
*   **Contextual Search**: Enhance the `web_search` tool to automatically refine queries based on the current conversation context.
*   **User Feedback**: Allow users to provide feedback on search results to improve future searches.
*   **Tool Selection Logic**: Monitor how effectively the LLM chooses to use `web_search` versus other tools. Adjust system prompts or add more sophisticated tool selection mechanisms if needed.
