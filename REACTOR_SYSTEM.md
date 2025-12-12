# Reactor System Documentation

## 🔄 Overview

The Reactor System is an **automatic AST analysis layer** that implements the "Simple Actions, Smart Reactions" architecture. It provides intelligent code analysis, validation, and feedback for all file operations performed by AI agents.

## 🎯 Core Principle

**"Simple Actions, Smart Reactions"**

```
🤖 Agent (Simple Operations)          🔄 Reactor (Automatic Analysis)          📁 File System
├─ Reads files              ├─ Parses AST automatically          ├─ Stores files
├─ Writes files             ├─ Validates syntax              ├─ Manages directories  
├─ Edits text               ├─ Checks imports                └─ Handles I/O
└─ Makes simple changes       ├─ Analyzes dependencies
                              ├─ Detects breaking changes
                              ├─ Applies auto-fixes
                              └─ Reports feedback
```

## 🏗️ Architecture

### Components

#### 1. **CodeReactor** (`src/reactor/code_reactor.py`)
Main orchestration class that coordinates all analysis:
- Triggers on file write/modify operations
- Manages analysis pipeline
- Provides unified feedback interface

#### 2. **Validators** (`src/reactor/validators.py`)
Syntax and import validation:
- `SyntaxValidator` - Real-time syntax checking
- `ImportValidator` - Import statement validation
- `CompositeValidator` - Combined validation pipeline

#### 3. **Analyzers** (`src/reactor/analyzers.py`)
Dependency and impact analysis:
- `DependencyAnalyzer` - Maps file relationships
- `ImpactAnalyzer` - Detects breaking changes
- Dependency graph construction and analysis

#### 4. **Auto-Fixes** (`src/reactor/auto_fixes.py`)
Automatic code improvements:
- `AutoFixer` - Fixes missing imports, formatting
- `SmartImportFixer` - Organizes imports by type
- Code formatting and cleanup

#### 5. **Feedback** (`src/reactor/feedback.py`)
Intelligent feedback formatting:
- `FeedbackFormatter` - Structured response formatting
- `ProgressFormatter` - Batch operation tracking
- Multiple verbosity levels (minimal/standard/detailed)

#### 6. **Configuration** (`src/reactor/config.py`)
Flexible configuration system:
- YAML/JSON configuration support
- Feature toggles for all components
- Performance and caching controls

## 🔧 Configuration

### Basic Configuration

```yaml
# reactor_config.yaml
reactor:
  enabled: true
  
  validation:
    syntax_check: true
    import_check: true
    type_check: false
  
  analysis:
    track_dependencies: true
    detect_breaking_changes: true
    analyze_complexity: false
  
  auto_fixes:
    fix_imports: true
    remove_unused_imports: true
    format_code: false
  
  feedback:
    verbosity: "standard"  # minimal, standard, detailed
    include_suggestions: true
    max_suggestions: 5
  
  performance:
    max_file_size_mb: 10
    timeout_seconds: 30
    parallel_processing: true
```

### Advanced Configuration

```yaml
reactor:
  cache:
    enabled: true
    max_size: 1000
    ttl_seconds: 3600
  
  languages:
    python:
      enabled: true
      strict_mode: false
    javascript:
      enabled: true
      strict_mode: false
    java:
      enabled: true
      strict_mode: false
```

## 📊 Feedback Format

### Standard Response Structure

```json
{
  "status": "success|warning|error",
  "file": "path/to/file.py",
  "operation": "write|modify|edit",
  "timestamp": "2025-12-11T23:50:27.127613",
  
  "validation": {
    "syntax": "valid|invalid",
    "imports": "valid|invalid",
    "types": "not_checked|valid|invalid"
  },
  
  "impact": {
    "level": "minimal|low|medium|high",
    "affected_files": ["file1.py", "file2.py"],
    "breaking_changes": [
      {
        "type": "removed_function",
        "name": "get_user",
        "line_number": 45,
        "description": "Function 'get_user' was removed"
      }
    ],
    "api_changes": [],
    "affected_file_count": 3
  },
  
  "auto_fixes": {
    "applied": ["Added missing import: typing.Optional"],
    "failed": [],
    "count": 1
  },
  
  "summary": {
    "validation_status": "passed|failed",
    "impact_level": "minimal",
    "fixes_applied": 1,
    "overall_health": "good|warning|error"
  },
  
  "suggestions": [
    "✓ Code looks good - no issues detected",
    "Update profile.py line 45: replace 'user.get_user()'",
    "Consider adding 'get_user' back for backward compatibility"
  ],
  
  "warnings": [],
  "errors": []
}
```

### Minimal Response (verbosity: minimal)

```json
{
  "status": "success",
  "file": "path/to/file.py",
  "validation": {
    "syntax": "valid"
  }
}
```

### Detailed Response (verbosity: detailed)

```json
{
  "status": "success",
  "file": "path/to/file.py",
  "validation": {
    "syntax": "valid",
    "syntax_details": {
      "parse_time_ms": 15,
      "language": "python",
      "ast_root_available": true
    },
    "import_details": {
      "total_imports": 3,
      "invalid_imports": 0,
      "missing_modules": 0,
      "imports_list": ["os", "sys", "typing"]
    }
  },
  "diagnostics": {
    "validation_details": {...},
    "impact_details": {...},
    "auto_fix_details": {...},
    "configuration": {
      "validation_enabled": true,
      "auto_fixes_enabled": true,
      "dependency_tracking": true
    }
  }
}
```

## 🚨 Error Handling

### Error Categories and Responses

#### 1. **Syntax Errors** (Highest Priority)
```json
{
  "status": "error",
  "validation": {
    "syntax": "invalid",
    "errors": ["Syntax error: unexpected EOF while parsing"],
    "line_number": 15
  },
  "auto_fixes": {
    "applied": [],  // BLOCKED for syntax errors
    "failed": []
  },
  "suggestions": [
    "Fix syntax errors before proceeding"
  ]
}
```

#### 2. **Import Issues** (Medium Priority)
```json
{
  "status": "warning",
  "validation": {
    "syntax": "valid",
    "imports": "invalid"
  },
  "auto_fixes": {
    "applied": ["Added missing import: json"],
    "failed": []
  },
  "warnings": [
    "Missing module: json"
  ],
  "suggestions": [
    "✓ Auto-fixed missing imports"
  ]
}
```

#### 3. **Breaking Changes** (Impact Analysis)
```json
{
  "status": "warning",
  "impact": {
    "level": "high",
    "breaking_changes": [
      {
        "type": "removed_method",
        "name": "get_user",
        "line_number": 23,
        "description": "Method 'get_user' was removed - used in 3 files"
      }
    ],
    "affected_files": ["user_service.py", "api.py", "test_user.py"]
  },
  "suggestions": [
    "Update user_service.py line 45: replace 'user.get_user()'",
    "Consider adding 'get_user' back for backward compatibility",
    "Review affected files for compatibility"
  ]
}
```

## 🔧 Integration with File Tools

### Enhanced File Operations

The reactor system integrates seamlessly with existing file tools:

#### `write_file()` Enhancement
```python
@tool
async def write_file(file_path: str, content: str, mode: str = "create", enable_reactor: bool = True):
    # ... existing implementation ...
    
    # Reactor integration
    if enable_reactor and REACTOR_AVAILABLE:
        reactor = get_global_reactor()
        reactor_feedback = await reactor.on_file_written(file_path, content, mode)
        result["reactor_feedback"] = reactor_feedback
    
    return result
```

#### `modify_file()` Enhancement
```python
@tool
async def modify_file(file_path: str, search_text: str, replace_text: str, 
                   occurrence: str = "all", enable_reactor: bool = True):
    # ... existing implementation ...
    
    # Reactor integration
    if enable_reactor and REACTOR_AVAILABLE:
        reactor = get_global_reactor()
        reactor_feedback = await reactor.on_file_written(file_path, new_content, "modify")
        result["reactor_feedback"] = reactor_feedback
    
    return result
```

#### `edit_file()` Enhancement
```python
@tool
async def edit_file(file_path: str, edits: List[Dict[str, str]], enable_reactor: bool = True):
    # ... existing implementation ...
    
    # Reactor integration
    if enable_reactor and REACTOR_AVAILABLE:
        reactor = get_global_reactor()
        reactor_feedback = await reactor.on_file_written(file_path, content, "edit")
        result["reactor_feedback"] = reactor_feedback
    
    return result
```

## 🎯 Use Cases

### 1. **Development Workflow**
```python
# Agent creates new module
await write_file("src/models/user.py", user_class_code)

# Reactor automatically:
# - Validates Python syntax
# - Checks imports (typing, dataclasses)
# - Analyzes impact on existing code
# - Provides feedback and suggestions
```

### 2. **Refactoring Operations**
```python
# Agent renames method
await modify_file("src/api/user.py", "get_user", "get_user_info")

# Reactor automatically:
# - Detects breaking change
# - Finds all files using old method
# - Reports impact and suggests updates
```

### 3. **Import Management**
```python
# Agent creates file using new library
await write_file("src/utils/data_processor.py", processor_code)

# Reactor automatically:
# - Detects missing imports
# - Adds required import statements
# - Removes unused imports
# - Organizes imports by type
```

### 4. **Quality Assurance**
```python
# Agent makes changes to critical file
await edit_file("src/core/auth.py", auth_edits)

# Reactor automatically:
# - Validates syntax and structure
# - Analyzes complexity and security
# - Checks for potential issues
# - Provides quality metrics
```

## 🚀 Performance Considerations

### Caching Strategy
- **AST Results**: Cached for 1 hour to avoid re-parsing
- **Dependency Graph**: Built incrementally and cached
- **Import Analysis**: Cached at module level
- **Configuration**: Hot-reloadable without restart

### Performance Tuning
```yaml
reactor:
  performance:
    max_file_size_mb: 10        # Skip large files
    timeout_seconds: 30           # Prevent hanging
    parallel_processing: true       # Process multiple files
    batch_size: 50               # Batch operations
  
  cache:
    enabled: true
    max_size: 1000               # Limit memory usage
    ttl_seconds: 3600             # Balance freshness/performance
```

## 🔍 Debugging and Monitoring

### Logging Configuration
```python
import logging

# Enable reactor debugging
logging.getLogger("reactor").setLevel(logging.DEBUG)

# Monitor performance
logging.getLogger("reactor.cache").setLevel(logging.INFO)
```

### Cache Statistics
```python
reactor = get_global_reactor()
stats = reactor.get_cache_stats()

print(f"AST Cache: {stats['ast_cache_stats']}")
print(f"Content Cache: {stats['content_cache_size']}")
print(f"Registered Languages: {stats['registered_languages']}")
```

### Performance Metrics
```python
# Track analysis performance
reactor = get_global_reactor()

# Individual file analysis
result = await reactor.validate_file("example.py")
print(f"Parse time: {result['validation']['syntax_details']['parse_time_ms']}ms")

# Batch operations
project_analysis = await reactor.get_project_analysis(file_list)
print(f"Analyzed {project_analysis['project_stats']['total_files']} files")
```

## 🧪 Testing

### Unit Testing
```python
import pytest
from src.reactor.code_reactor import CodeReactor
from src.reactor.config import ReactorConfig

@pytest.mark.asyncio
async def test_syntax_validation():
    config = ReactorConfig()
    reactor = CodeReactor(config)
    
    # Test valid code
    result = await reactor.on_file_written("test.py", valid_code)
    assert result["status"] == "success"
    assert result["validation"]["syntax"] == "valid"
    
    # Test invalid code
    result = await reactor.on_file_written("invalid.py", invalid_code)
    assert result["status"] == "error"
    assert result["validation"]["syntax"] == "invalid"
```

### Integration Testing
```python
from src.tools.file_tools import write_file

async def test_reactor_integration():
    # Test with reactor enabled
    result = await write_file("test.py", code, enable_reactor=True)
    assert "reactor_feedback" in result
    
    # Test with reactor disabled
    result = await write_file("test.py", code, enable_reactor=False)
    assert "reactor_feedback" not in result
```

### Performance Testing
```python
import time
from src.reactor.code_reactor import CodeReactor

async def benchmark_reactor():
    reactor = CodeReactor()
    
    start_time = time.time()
    for i in range(100):
        await reactor.on_file_written(f"test_{i}.py", test_code)
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 100
    print(f"Average analysis time: {avg_time:.3f}s")
```

## 🔮 Future Enhancements

### Planned Features
- [ ] **Semantic Analysis** - Deeper code understanding
- [ ] **Cross-language Support** - Enhanced JavaScript, Java, Go parsing
- [ ] **Real-time Collaboration** - Multi-user impact analysis
- [ ] **Advanced Refactoring** - Automated safe refactoring suggestions
- [ ] **Test Generation** - Auto-generate unit tests for changes
- [ ] **Documentation Generation** - Auto-update docs for API changes
- [ ] **Performance Profiling** - Code performance analysis
- [ ] **Security Scanning** - Vulnerability detection in code changes

### Research Directions
- **Machine Learning Models** - Train models for code quality prediction
- **Static Analysis Integration** - Incorporate tools like ESLint, mypy
- **IDE Integration** - Real-time feedback in development environments
- **Cloud Processing** - Distributed analysis for large codebases
- **Language Server Protocol** - LSP integration for editor support

## 📚 API Reference

### Core Classes

#### `CodeReactor`
```python
class CodeReactor:
    async def on_file_written(self, file_path: str, content: str, operation: str = "write") -> Dict[str, Any]
    """Main entry point for file analysis"""
    
    async def validate_file(self, file_path: str, content: str) -> Dict[str, Any]
        """Validate file without auto-fixes"""
    
    async def analyze_dependencies(self, file_path: str) -> Dict[str, Any]
        """Analyze file dependencies"""
    
    async def get_project_analysis(self, file_paths: List[str]) -> Dict[str, Any]
        """Analyze entire project"""
```

#### `ReactorConfig`
```python
class ReactorConfig:
    def __init__(self, config_path: Optional[str] = None)
        """Initialize with optional config file"""
    
    def get(self, key_path: str, default=None)
        """Get configuration value with dot notation"""
    
    def set(self, key_path: str, value: Any)
        """Set configuration value with dot notation"""
    
    def should_validate_syntax(self) -> bool
        """Check if syntax validation is enabled"""
    
    def should_auto_fix_imports(self) -> bool
        """Check if auto-fixes are enabled"""
```

### Utility Functions

```python
from src.reactor.code_reactor import get_global_reactor, set_global_reactor

# Get global instance
reactor = get_global_reactor()

# Set custom instance
custom_reactor = CodeReactor(custom_config)
set_global_reactor(custom_reactor)
```

## 🎓 Best Practices

### For Developers
1. **Always enable reactor** in development for better code quality
2. **Configure appropriate verbosity** - `standard` for most use cases
3. **Monitor performance** - Use cache statistics to optimize
4. **Handle errors gracefully** - Reactor provides detailed error information
5. **Test configurations** - Ensure reactor works with your codebase

### For Users
1. **Review reactor feedback** - It provides actionable suggestions
2. **Fix syntax errors first** - Auto-fixes are blocked by syntax issues
3. **Understand impact levels** - High impact requires careful review
4. **Use suggestions** - Reactor provides specific improvement recommendations
5. **Configure appropriately** - Balance validation thoroughness vs performance

### Configuration Guidelines
```yaml
# Recommended for development
reactor:
  validation:
    syntax_check: true
    import_check: true
  analysis:
    track_dependencies: true
    detect_breaking_changes: true
  auto_fixes:
    fix_imports: true
    remove_unused_imports: true
  feedback:
    verbosity: "standard"
    include_suggestions: true

# Recommended for production
reactor:
  validation:
    syntax_check: true
    import_check: true
  analysis:
    track_dependencies: false  # Faster performance
    detect_breaking_changes: true
  auto_fixes:
    fix_imports: false      # Safer in production
    remove_unused_imports: false
  feedback:
    verbosity: "minimal"     # Less noise
    include_suggestions: false
```

---

**The Reactor System transforms simple file operations into intelligent code analysis, providing AI agents with the feedback they need to write better code, faster.** 🚀