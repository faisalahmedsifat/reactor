"""Security analyzer for detecting potential vulnerabilities and security issues."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class SecurityIssue:
    """Represents a security vulnerability or issue."""
    severity: str  # critical, high, medium, low
    category: str  # injection, xss, crypto, auth, etc.
    title: str
    description: str
    line_number: int
    file_path: str
    code_snippet: str
    recommendation: str
    cwe_id: Optional[str] = None


class SecurityAnalyzer:
    """Analyzes code for security vulnerabilities and issues."""
    
    def __init__(self):
        self.security_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize security vulnerability patterns for different languages."""
        return {
            "python": [
                {
                    "pattern": r'eval\s*\(',
                    "severity": "critical",
                    "category": "code_injection",
                    "title": "Use of eval() function",
                    "description": "eval() can execute arbitrary code and is dangerous",
                    "recommendation": "Use ast.literal_eval() or avoid dynamic code execution",
                    "cwe": "CWE-94"
                },
                {
                    "pattern": r'exec\s*\(',
                    "severity": "critical", 
                    "category": "code_injection",
                    "title": "Use of exec() function",
                    "description": "exec() can execute arbitrary code and is dangerous",
                    "recommendation": "Avoid dynamic code execution or use safer alternatives",
                    "cwe": "CWE-94"
                },
                {
                    "pattern": r'shell=True',
                    "severity": "high",
                    "category": "command_injection",
                    "title": "Shell injection vulnerability",
                    "description": "shell=True in subprocess can lead to command injection",
                    "recommendation": "Avoid shell=True or validate input thoroughly",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r'pickle\.loads?\s*\(',
                    "severity": "high",
                    "category": "deserialization",
                    "title": "Unsafe pickle deserialization",
                    "description": "pickle can execute arbitrary code during deserialization",
                    "recommendation": "Use JSON or safer serialization formats",
                    "cwe": "CWE-502"
                },
                {
                    "pattern": r'md5\s*\(',
                    "severity": "medium",
                    "category": "weak_crypto",
                    "title": "Weak cryptographic hash (MD5)",
                    "description": "MD5 is cryptographically weak and collision-prone",
                    "recommendation": "Use SHA-256 or stronger hash functions",
                    "cwe": "CWE-327"
                },
                {
                    "pattern": r'sha1\s*\(',
                    "severity": "medium",
                    "category": "weak_crypto", 
                    "title": "Weak cryptographic hash (SHA1)",
                    "description": "SHA1 is cryptographically weak and collision-prone",
                    "recommendation": "Use SHA-256 or stronger hash functions",
                    "cwe": "CWE-327"
                }
            ],
            "javascript": [
                {
                    "pattern": r'eval\s*\(',
                    "severity": "critical",
                    "category": "code_injection",
                    "title": "Use of eval() function",
                    "description": "eval() can execute arbitrary code and is dangerous",
                    "recommendation": "Use JSON.parse() or avoid dynamic code execution",
                    "cwe": "CWE-94"
                },
                {
                    "pattern": r'innerHTML\s*=',
                    "severity": "high",
                    "category": "xss",
                    "title": "Potential XSS vulnerability",
                    "description": "innerHTML can lead to cross-site scripting attacks",
                    "recommendation": "Use textContent or sanitize input",
                    "cwe": "CWE-79"
                },
                {
                    "pattern": r'document\.write\s*\(',
                    "severity": "high",
                    "category": "xss",
                    "title": "Potential XSS vulnerability",
                    "description": "document.write can lead to cross-site scripting attacks",
                    "recommendation": "Use DOM manipulation methods or sanitize input",
                    "cwe": "CWE-79"
                }
            ],
            "java": [
                {
                    "pattern": r'Runtime\.getRuntime\(\)\.exec',
                    "severity": "high",
                    "category": "command_injection",
                    "title": "Command execution vulnerability",
                    "description": "Runtime.exec can lead to command injection",
                    "recommendation": "Validate and sanitize all input",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r'Class\.forName\s*\(',
                    "severity": "medium",
                    "category": "reflection",
                    "title": "Unsafe reflection usage",
                    "description": "Reflection can bypass security controls",
                    "recommendation": "Validate class names and use allowlists",
                    "cwe": "CWE-470"
                }
            ],
            "cpp": [
                {
                    "pattern": r'strcpy\s*\(',
                    "severity": "high",
                    "category": "buffer_overflow",
                    "title": "Unsafe string copy function",
                    "description": "strcpy is vulnerable to buffer overflow attacks",
                    "recommendation": "Use strncpy or std::string",
                    "cwe": "CWE-120"
                },
                {
                    "pattern": r'strcat\s*\(',
                    "severity": "high",
                    "category": "buffer_overflow",
                    "title": "Unsafe string concatenation function",
                    "description": "strcat is vulnerable to buffer overflow attacks",
                    "recommendation": "Use strncat or std::string",
                    "cwe": "CWE-120"
                },
                {
                    "pattern": r'gets\s*\(',
                    "severity": "critical",
                    "category": "buffer_overflow",
                    "title": "Extremely dangerous input function",
                    "description": "gets has no bounds checking and is always unsafe",
                    "recommendation": "Use fgets or std::getline",
                    "cwe": "CWE-120"
                }
            ],
            "csharp": [
                {
                    "pattern": r'Process\.Start\s*\(',
                    "severity": "high",
                    "category": "command_injection",
                    "title": "Command execution vulnerability",
                    "description": "Process.Start can lead to command injection",
                    "recommendation": "Validate and sanitize all input",
                    "cwe": "CWE-78"
                },
                {
                    "pattern": r'Assembly\.LoadFrom\s*\(',
                    "severity": "medium",
                    "category": "deserialization",
                    "title": "Unsafe assembly loading",
                    "description": "Loading assemblies from untrusted sources is dangerous",
                    "recommendation": "Validate assembly sources and signatures",
                    "cwe": "CWE-502"
                }
            ]
        }
    
    def analyze(self, ast_result: ASTResult, file_path: str, content: str) -> List[SecurityIssue]:
        """Analyze AST result for security vulnerabilities."""
        issues = []
        
        # Get language-specific patterns
        language = ast_result.language.value.lower() if hasattr(ast_result.language, 'value') else str(ast_result.language).lower()
        patterns = self.security_patterns.get(language, [])
        
        # Analyze content for security patterns
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern_info in patterns:
                if re.search(pattern_info["pattern"], line, re.IGNORECASE):
                    issue = SecurityIssue(
                        severity=pattern_info["severity"],
                        category=pattern_info["category"],
                        title=pattern_info["title"],
                        description=pattern_info["description"],
                        line_number=line_num,
                        file_path=file_path,
                        code_snippet=line.strip(),
                        recommendation=pattern_info["recommendation"],
                        cwe_id=pattern_info.get("cwe")
                    )
                    issues.append(issue)
        
        # Analyze imports for risky dependencies
        if ast_result.imports:
            issues.extend(self._analyze_imports(ast_result.imports, file_path))
        
        # Analyze functions for security issues
        if ast_result.functions:
            issues.extend(self._analyze_functions(ast_result.functions, file_path))
        
        return issues
    
    def _analyze_imports(self, imports: List[Import], file_path: str) -> List[SecurityIssue]:
        """Analyze imports for risky dependencies."""
        issues = []
        
        risky_imports = {
            "python": {
                "subprocess": {"severity": "medium", "category": "command_injection"},
                "os": {"severity": "low", "category": "command_injection"},
                "pickle": {"severity": "high", "category": "deserialization"},
                "ctypes": {"severity": "medium", "category": "code_injection"}
            },
            "javascript": {
                "child_process": {"severity": "medium", "category": "command_injection"},
                "vm": {"severity": "high", "category": "code_injection"}
            }
        }
        
        for import_stmt in imports:
            module_name = import_stmt.module.split('.')[0]
            # Check against risky imports (simplified)
            if module_name in ["subprocess", "os", "pickle", "child_process", "vm"]:
                issues.append(SecurityIssue(
                    severity="medium",
                    category="risky_import",
                    title=f"Potentially risky import: {module_name}",
                    description=f"Import {module_name} can be dangerous if used improperly",
                    line_number=import_stmt.line_number,
                    file_path=file_path,
                    code_snippet=import_stmt.module,
                    recommendation="Ensure proper input validation and sanitization"
                ))
        
        return issues
    
    def _analyze_functions(self, functions: List[Function], file_path: str) -> List[SecurityIssue]:
        """Analyze functions for security issues."""
        issues = []
        
        for func in functions:
            # Check for functions with no input validation
            if len(func.parameters) > 0 and not self._has_input_validation(func):
                issues.append(SecurityIssue(
                    severity="low",
                    category="input_validation",
                    title=f"Missing input validation in {func.name}",
                    description=f"Function {func.name} accepts parameters but may not validate input",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Add input validation for all external inputs"
                ))
            
            # Check for hardcoded credentials
            if self._has_hardcoded_credentials(func):
                issues.append(SecurityIssue(
                    severity="high",
                    category="hardcoded_credentials",
                    title=f"Potential hardcoded credentials in {func.name}",
                    description=f"Function {func.name} may contain hardcoded credentials",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Use environment variables or secure credential storage"
                ))
        
        return issues
    
    def _has_input_validation(self, func: Function) -> bool:
        """Check if function appears to have input validation."""
        # Simplified check - in real implementation would analyze function body
        validation_keywords = ["validate", "sanitize", "check", "verify", "clean"]
        return any(keyword in func.name.lower() for keyword in validation_keywords)
    
    def _has_hardcoded_credentials(self, func: Function) -> bool:
        """Check if function might have hardcoded credentials."""
        # Simplified check - in real implementation would analyze function body
        credential_keywords = ["password", "secret", "key", "token", "auth"]
        return any(keyword in func.name.lower() for keyword in credential_keywords)
    
    def get_security_score(self, issues: List[SecurityIssue]) -> Dict[str, Any]:
        """Calculate overall security score based on found issues."""
        if not issues:
            return {"score": 100, "grade": "A", "issues_by_severity": {}}
        
        severity_weights = {"critical": 10, "high": 5, "medium": 2, "low": 1}
        issues_by_severity = {}
        total_weight = 0
        
        for issue in issues:
            severity = issue.severity
            issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
            total_weight += severity_weights.get(severity, 1)
        
        # Calculate score (0-100, lower is worse)
        score = max(0, 100 - total_weight * 2)
        
        # Determine grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": score,
            "grade": grade,
            "issues_by_severity": issues_by_severity,
            "total_issues": len(issues)
        }