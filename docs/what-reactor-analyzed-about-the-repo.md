# Project Analysis: Reactor

Based on the codebase analysis, the "Reactor" project appears to be a comprehensive AI agent framework designed for developing, managing, and executing AI agents. Its architecture emphasizes modularity, tool integration, and an interactive Text User Interface (TUI).

## Key Components and Their Functions:

*   **LLM Interaction (`src/llm`):** This module is responsible for all interactions with Large Language Models. It includes a base interface, a client for general LLM communication, a factory for creating LLM instances, and a specific client for Langchain, indicating support for various LLM providers and frameworks.

*   **Agents (`src/agents`):** This core component manages the lifecycle and behavior of AI agents. It includes:
    *   `__init__.py`: Package initialization.
    *   `manager.py`: Likely handles the creation, supervision, and coordination of multiple agent instances.
    *   `instance.py`: Defines the structure and state of an individual agent instance.
    *   `loader.py`: Responsible for loading agent definitions and configurations, possibly from files like those found in `.reactor/agents/`.

*   **Tools (`src/tools`):** This is a crucial part of the framework, providing agents with a wide array of capabilities to interact with the environment and perform tasks. The tools are categorized for different functionalities:
    *   `git_tools.py`: For performing Git operations (e.g., status, log, diff, checkout, commit).
    *   `file_tools.py`: For file system interactions (e.g., read, write, modify, search).
    *   `todo_tools.py`: For managing TODO tasks within the agent's workflow.
    *   `grep_and_log_tools.py`: For searching patterns in files and analyzing log data.
    *   `agent_tools.py`: For managing other agents (e.g., spawning, listing, stopping).
    *   `shell_tools.py`: For executing arbitrary shell commands.
    *   `web_tools.py`: For web-related tasks (e.g., web search, recursive crawling).

*   **Skills (`src/skills`):** This module likely defines and loads specific "skills" that agents can acquire and utilize. These skills could be pre-defined functionalities or learned behaviors that enhance an agent's capabilities beyond basic tool usage.

*   **Nodes (`src/nodes`):** This component suggests a graph-based or state-machine approach to agent execution.
    *   `agent_nodes.py`: Represents specific actions or states related to agent operations.
    *   `thinking_nodes.py`: Likely represents decision-making or planning stages within an agent's workflow.

*   **TUI (`src/tui`):** The Text User Interface provides an interactive console-based experience for users to interact with the Reactor framework and its agents. It includes various widgets for:
    *   `agent_ui.py`: General UI for agent interactions.
    *   `todo_panel.py`: Displaying and managing TODO tasks.
    *   `file_tree.py`: Navigating the project file structure.
    *   `code_viewer.py`: Viewing code files.
    *   `chat_widgets.py`: Facilitating chat-like interactions with agents.
    *   `autocomplete_panel.py`, `file_autocomplete.py`: Providing auto-completion features.
    *   `diff_viewer.py`: For viewing code differences.
    *   `modals.py`, `agent_editor_modal.py`, `file_reference_modal.py`, `suggestions_list.py`: For various interactive dialogs and suggestions.
    *   `styles.tcss`: Defines the styling for the TUI.
    *   `app.py`: The main application logic for the TUI.

*   **State Management (`src/state.py`, `src/tui/state.py`):** These modules are responsible for managing the overall application state and the specific state of the TUI, ensuring data consistency and responsiveness.

*   **Graph (`src/graph.py`):** This module likely defines the execution flow, dependencies, or relationships between different agents, nodes, and tools, enabling complex multi-agent workflows.

*   **Prompts (`src/prompts`):** Contains system prompts, which are crucial for guiding the behavior and responses of the LLMs used by the agents. `system_prompts.yaml` suggests a configurable approach to prompt management.

*   **Utilities (`src/utils`):** Provides general helper functions and modules, such as `conversation_compactor.py`, which might be used to optimize LLM context by summarizing past conversations.

*   **Logging (`src/logger.py`):** Implements logging functionality to record events, debug information, and errors within the application.

*   **Main Entry Point (`src/main.py`):** The primary script that initializes and runs the Reactor application.

*   **Tests (`tests`):** Contains various tests (`test_smoke.py`, `verify_parallel_agents.py`) to ensure the correctness and stability of the framework, especially concerning parallel agent execution.

*   **Documentation and Configuration:** The project includes extensive documentation (e.g., `DOCUMENTATION.md`, `README.md`, `CONTRIBUTING.md`, `AI_ONBOARDING.md`) and configuration files (e.g., `.github/workflows/ci.yaml`, `pyproject.toml`, `.env.example`). The `.reactor` directory specifically contains markdown files defining agents (`code-reviewer.md`, `web-researcher.md`) and skills (`frontend-dev.md`, `backend-api.md`), highlighting the framework's extensibility.

## Conclusion:

"Reactor" is a robust and extensible framework for building and deploying AI agents. Its design allows for the creation of intelligent agents capable of performing a wide range of tasks by leveraging LLMs, a diverse set of tools, and a structured execution flow. The interactive TUI provides a user-friendly interface for monitoring and interacting with these agents, making it a powerful platform for AI-driven automation and development.
# Detailed Codebase Analysis: Reactor

This document provides a deeper dive into the technical choices, architecture, and potential improvements for the "Reactor" AI agent framework, building upon the initial high-level overview.

## 1. Core Architecture: LangGraph and State Management

**Technical Choices:**
*   **LangGraph for Orchestration (`src/graph.py`):** Reactor leverages `langgraph` to define the flow and state transitions of its AI agents. This is a strong choice for building robust, stateful, and multi-turn agent applications. LangGraph provides a clear way to define nodes (thinking, agent, tools) and edges (conditional transitions), making the agent's decision-making process explicit and manageable.
*   **`ShellAgentState` (`src/state.py`):** A `TypedDict` is used to define the shared state across the LangGraph nodes. This provides type safety and clear structure for the data that flows through the agent's execution. Key elements like `messages`, `user_input`, `system_info`, `intent`, `execution_plan`, `results`, `active_agent`, and `active_skills` are well-defined, capturing the necessary context for an agent's operation.
*   **MemorySaver Checkpointer:** The use of `MemorySaver` for `checkpointer` in `src/graph.py` indicates that the conversation history and state are persisted in memory. This is suitable for single-session or short-lived interactions but would need to be replaced with a persistent storage solution (e.g., database, file system) for long-running or multi-user applications.

**Architecture Insights:**
*   **Reactive Loop:** The `thinking` -> `agent` -> `tools` loop is a classic reactive agent pattern. The `thinking_node` (pure reasoning) plans, the `agent_node` (tool-binding LLM) executes, and `ToolNode` performs the actual tool calls. This separation of concerns is excellent for clarity and maintainability.
*   **Conditional Edges:** The `should_continue` and `should_continue_after_tools` functions define the conditional logic for state transitions. This allows for dynamic behavior, such as immediately ending after a `spawn_agent` call or continuing to think after tool execution.
*   **Agent Delegation:** The `spawn_agent` tool and the conditional logic around it (`should_continue_after_tools`) are critical for enabling multi-agent architectures. The main agent can delegate complex tasks to specialized sub-agents, which is a powerful pattern for tackling diverse problems.

**Potential Improvements:**
*   **Persistent Checkpointing:** For production use cases, replace `MemorySaver` with a persistent checkpointer (e.g., `SQLAlchemySaver` for database persistence) to allow for agent state recovery and longer-running conversations.
*   **Error Handling in Graph:** While `try-except` blocks exist in nodes, more explicit error handling and recovery strategies within the LangGraph itself could be beneficial (e.g., dedicated error handling nodes, retry mechanisms at the graph level).
*   **Visualization/Debugging:** Integrating LangGraph's built-in visualization tools (if not already used) could greatly aid in understanding and debugging complex agent flows.

## 2. LLM Integration and Flexibility

**Technical Choices:**
*   **`LLMFactory` (`src/llm/factory.py`):** This factory pattern is well-implemented for creating `BaseChatModel` instances from various providers (Anthropic, OpenAI, Google, Ollama). This promotes modularity and makes it easy to add new LLM providers in the future.
*   **Dynamic Imports:** The use of `__import__` for dynamic loading of `langchain` modules based on the provider is a clever way to keep the codebase clean and avoid unnecessary dependencies.
*   **Environment Variable Configuration (`src/main.py`, `src/llm/client.py`):** LLM provider, model, and API keys are configured via environment variables, with CLI overrides. This is a standard and flexible approach for managing sensitive credentials and configuration.
*   **`@lru_cache` (`src/llm/client.py`):** Caching the LLM client instance ensures that the client is only initialized once, improving performance.

**Architecture Insights:**
*   **Provider Agnostic:** The design allows for easy switching between different LLM providers, which is crucial for flexibility, cost optimization, and leveraging the strengths of various models.
*   **Raw ChatModel for LangGraph:** The decision to return `BaseChatModel` directly from the factory (instead of a `ToolEnabledLLMClient` wrapper) is appropriate for LangGraph, as LangGraph handles tool binding natively.

**Potential Improvements:**
*   **Advanced Model Configuration:** Allow for more granular configuration of LLM parameters (e.g., `top_p`, `frequency_penalty`) via environment variables or a configuration file, beyond just `temperature` and `max_tokens`.
*   **Rate Limiting/Retry Policies:** Implement more sophisticated rate limiting and retry mechanisms for LLM API calls, especially for production environments, to handle transient errors and API quotas gracefully.
*   **Streaming Support:** While LangGraph supports streaming, ensuring that the `LLMFactory` and `LLMClient` fully leverage streaming capabilities for faster user feedback could be beneficial.

## 3. Prompt Management and Contextualization

**Technical Choices:**
*   **`PromptManager` (`src/prompts/__init__.py`):** A centralized `PromptManager` loads prompts from YAML files (`src/prompts/system_prompts.yaml`) and supports hot-reloading. This is an excellent design for managing and iterating on prompts without code changes.
*   **YAML for Prompts:** Storing prompts in YAML files makes them human-readable, version-controllable, and easily editable by non-developers.
*   **Dynamic Prompt Composition (`compose_prompt`):** The ability to compose a final system prompt by merging a base prompt with agent-specific prompts and skill instructions is a powerful feature for contextualizing agent behavior.
*   **Agent and Skill Loaders (`src/agents/loader.py`, `src/skills/loader.py`):** These loaders parse markdown files with YAML frontmatter (e.g., `.reactor/agents/*.md`, `.reactor/skills/*.md`) to define agents and skills. This allows for a highly extensible system where new agents and skills can be added by simply creating markdown files.

**Architecture Insights:**
*   **Separation of Concerns:** Prompts are separated from code, allowing prompt engineering to be an independent activity.
*   **Contextual Awareness:** The system dynamically injects `system_info`, `active_agent`, and `active_skills` into the prompts, ensuring the LLM has the most relevant context for its current task and role.
*   **Identity and Authority:** The `thinking_node` explicitly sets the agent's identity and authority (Main Coordinator vs. Sub-Agent) based on the `execution_mode`, which is crucial for controlling delegation behavior and preventing recursive spawning.

**Potential Improvements:**
*   **Prompt Versioning:** For more complex prompt engineering workflows, consider adding explicit versioning to prompts within the YAML files or the `PromptManager` to track changes and roll back if needed.
*   **Prompt Testing Framework:** Develop a framework for testing prompts against various inputs and expected outputs to ensure their effectiveness and prevent regressions.
*   **Prompt Chaining/Templating:** Explore more advanced prompt templating engines (if `str.format` becomes limiting) or a system for chaining smaller, specialized prompts together.

## 4. Tooling and Capabilities

**Technical Choices:**
*   **Comprehensive Toolset (`src/tools`):** Reactor provides a rich set of tools covering shell, file, web, todo, grep/log, and Git operations. This breadth of tools makes the agents highly capable across various domains.
*   **`validate_command_safety`:** The inclusion of a command safety validator is a critical security feature, preventing agents from executing dangerous shell commands.
*   **Specialized Log/JSON Parsers:** Tools like `parse_log_file`, `extract_json_fields`, and `analyze_error_logs` demonstrate a focus on practical utility for developers and system administrators.

**Architecture Insights:**
*   **Modular Tooling:** Tools are organized into logical modules, making them easy to discover, manage, and extend.
*   **Tool Binding in `agent_node`:** The `agent_node` explicitly binds the available tools to the LLM, allowing the LLM to dynamically select and call the appropriate tools based on its reasoning.
*   **Agent Management Tools:** The `agent_tools` (spawn, get_result, list, stop) are essential for enabling the multi-agent orchestration capabilities of Reactor.

**Potential Improvements:**
*   **Tool Discovery and Registration:** For a very large number of tools, a more dynamic tool discovery and registration mechanism (e.g., decorators, plugin system) could simplify management.
*   **Tool Input/Output Schemas:** Explicitly defining input and output schemas for tools (e.g., using Pydantic) could improve LLM's ability to correctly use tools and reduce parsing errors.
*   **User Approval for Sensitive Actions:** For highly sensitive tools (e.g., `execute_shell_command` with certain patterns, `modify_file`), implementing a user approval step before execution could enhance safety and control.

## 5. User Interface: TUI and CLI

**Technical Choices:**
*   **Textual UI (`src/tui`):** The use of `Textual` for the TUI provides a rich, interactive, and terminal-based user experience. This is a great choice for developers who prefer a command-line workflow but desire more interactivity than a plain CLI.
*   **CLI and Headless Modes (`src/main.py`):** The support for CLI and headless modes (via `--cli` and `--prompt` flags) ensures flexibility for different use cases, from interactive development to automated scripting.
*   **Widgets:** The TUI is composed of various widgets (agent UI, todo panel, file tree, code viewer, chat widgets, etc.), indicating a well-structured and extensible UI design.

**Architecture Insights:**
*   **Separation of UI and Logic:** The TUI components are largely separated from the core agent logic, allowing for independent development and potential replacement of the UI layer.
*   **Event-Driven UI:** Textual's event-driven architecture is well-suited for building responsive and interactive terminal applications.

**Potential Improvements:**
*   **More Advanced TUI Features:** Explore features like real-time streaming of tool outputs, more sophisticated code editing capabilities within the TUI, and integrated debugging views.
*   **Web UI Option:** For broader accessibility, consider developing a web-based UI as an alternative to the TUI, perhaps using a framework like Streamlit or a more traditional web framework.

## 6. Overall Code Quality and Best Practices

**Technical Choices:**
*   **Type Hinting:** Extensive use of type hints throughout the codebase improves readability, maintainability, and allows for static analysis.
*   **Docstrings:** Clear docstrings explain the purpose and usage of functions and classes.
*   **Modularity:** The project is well-organized into logical modules (llm, agents, tools, tui, prompts, etc.), promoting code reusability and maintainability.
*   **`dataclasses`:** Used for `AgentConfig` and `SkillConfig`, providing concise and readable data structures.

**Architecture Insights:**
*   **Clean Separation of Concerns:** The project demonstrates a strong adherence to separating different functionalities into distinct modules and components.
*   **Extensibility:** The use of loaders for agents and skills, and the factory for LLMs, makes the framework highly extensible.

**Potential Improvements:**
*   **Unit and Integration Tests:** While `tests/` exists, ensuring comprehensive test coverage for all modules and critical paths would further enhance reliability.
*   **Linting and Formatting:** Consistent application of linting (e.g., Black, Flake8) and formatting tools would ensure code style consistency.
*   **Dependency Management:** The `pyproject.toml` and `poetry.lock` indicate Poetry is used for dependency management, which is a good practice. Ensuring all dependencies are correctly specified and managed is key.

## Conclusion

Reactor is a thoughtfully designed and well-implemented AI agent framework. Its core strength lies in its modular architecture, flexible LLM integration, sophisticated prompt management, and comprehensive tooling, all orchestrated by LangGraph. The TUI provides a powerful interface for developers. Future improvements could focus on enhancing persistence, error recovery, advanced LLM controls, and potentially expanding to a web-based UI for broader reach. The current design provides a solid foundation for building and experimenting with advanced AI agents.