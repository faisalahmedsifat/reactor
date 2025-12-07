# Contributing to Reactor

First off, thank you for considering contributing to Reactor! 🎉 It's people like you that make Reactor such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct (see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)).

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples** (code snippets, commands, etc.)
- **Describe the behavior you observed** and what you expected
- **Include screenshots/GIFs** if relevant
- **Provide environment details**: OS, Python version, installation method

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful** to most Reactor users
- **Provide examples** of how it would work

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** if you've added code that should be tested
4. **Update documentation** if you've changed APIs or added features
5. **Ensure tests pass**: `poetry run pytest`
6. **Format your code**: `poetry run black src/`
7. **Submit a pull request**

#### Pull Request Guidelines

- Keep PRs focused on a single feature or fix
- Write clear commit messages
- Update the CHANGELOG.md
- Reference related issues in the PR description
- Be responsive to feedback and questions

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/reactor.git
cd reactor

# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Add your API keys to .env

# Run tests
poetry run pytest

# Format code
poetry run black src/

# Run the application
poetry run python main.py
```

## Project Structure

```
reactor/
├── src/
│   ├── graph.py          # LangGraph workflow
│   ├── nodes/            # Agent nodes
│   ├── tools/            # LangChain tools
│   ├── tui/              # Terminal UI
│   └── llm/              # LLM integration
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Coding Standards

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Keep functions focused and single-purpose
- Use meaningful variable names
- Add comments for complex logic

## Testing

- Write unit tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage for new code
- Use pytest for all tests

## Documentation

- Update README.md if you change functionality
- Add docstrings to new functions/classes
- Update type hints
- Create examples for new features

## Git Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and pull requests after the first line

Example:
```
Add grep tool with regex support

- Implement grep_advanced with context lines
- Add tests for regex patterns
- Update documentation

Fixes #123
```

## Community

- Join discussions in GitHub Discussions
- Be respectful and constructive
- Help others when you can
- Share your use cases and feedback

## Questions?

Feel free to open an issue with the `question` label or start a discussion in GitHub Discussions.

---

Thank you for contributing! 🚀
