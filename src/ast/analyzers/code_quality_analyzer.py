"""Code quality analyzer for measuring maintainability and quality metrics."""

import re
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class QualityIssue:
    """Represents a code quality issue."""
    severity: str  # critical, high, medium, low
    category: str  # complexity, maintainability, style, duplication
    title: str
    description: str
    line_number: int
    file_path: str
    code_snippet: str
    recommendation: str


@dataclass
class QualityMetrics:
    """Code quality metrics for a file or project."""
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: float
    technical_debt_ratio: float
    duplication_percentage: float
    test_coverage: float
    lines_of_code: int
    comment_ratio: float


class CodeQualityAnalyzer:
    """Analyzes code for quality issues and metrics."""
    
    def __init__(self):
        self.complexity_thresholds = {
            "low": 5,
            "moderate": 10,
            "high": 15,
            "very_high": 20
        }
    
    def analyze(self, ast_result: ASTResult, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze code quality and return issues and metrics."""
        issues = []
        
        # Analyze complexity
        if ast_result.functions:
            issues.extend(self._analyze_complexity(ast_result.functions, file_path))
        
        # Analyze maintainability
        if ast_result.functions:
            issues.extend(self._analyze_maintainability(ast_result.functions, file_path))
        
        # Analyze code style
        issues.extend(self._analyze_style(content, file_path))
        
        # Analyze naming conventions
        if ast_result.functions and ast_result.classes:
            issues.extend(self._analyze_naming(ast_result.functions, ast_result.classes, file_path))
        
        # Calculate metrics
        metrics = self._calculate_metrics(ast_result, content)
        
        return {
            "issues": issues,
            "metrics": metrics,
            "quality_score": self._calculate_quality_score(issues, metrics)
        }
    
    def _analyze_complexity(self, functions: List[Function], file_path: str) -> List[QualityIssue]:
        """Analyze cyclomatic and cognitive complexity."""
        issues = []
        
        for func in functions:
            # Simplified complexity calculation
            complexity = self._calculate_cyclomatic_complexity(func)
            
            if complexity > self.complexity_thresholds["very_high"]:
                severity = "critical"
            elif complexity > self.complexity_thresholds["high"]:
                severity = "high"
            elif complexity > self.complexity_thresholds["moderate"]:
                severity = "medium"
            elif complexity > self.complexity_thresholds["low"]:
                severity = "low"
            else:
                continue
            
            issues.append(QualityIssue(
                severity=severity,
                category="complexity",
                title=f"High cyclomatic complexity in {func.name}",
                description=f"Function {func.name} has cyclomatic complexity of {complexity}",
                line_number=func.line_number,
                file_path=file_path,
                code_snippet=f"def {func.name}(...)",
                recommendation=f"Refactor function to reduce complexity below {self.complexity_thresholds['moderate']}"
            ))
        
        return issues
    
    def _analyze_maintainability(self, functions: List[Function], file_path: str) -> List[QualityIssue]:
        """Analyze maintainability issues."""
        issues = []
        
        for func in functions:
            # Check function length
            if func.line_number > 50:  # Simplified - would need actual function body
                issues.append(QualityIssue(
                    severity="medium",
                    category="maintainability",
                    title=f"Long function: {func.name}",
                    description=f"Function {func.name} is too long and hard to maintain",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Break down function into smaller, focused functions"
                ))
            
            # Check parameter count
            if len(func.parameters) > 7:
                issues.append(QualityIssue(
                    severity="medium",
                    category="maintainability",
                    title=f"Too many parameters in {func.name}",
                    description=f"Function {func.name} has {len(func.parameters)} parameters",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Consider using a parameter object or reducing parameters"
                ))
            
            # Check for deep nesting (simplified)
            if func.complexity_score > 10:
                issues.append(QualityIssue(
                    severity="medium",
                    category="maintainability",
                    title=f"Deep nesting in {func.name}",
                    description=f"Function {func.name} appears to have deeply nested code",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Reduce nesting by extracting nested logic into separate functions"
                ))
        
        return issues
    
    def _analyze_style(self, content: str, file_path: str) -> List[QualityIssue]:
        """Analyze code style issues."""
        issues = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # Check for long lines
            if len(line) > 120:
                issues.append(QualityIssue(
                    severity="low",
                    category="style",
                    title="Line too long",
                    description=f"Line {line_num} exceeds 120 characters ({len(line)} chars)",
                    line_number=line_num,
                    file_path=file_path,
                    code_snippet=line[:50] + "...",
                    recommendation="Break long lines into multiple lines"
                ))
            
            # Check for trailing whitespace
            if line.endswith(' ') and line:
                issues.append(QualityIssue(
                    severity="low",
                    category="style",
                    title="Trailing whitespace",
                    description=f"Line {line_num} has trailing whitespace",
                    line_number=line_num,
                    file_path=file_path,
                    code_snippet=line,
                    recommendation="Remove trailing whitespace"
                ))
            
            # Check for TODO comments without issue reference
            if re.search(r'//\s*TODO(?!\s*#\d+)', line) or re.search(r'#\s*TODO(?!\s*#\d+)', line):
                issues.append(QualityIssue(
                    severity="low",
                    category="style",
                    title="TODO without issue reference",
                    description=f"Line {line_num} has TODO without issue reference",
                    line_number=line_num,
                    file_path=file_path,
                    code_snippet=line,
                    recommendation="Add issue reference to TODO (e.g., TODO #123)"
                ))
        
        return issues
    
    def _analyze_naming(self, functions: List[Function], classes: List[Class], file_path: str) -> List[QualityIssue]:
        """Analyze naming convention issues."""
        issues = []
        
        # Analyze function names
        for func in functions:
            if not self._is_valid_function_name(func.name):
                issues.append(QualityIssue(
                    severity="medium",
                    category="style",
                    title=f"Invalid function name: {func.name}",
                    description=f"Function name '{func.name}' doesn't follow naming conventions",
                    line_number=func.line_number,
                    file_path=file_path,
                    code_snippet=f"def {func.name}(...)",
                    recommendation="Use snake_case for function names"
                ))
        
        # Analyze class names
        for cls in classes:
            if not self._is_valid_class_name(cls.name):
                issues.append(QualityIssue(
                    severity="medium",
                    category="style",
                    title=f"Invalid class name: {cls.name}",
                    description=f"Class name '{cls.name}' doesn't follow naming conventions",
                    line_number=cls.line_number,
                    file_path=file_path,
                    code_snippet=f"class {cls.name}",
                    recommendation="Use PascalCase for class names"
                ))
        
        return issues
    
    def _calculate_cyclomatic_complexity(self, func: Function) -> int:
        """Calculate cyclomatic complexity for a function."""
        # Simplified calculation - in real implementation would analyze function body
        base_complexity = 1
        
        # Add complexity based on parameters (simplified heuristic)
        param_complexity = min(len(func.parameters), 5)
        
        # Add complexity based on existing complexity score
        return base_complexity + param_complexity + func.complexity_score
    
    def _calculate_metrics(self, ast_result: ASTResult, content: str) -> QualityMetrics:
        """Calculate various code quality metrics."""
        lines = content.split('\n')
        
        # Lines of code (non-empty, non-comment lines)
        loc = sum(1 for line in lines if line.strip() and not line.strip().startswith(('//', '#', '/*', '*')))
        
        # Comment ratio
        comment_lines = sum(1 for line in lines if line.strip().startswith(('//', '#', '/*', '*')))
        comment_ratio = comment_lines / len(lines) if lines else 0
        
        # Average cyclomatic complexity
        if ast_result.functions:
            avg_complexity = sum(self._calculate_cyclomatic_complexity(f) for f in ast_result.functions) / len(ast_result.functions)
        else:
            avg_complexity = 1.0
        
        # Maintainability index (simplified calculation)
        maintainability_index = max(0, 171 - 5.2 * math.log(avg_complexity + 1) - 0.23 * avg_complexity - 16.2 * math.log(loc + 1))
        
        # Technical debt ratio (simplified)
        if ast_result.functions:
            debt_issues = sum(1 for f in ast_result.functions if self._calculate_cyclomatic_complexity(f) > 10)
            technical_debt_ratio = debt_issues / len(ast_result.functions)
        else:
            technical_debt_ratio = 0.0
        
        # Duplication percentage (simplified - would need more sophisticated analysis)
        duplication_percentage = 0.0
        
        # Test coverage (placeholder - would need test analysis)
        test_coverage = 0.0
        
        return QualityMetrics(
            cyclomatic_complexity=int(avg_complexity),
            cognitive_complexity=int(avg_complexity),  # Simplified
            maintainability_index=maintainability_index,
            technical_debt_ratio=technical_debt_ratio,
            duplication_percentage=duplication_percentage,
            test_coverage=test_coverage,
            lines_of_code=loc,
            comment_ratio=comment_ratio
        )
    
    def _calculate_quality_score(self, issues: List[QualityIssue], metrics: QualityMetrics) -> Dict[str, Any]:
        """Calculate overall quality score."""
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for issues
        severity_weights = {"critical": 20, "high": 10, "medium": 5, "low": 1}
        for issue in issues:
            score -= severity_weights.get(issue.severity, 1)
        
        # Adjust based on metrics
        if metrics.cyclomatic_complexity > 15:
            score -= 10
        elif metrics.cyclomatic_complexity > 10:
            score -= 5
        
        if metrics.maintainability_index < 50:
            score -= 15
        elif metrics.maintainability_index < 70:
            score -= 8
        
        if metrics.technical_debt_ratio > 0.3:
            score -= 10
        elif metrics.technical_debt_ratio > 0.1:
            score -= 5
        
        # Ensure score is within bounds
        score = max(0, min(100, score))
        
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
            "score": round(score, 1),
            "grade": grade,
            "issues_by_severity": self._group_issues_by_severity(issues),
            "recommendations": self._get_recommendations(issues, metrics)
        }
    
    def _group_issues_by_severity(self, issues: List[QualityIssue]) -> Dict[str, int]:
        """Group issues by severity."""
        groups = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            if issue.severity in groups:
                groups[issue.severity] += 1
        return groups
    
    def _get_recommendations(self, issues: List[QualityIssue], metrics: QualityMetrics) -> List[str]:
        """Get prioritized recommendations based on issues and metrics."""
        recommendations = []
        
        # Prioritize critical and high severity issues
        critical_issues = [i for i in issues if i.severity in ["critical", "high"]]
        if critical_issues:
            recommendations.append("Address critical and high severity issues first")
        
        # Complexity recommendations
        if metrics.cyclomatic_complexity > 15:
            recommendations.append("Reduce function complexity through refactoring")
        
        # Maintainability recommendations
        if metrics.maintainability_index < 70:
            recommendations.append("Improve code maintainability by reducing complexity and improving documentation")
        
        # Technical debt recommendations
        if metrics.technical_debt_ratio > 0.1:
            recommendations.append("Focus on reducing technical debt by refactoring complex functions")
        
        # Style recommendations
        style_issues = [i for i in issues if i.category == "style"]
        if len(style_issues) > 5:
            recommendations.append("Consider using a code formatter to address style issues")
        
        return recommendations
    
    def _is_valid_function_name(self, name: str) -> bool:
        """Check if function name follows conventions (simplified)."""
        # Python convention: snake_case
        if re.match(r'^[a-z_][a-z0-9_]*$', name):
            return True
        # JavaScript convention: camelCase
        if re.match(r'^[a-z][a-zA-Z0-9]*$', name):
            return True
        return False
    
    def _is_valid_class_name(self, name: str) -> bool:
        """Check if class name follows conventions (simplified)."""
        # PascalCase convention
        return re.match(r'^[A-Z][a-zA-Z0-9]*$', name) is not None