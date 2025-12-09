# Creating Agents and Skills for ReACTOR

A comprehensive guide to extending ReACTOR with custom agents and skills.

---

## Table of Contents

1. [Understanding Agents vs Skills](#understanding-agents-vs-skills)
2. [File Structure](#file-structure)
3. [Creating an Agent](#creating-an-agent)
4. [Creating a Skill](#creating-a-skill)
5. [Using the TUI Interface](#using-the-tui-interface)
6. [Manual Creation](#manual-creation)
7. [Best Practices](#best-practices)
8. [Examples](#examples)

---

## Understanding Agents vs Skills

### Agents
**What**: Specialized AI personalities for specific domains (research, code review, data analysis).

**When to use**:
- Task requires specialized knowledge or approach
- Parallel execution is beneficial
- Delegation makes sense (main agent → specialist)

**Examples**: `web-researcher`, `code-reviewer`, `data-analyst`

### Skills
**What**: Reusable knowledge modules that enhance ANY agent's capabilities.

**When to use**:
- Common patterns across tasks (frontend dev, API design)
- Domain-specific best practices
- Tool usage guidelines

**Examples**: `frontend-dev`, `backend-api`, `testing-expert`

---

## File Structure

```
.reactor/
├── agents/
│   ├── web-researcher.md
│   ├── code-reviewer.md
│   └── my-custom-agent.md
└── skills/
    ├── frontend-dev.md
    ├── backend-api.md
    └── my-custom-skill.md
```

**Locations**:
1. **Project-specific**: `.reactor/` in your project root
2. **Global**: `~/.reactor/` in your home directory

---

## Creating an Agent

### 1. Agent File Format

Agents are defined in Markdown files with YAML frontmatter:

```markdown
---
name: agent-id
description: Brief description of what this agent does
version: 1.0
author: Your Name
preferred_tools:
  - tool_name_1
  - tool_name_2
---

# Agent Name

Detailed instructions and personality for this agent.

## Capabilities
- List what this agent is good at
- Specific domain knowledge

## Approach
How this agent should approach tasks.

## Example Workflow
Step-by-step example of agent behavior.
```

### 2. YAML Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ Yes | Unique ID for this agent (lowercase, hyphens) |
| `description` | ✅ Yes | Short summary for agent selection UI |
| `version` | ✅ Yes | Semantic version (e.g., "1.0", "2.1.3") |
| `author` | ❌ No | Your name or organization |
| `preferred_tools` | ❌ No | List of tools this agent should use |

### 3. Agent Body Content

The markdown body defines the agent's **personality and instructions**:

- **First-person perspective**: "You are a..."
- **Clear capabilities**: What can this agent do?
- **Approach guidelines**: How should it think?
- **Output format**: How should it present results?
- **Examples**: Concrete example workflows

---

## Creating a Skill

### 1. Skill File Format

Skills are similar but focus on **knowledge modules**:

```markdown
---
name: skill-id
description: Brief description of this skill
version: 1.0
author: Your Name
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
working_patterns:
  - "**/*.tsx"
  - "**/*.css"
---

# Skill Name

Knowledge and best practices for this domain.

## Guidelines
- Rule 1
- Rule 2

## Code Examples
```language
example code
```

## Common Patterns
How to approach typical scenarios.
```

### 2. YAML Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | ✅ Yes | Unique ID (lowercase, hyphens) |
| `description` | ✅ Yes | Short summary |
| `version` | ✅ Yes | Semantic version |
| `author` | ❌ No | Creator name |
| `allowed_tools` | ❌ No | Tools this skill uses |
| `working_patterns` | ❌ No | File glob patterns (for file-focused skills) |

### 3. Skill Body Content

The markdown body contains **knowledge and guidelines**:

- **Best practices**: Industry standards
- **Code examples**: Template code
- **Patterns**: Common solutions
- **Testing guidelines**: How to verify
- **Performance tips**: Optimization advice

---

## Using the TUI Interface

### Method 1: Slash Commands

**Create new agent**:
```
/new-agent
```
This opens a modal with:
- Name field
- Description field
- Template selection

**Edit existing agent**:
```
/edit-agent web-researcher
```

**View agent details**:
```
/view-agent code-reviewer
```

**Delete agent**:
```
/delete-agent my-old-agent
```

### Method 2: File Browser

1. Navigate to `.reactor/agents/` or `.reactor/skills/`
2. Create new `.md` file
3. Edit in your favorite editor
4. ReACTOR auto-discovers new files on restart

---

## Manual Creation

### Step 1: Create Directory

```bash
# Project-specific
mkdir -p .reactor/agents
mkdir -p .reactor/skills

# Global (all projects)
mkdir -p ~/.reactor/agents
mkdir -p ~/.reactor/skills
```

### Step 2: Create File

**Agent Example** (`.reactor/agents/seo-expert.md`):

```markdown
---
name: seo-expert
description: SEO optimization and content strategy specialist
version: 1.0
author: Dev Team
preferred_tools:
  - web_search
  - read_file_content
  - modify_file
---

# SEO Expert Agent

You are an SEO specialist focused on improving search rankings and content discoverability.

## Capabilities
- Keyword research and analysis
- Meta tag optimization
- Content structure improvement
- Performance analysis
- Competitor analysis

## Approach

When optimizing content:

1. **Audit**: Analyze current state (meta tags, headers, content)
2. **Research**: Use web_search for keyword trends
3. **Optimize**: Improve titles, descriptions, headers
4. **Validate**: Check against SEO best practices

## Guidelines

- **Title Tags**: 50-60 characters, keyword-focused
- **Meta Descriptions**: 150-160 characters, compelling CTA
- **Headers**: H1 (one per page), H2-H6 (hierarchical)
- **Internal Links**: 3-5 per page, relevant anchors
- **Images**: Alt text, optimized file size

## Output Format

Provide structured recommendations:
- Current issues
- Recommended changes
- Expected impact
- Priority level (High/Medium/Low)
```

**Skill Example** (`.reactor/skills/api-design.md`):

```markdown
---
name: api-design
description: RESTful API design best practices
version: 1.0
author: Backend Team
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
working_patterns:
  - "**/routes/**/*.ts"
  - "**/controllers/**/*.ts"
  - "**/api/**/*.ts"
---

# API Design Skill

Best practices for designing RESTful APIs.

## Principles

1. **Resource-Oriented**: URLs represent resources, not actions
2. **HTTP Methods**: Use GET, POST, PUT, DELETE correctly
3. **Status Codes**: Return appropriate HTTP status codes
4. **Versioning**: Include API version in URL
5. **Consistency**: Follow naming conventions

## URL Structure

```
Good:
  GET    /api/v1/users
  GET    /api/v1/users/{id}
  POST   /api/v1/users
  PUT    /api/v1/users/{id}
  DELETE /api/v1/users/{id}

Bad:
  GET /api/v1/getUsers
  POST /api/v1/createUser
```

## Response Format

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "page": 1,
    "total": 100
  }
}
```

## Error Handling

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "field": "email"
  }
}
```

## Status Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth |
| 404 | Not Found | Resource doesn't exist |
| 500 | Server Error | Unexpected error |
```

### Step 3: Reload ReACTOR

```bash
# Restart the application to discover new agents/skills
poetry run python src/main.py
```

Or use slash command:
```
/agents    # List all available agents
/skills    # List all available skills
```

---

## Best Practices

### For Agents

✅ **DO**:
- Use clear, descriptive names (`web-researcher`, not `researcher1`)
- Define specific capabilities and limitations
- Provide example workflows
- Include preferred tools list
- Use first-person perspective ("You are...")

❌ **DON'T**:
- Make agents too broad (use skills instead)
- Duplicate existing agent functionality
- Forget version numbers
- Use generic descriptions

### For Skills

✅ **DO**:
- Focus on reusable knowledge
- Include code examples
- Specify allowed tools
- Define file patterns for file-focused skills
- Keep content concise and scannable

❌ **DON'T**:
- Make skills agent-specific
- Include implementation details (that's for tools)
- Overlap with other skills
- Forget to update version when changing

### General Guidelines

1. **Version Control**: Commit agents/skills to Git
2. **Documentation**: Keep examples updated
3. **Testing**: Verify agents work before sharing
4. **Naming**: Use kebab-case: `my-agent-name`
5. **Descriptions**: Make them searchable and clear

---

## Examples

### Example 1: Data Analyst Agent

```markdown
---
name: data-analyst
description: Specialized in data analysis and visualization
version: 1.0
author: Analytics Team
preferred_tools:
  - read_file_content
  - execute_shell_command
  - web_search
---

# Data Analyst Agent

You are a data analyst specializing in extracting insights from structured data.

## Capabilities
- CSV/JSON data parsing
- Statistical analysis
- Trend identification
- Data visualization recommendations
- Report generation

## Approach

1. **Understand**: Clarify data structure and analysis goals
2. **Explore**: Load and examine the data
3. **Analyze**: Apply statistical methods
4. **Visualize**: Recommend charts/graphs
5. **Report**: Summarize findings with actionable insights

## Tools

- Use `read_file_content` for CSV/JSON files
- Use `execute_shell_command` for pandas/numpy operations
- Use `web_search` for statistical method references

## Output Format

```
# Analysis Report

## Dataset Overview
- Rows: X
- Columns: Y
- Time Range: ...

## Key Findings
1. Finding 1 (with numbers)
2. Finding 2 (with context)

## Recommendations
- Action 1
- Action 2

## Visualizations
- Chart type 1: [description]
- Chart type 2: [description]
```
```

### Example 2: Testing Skill

```markdown
---
name: testing-expert
description: Comprehensive testing best practices
version: 1.0
author: QA Team
allowed_tools:
  - read_file_content
  - write_file
  - modify_file
  - execute_shell_command
working_patterns:
  - "**/*.test.ts"
  - "**/*.test.tsx"
  - "**/*.spec.ts"
---

# Testing Expert Skill

Guidelines for writing effective tests.

## Testing Pyramid

```
     ╱╲
    ╱E2E╲       Few (slow, expensive)
   ╱─────╲
  ╱ Integ ╲     Some (moderate)
 ╱─────────╲
╱   Unit    ╲   Many (fast, cheap)
─────────────
```

## Unit Testing

### Principles
- Test one thing at a time
- Fast execution (\u003c100ms per test)
- No external dependencies
- Clear test names

### Structure (AAA Pattern)
```typescript
test('should calculate total price with tax', () => {
  // Arrange
  const price = 100;
  const taxRate = 0.1;
  
  // Act
  const result = calculateTotal(price, taxRate);
  
  // Assert
  expect(result).toBe(110);
});
```

## Integration Testing

```typescript
test('should create user and return ID', async () => {
  const userData = { name: 'John', email: 'john@test.com' };
  
  const userId = await userService.create(userData);
  const user = await userService.getById(userId);
  
  expect(user.name).toBe('John');
  expect(user.email).toBe('john@test.com');
});
```

## Mocking

### When to Mock
- External APIs
- Database calls
- File system operations
- Time-dependent code

### How to Mock
```typescript
jest.mock('./api');

test('fetches user data', async () => {
  api.getUser.mockResolvedValue({ id: 1, name: 'John' });
  
  const result = await fetchUserProfile(1);
  
  expect(result.name).toBe('John');
});
```

## Coverage Goals
- Unit Tests: 80%+ coverage
- Integration Tests: Critical paths
- E2E Tests: Happy paths + error scenarios
```

---

## Quick Reference

### Agent Creation Checklist

- [ ] Create `.reactor/agents/agent-name.md`
- [ ] Add YAML frontmatter (name, description, version)
- [ ] Define capabilities
- [ ] Specify approach/workflow
- [ ] List preferred tools
- [ ] Include examples
- [ ] Test with `/view-agent agent-name`
- [ ] Use with `spawn_agent` tool

### Skill Creation Checklist

- [ ] Create `.reactor/skills/skill-name.md`
- [ ] Add YAML frontmatter (name, description, version)
- [ ] Document guidelines/best practices
- [ ] Include code examples
- [ ] Specify allowed tools (if applicable)
- [ ] Define file patterns (if applicable)
- [ ] Test by loading with an agent
- [ ] Verify knowledge is applied

---

## Troubleshooting

**Agent not appearing in `/agents` list?**
- Check YAML frontmatter syntax
- Ensure file is in `.reactor/agents/`
- Restart ReACTOR
- Check file has `.md` extension

**Skill not being loaded?**
- Verify YAML frontmatter
- Check file location (`.reactor/skills/`)
- Ensure `name` field matches
- Restart application

**Agent not behaving as expected?**
- Review prompt clarity
- Check preferred_tools list
- Test with specific task
- Refine instructions iteratively

---

## Next Steps

1. **Start Simple**: Create a basic agent for a specific task
2. **Test**: Use it with `spawn_agent` tool
3. **Iterate**: Refine based on performance
4. **Share**: Commit to your project repo
5. **Expand**: Create complementary skills

For more examples, check `.reactor/agents/` and `.reactor/skills/` in your installation.
