"""Architecture analyzer for analyzing software architecture and design patterns."""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class ArchitectureIssue:
    """Represents an architecture or design issue."""
    severity: str  # critical, high, medium, low
    category: str  # coupling, cohesion, patterns, structure
    title: str
    description: str
    line_number: int
    file_path: str
    code_snippet: str
    recommendation: str


@dataclass
class ArchitectureMetrics:
    """Architecture quality metrics."""
    coupling_score: float  # 0-100, higher is better (lower coupling)
    cohesion_score: float  # 0-100, higher is better (higher cohesion)
    instability: float  # 0-1, lower is better
    abstractness: float  # 0-1, balance with instability
    distance_from_main: float  # 0-1, closer to 0 is better
    circular_dependencies: int
    god_classes: int
    duplicate_code_smells: int


class ArchitectureAnalyzer:
    """Analyzes software architecture and design patterns."""
    
    def __init__(self):
        self.design_patterns = self._initialize_pattern_detectors()
    
    def _initialize_pattern_detectors(self) -> Dict[str, Dict]:
        """Initialize design pattern detection rules."""
        return {
            "singleton": {
                "keywords": ["getInstance", "instance", "static"],
                "structure": ["private constructor", "static instance"],
                "description": "Singleton pattern detected"
            },
            "factory": {
                "keywords": ["create", "build", "factory", "make"],
                "structure": ["factory method", "abstract factory"],
                "description": "Factory pattern detected"
            },
            "observer": {
                "keywords": ["observer", "listener", "subscribe", "notify"],
                "structure": ["attach", "detach", "notify"],
                "description": "Observer pattern detected"
            },
            "strategy": {
                "keywords": ["strategy", "algorithm", "context"],
                "structure": ["interface", "implementation"],
                "description": "Strategy pattern detected"
            },
            "decorator": {
                "keywords": ["decorator", "wrapper", "enhance"],
                "structure": ["component", "decorator"],
                "description": "Decorator pattern detected"
            }
        }
    
    def analyze(self, ast_result: ASTResult, file_path: str, content: str) -> Dict[str, Any]:
        """Analyze architecture and return issues and metrics."""
        issues = []
        
        # Analyze coupling
        issues.extend(self._analyze_coupling(ast_result, file_path))
        
        # Analyze cohesion
        issues.extend(self._analyze_cohesion(ast_result, file_path))
        
        # Analyze design patterns
        patterns = self._detect_design_patterns(ast_result, file_path)
        
        # Analyze structure
        issues.extend(self._analyze_structure(ast_result, file_path))
        
        # Calculate metrics
        metrics = self._calculate_architecture_metrics(ast_result)
        
        return {
            "issues": issues,
            "patterns": patterns,
            "metrics": metrics,
            "architecture_score": self._calculate_architecture_score(issues, metrics)
        }
    
    def _analyze_coupling(self, ast_result: ASTResult, file_path: str) -> List[ArchitectureIssue]:
        """Analyze coupling issues."""
        issues = []
        
        if not ast_result.classes:
            return issues
        
        # Check for high coupling between classes
        for cls in ast_result.classes:
            # Count dependencies (imports and method calls)
            dependencies = set()
            
            # Check imports for external dependencies
            if ast_result.imports:
                for imp in ast_result.imports:
                    if not self._is_standard_library(imp.module):
                        dependencies.add(imp.module.split('.')[0])
            
            # Check method parameters for coupling
            for method in cls.methods:
                for param in method.parameters:
                    param_type = param.type_hint
                    if self._is_custom_type(param_type, ast_result.classes):
                        dependencies.add(param_type.split('[')[0])  # Remove generics
            
            # High coupling threshold
            if len(dependencies) > 7:
                issues.append(ArchitectureIssue(
                    severity="high",
                    category="coupling",
                    title=f"High coupling in class {cls.name}",
                    description=f"Class {cls.name} has {len(dependencies)} dependencies",
                    line_number=cls.line_number,
                    file_path=file_path,
                    code_snippet=f"class {cls.name}",
                    recommendation="Consider reducing dependencies or using dependency injection"
                ))
            
            # Check for tight coupling (concrete dependencies)
            concrete_deps = [dep for dep in dependencies if not self._is_interface_or_abstract(dep, ast_result.classes)]
            if len(concrete_deps) > len(dependencies) * 0.7:
                issues.append(ArchitectureIssue(
                    severity="medium",
                    category="coupling",
                    title=f"Tight coupling in class {cls.name}",
                    description=f"Class {cls.name} depends mainly on concrete classes",
                    line_number=cls.line_number,
                    file_path=file_path,
                    code_snippet=f"class {cls.name}",
                    recommendation="Depend on abstractions, not concrete classes"
                ))
        
        return issues
    
    def _analyze_cohesion(self, ast_result: ASTResult, file_path: str) -> List[ArchitectureIssue]:
        """Analyze cohesion issues."""
        issues = []
        
        if not ast_result.classes:
            return issues
        
        for cls in ast_result.classes:
            # Check for low cohesion (class doing too many things)
            method_types = set()
            
            for method in cls.methods:
                # Categorize methods by purpose (simplified)
                if any(keyword in method.name.lower() for keyword in ["get", "set", "is", "has"]):
                    method_types.add("accessor")
                elif any(keyword in method.name.lower() for keyword in ["create", "build", "make"]):
                    method_types.add("factory")
                elif any(keyword in method.name.lower() for keyword in ["validate", "check", "verify"]):
                    method_types.add("validation")
                elif any(keyword in method.name.lower() for keyword in ["save", "load", "read", "write"]):
                    method_types.add("persistence")
                elif any(keyword in method.name.lower() for keyword in ["render", "draw", "display"]):
                    method_types.add("ui")
                else:
                    method_types.add("business")
            
            # Low cohesion if class has many different types of responsibilities
            if len(method_types) > 3:
                issues.append(ArchitectureIssue(
                    severity="medium",
                    category="cohesion",
                    title=f"Low cohesion in class {cls.name}",
                    description=f"Class {cls.name} has {len(method_types)} different types of responsibilities",
                    line_number=cls.line_number,
                    file_path=file_path,
                    code_snippet=f"class {cls.name}",
                    recommendation="Consider splitting class into more focused classes"
                ))
            
            # Check for god classes (too many methods and properties)
            total_members = len(cls.methods) + len(cls.properties)
            if total_members > 20:
                issues.append(ArchitectureIssue(
                    severity="high",
                    category="structure",
                    title=f"God class detected: {cls.name}",
                    description=f"Class {cls.name} has {total_members} members, indicating it's doing too much",
                    line_number=cls.line_number,
                    file_path=file_path,
                    code_snippet=f"class {cls.name}",
                    recommendation="Break down the god class into smaller, more focused classes"
                ))
        
        return issues
    
    def _analyze_structure(self, ast_result: ASTResult, file_path: str) -> List[ArchitectureIssue]:
        """Analyze structural issues."""
        issues = []
        
        # Check for circular dependencies (simplified)
        if ast_result.imports and ast_result.classes:
            class_names = {cls.name for cls in ast_result.classes}
            imports_by_class = {}
            
            for imp in ast_result.imports:
                import_name = imp.module.split('.')[-1]
                if import_name in class_names:
                    if import_name not in imports_by_class:
                        imports_by_class[import_name] = []
                    imports_by_class[import_name].append(imp.module)
            
            # Simple circular dependency detection
            for class_name, imports in imports_by_class.items():
                for imp in imports:
                    imp_class = imp.split('.')[-1]
                    if imp_class in imports_by_class and class_name in [i.split('.')[-1] for i in imports_by_class[imp_class]]:
                        issues.append(ArchitectureIssue(
                            severity="high",
                            category="structure",
                            title=f"Circular dependency detected",
                            description=f"Circular dependency between {class_name} and {imp_class}",
                            line_number=1,
                            file_path=file_path,
                            code_snippet=f"import {imp}",
                            recommendation="Break circular dependency by introducing abstraction or reorganizing code"
                        ))
        
        # Check for deep inheritance hierarchies
        if ast_result.classes:
            for cls in ast_result.classes:
                if len(cls.base_classes) > 3:
                    issues.append(ArchitectureIssue(
                        severity="medium",
                        category="structure",
                        title=f"Deep inheritance hierarchy in {cls.name}",
                        description=f"Class {cls.name} has {len(cls.base_classes)} base classes",
                        line_number=cls.line_number,
                        file_path=file_path,
                        code_snippet=f"class {cls.name}",
                        recommendation="Consider composition over inheritance or flatten hierarchy"
                    ))
        
        return issues
    
    def _detect_design_patterns(self, ast_result: ASTResult, file_path: str) -> List[Dict[str, Any]]:
        """Detect design patterns in the code."""
        patterns = []
        
        if not ast_result.classes:
            return patterns
        
        for cls in ast_result.classes:
            for pattern_name, pattern_info in self.design_patterns.items():
                if self._matches_pattern(cls, pattern_info):
                    patterns.append({
                        "name": pattern_name,
                        "class": cls.name,
                        "line": cls.line_number,
                        "description": pattern_info["description"],
                        "confidence": self._calculate_pattern_confidence(cls, pattern_info)
                    })
        
        return patterns
    
    def _matches_pattern(self, cls: Class, pattern_info: Dict) -> bool:
        """Check if a class matches a design pattern."""
        class_text = f"{cls.name} {' '.join(m.name for m in cls.methods)}".lower()
        
        # Check for pattern keywords
        keyword_matches = sum(1 for keyword in pattern_info["keywords"] if keyword in class_text)
        
        # Simple heuristic: if enough keywords match, consider it a pattern
        return keyword_matches >= len(pattern_info["keywords"]) // 2
    
    def _calculate_pattern_confidence(self, cls: Class, pattern_info: Dict) -> float:
        """Calculate confidence score for pattern detection."""
        class_text = f"{cls.name} {' '.join(m.name for m in cls.methods)}".lower()
        
        keyword_matches = sum(1 for keyword in pattern_info["keywords"] if keyword in class_text)
        confidence = keyword_matches / len(pattern_info["keywords"])
        
        return min(confidence, 1.0)
    
    def _calculate_architecture_metrics(self, ast_result: ASTResult) -> ArchitectureMetrics:
        """Calculate architecture quality metrics."""
        if not ast_result.classes:
            return ArchitectureMetrics(
                coupling_score=100.0,
                cohesion_score=100.0,
                instability=0.0,
                abstractness=0.0,
                distance_from_main=0.0,
                circular_dependencies=0,
                god_classes=0,
                duplicate_code_smells=0
            )
        
        # Calculate coupling score (0-100, higher is better)
        total_dependencies = 0
        max_dependencies = 0
        
        for cls in ast_result.classes:
            dependencies = self._count_class_dependencies(cls, ast_result)
            total_dependencies += dependencies
            max_dependencies = max(max_dependencies, dependencies)
        
        avg_dependencies = total_dependencies / len(ast_result.classes)
        coupling_score = max(0, 100 - (avg_dependencies * 10))
        
        # Calculate cohesion score (simplified)
        total_methods = sum(len(cls.methods) for cls in ast_result.classes)
        total_classes = len(ast_result.classes)
        avg_methods_per_class = total_methods / total_classes if total_classes > 0 else 0
        
        # Higher cohesion if classes have focused responsibilities
        cohesion_score = max(0, 100 - (avg_methods_per_class * 2))
        
        # Calculate instability (I = Ce / (Ce + Ca))
        # Ce = efferent coupling (outgoing), Ca = afferent coupling (incoming)
        instability = 0.5  # Simplified - would need full dependency graph
        
        # Calculate abstractness (A = Na / Nc)
        # Na = number of abstract classes, Nc = total number of classes
        abstract_classes = sum(1 for cls in ast_result.classes if cls.is_abstract)
        abstractness = abstract_classes / total_classes if total_classes > 0 else 0
        
        # Distance from main sequence (D = |A + I - 1|)
        distance_from_main = abs(abstractness + instability - 1)
        
        # Count god classes
        god_classes = sum(1 for cls in ast_result.classes 
                        if len(cls.methods) + len(cls.properties) > 20)
        
        return ArchitectureMetrics(
            coupling_score=coupling_score,
            cohesion_score=cohesion_score,
            instability=instability,
            abstractness=abstractness,
            distance_from_main=distance_from_main,
            circular_dependencies=0,  # Would need more complex analysis
            god_classes=god_classes,
            duplicate_code_smells=0  # Would need code similarity analysis
        )
    
    def _calculate_architecture_score(self, issues: List[ArchitectureIssue], metrics: ArchitectureMetrics) -> Dict[str, Any]:
        """Calculate overall architecture score."""
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for issues
        severity_weights = {"critical": 25, "high": 15, "medium": 8, "low": 3}
        for issue in issues:
            score -= severity_weights.get(issue.severity, 1)
        
        # Adjust based on metrics
        score -= (100 - metrics.coupling_score) * 0.2
        score -= (100 - metrics.cohesion_score) * 0.2
        score -= metrics.distance_from_main * 20
        score -= metrics.god_classes * 10
        
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
            "issues_by_category": self._group_issues_by_category(issues),
            "recommendations": self._get_architecture_recommendations(issues, metrics)
        }
    
    def _group_issues_by_category(self, issues: List[ArchitectureIssue]) -> Dict[str, int]:
        """Group issues by category."""
        groups = {"coupling": 0, "cohesion": 0, "patterns": 0, "structure": 0}
        for issue in issues:
            if issue.category in groups:
                groups[issue.category] += 1
        return groups
    
    def _get_architecture_recommendations(self, issues: List[ArchitectureIssue], metrics: ArchitectureMetrics) -> List[str]:
        """Get prioritized architecture recommendations."""
        recommendations = []
        
        # Prioritize critical and high severity issues
        critical_issues = [i for i in issues if i.severity in ["critical", "high"]]
        if critical_issues:
            recommendations.append("Address critical and high severity architecture issues first")
        
        # Coupling recommendations
        if metrics.coupling_score < 70:
            recommendations.append("Reduce coupling by implementing dependency injection and using interfaces")
        
        # Cohesion recommendations
        if metrics.cohesion_score < 70:
            recommendations.append("Improve cohesion by ensuring classes have single responsibilities")
        
        # Structure recommendations
        if metrics.god_classes > 0:
            recommendations.append("Refactor god classes into smaller, more focused classes")
        
        # Pattern recommendations
        if metrics.distance_from_main > 0.3:
            recommendations.append("Balance abstractness and instability for better architecture")
        
        return recommendations
    
    def _count_class_dependencies(self, cls: Class, ast_result: ASTResult) -> int:
        """Count dependencies for a class."""
        dependencies = set()
        
        # Count base classes
        dependencies.update(cls.base_classes)
        
        # Count method parameter types
        for method in cls.methods:
            for param in method.parameters:
                param_type = param.type_hint
                if ast_result.classes and self._is_custom_type(param_type, ast_result.classes):
                    dependencies.add(param_type.split('[')[0])
        
        # Count property types
        for prop in cls.properties:
            prop_type = prop.type_hint
            if ast_result.classes and self._is_custom_type(prop_type, ast_result.classes):
                dependencies.add(prop_type.split('[')[0])
        
        return len(dependencies)
    
    def _is_custom_type(self, type_name: str, classes: List[Class]) -> bool:
        """Check if a type is a custom class (not built-in)."""
        if not type_name or not classes:
            return False
        
        # Remove generics and qualifiers
        clean_type = type_name.split('[')[0].split('<')[0]
        
        # Check against known class names
        class_names = {cls.name for cls in classes}
        return clean_type in class_names
    
    def _is_interface_or_abstract(self, type_name: str, classes: List[Class]) -> bool:
        """Check if a type is an interface or abstract class."""
        for cls in classes:
            if cls.name == type_name and cls.is_abstract:
                return True
        return False
    
    def _is_standard_library(self, import_name: str) -> bool:
        """Check if import is from standard library."""
        std_prefixes = {
            "java.", "javax.", "org.w3c.", "org.xml.", "org.ietf.",
            "std.", "boost.", "System.", "Microsoft.", "dart:",
            "python", "os", "sys", "json", "http", "url", "path"
        }
        
        return any(import_name.startswith(prefix) for prefix in std_prefixes)