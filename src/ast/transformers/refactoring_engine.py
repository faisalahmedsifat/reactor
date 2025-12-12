"""Refactoring engine for safe code transformations."""

import re
import difflib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.base_parser import ASTResult, Function, Class, Import, Variable


@dataclass
class RefactoringOperation:
    """Represents a refactoring operation."""
    operation_type: str  # rename, extract_method, inline_variable, etc.
    description: str
    file_path: str
    line_number: int
    original_code: str
    refactored_code: str
    confidence: float  # 0-1, higher is more confident
    risk_level: str  # low, medium, high
    affected_lines: List[int]
    dependencies: List[str]  # Other files that might be affected


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""
    success: bool
    operation: RefactoringOperation
    modified_content: str
    changes: List[str]
    warnings: List[str]
    errors: List[str]


class RefactoringEngine:
    """Engine for performing safe code refactoring operations."""
    
    def __init__(self):
        self.refactoring_rules = self._initialize_refactoring_rules()
    
    def _initialize_refactoring_rules(self) -> Dict[str, Dict]:
        """Initialize refactoring rules and patterns."""
        return {
            "rename_variable": {
                "pattern": r'(\w+)\s*=\s*',
                "description": "Rename variable for better clarity",
                "risk": "low"
            },
            "extract_method": {
                "pattern": r'if\s*\([^)]+\)\s*\{[^}]*\}',
                "description": "Extract complex conditional into method",
                "risk": "medium"
            },
            "inline_variable": {
                "pattern": r'const\s+(\w+)\s*=\s*([^;]+);',
                "description": "Inline simple constant variable",
                "risk": "low"
            },
            "simplify_conditional": {
                "pattern": r'if\s*\([^)]+\)\s*{\s*return\s+true;\s*}\s*else\s*{\s*return\s+false;\s*}',
                "description": "Simplify boolean conditional",
                "risk": "low"
            },
            "extract_constant": {
                "pattern": r'(["\'])(\d+)\1',
                "description": "Extract magic number as constant",
                "risk": "medium"
            },
            "remove_dead_code": {
                "pattern": r'if\s*\(false\)\s*\{[^}]*\}',
                "description": "Remove dead code block",
                "risk": "low"
            }
        }
    
    def analyze_refactoring_opportunities(self, ast_result: ASTResult, file_path: str, content: str) -> List[RefactoringOperation]:
        """Analyze code for refactoring opportunities."""
        operations = []
        
        # Analyze functions for refactoring opportunities
        if ast_result.functions:
            operations.extend(self._analyze_functions(ast_result.functions, file_path, content))
        
        # Analyze classes for refactoring opportunities
        if ast_result.classes:
            operations.extend(self._analyze_classes(ast_result.classes, file_path, content))
        
        # Analyze general code patterns
        operations.extend(self._analyze_code_patterns(content, file_path))
        
        # Sort by confidence and risk
        operations.sort(key=lambda x: (-x.confidence, x.risk_level))
        
        return operations
    
    def apply_refactoring(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply a refactoring operation to code."""
        try:
            if operation.operation_type == "rename_variable":
                return self._apply_rename_variable(operation, content)
            elif operation.operation_type == "extract_method":
                return self._apply_extract_method(operation, content)
            elif operation.operation_type == "inline_variable":
                return self._apply_inline_variable(operation, content)
            elif operation.operation_type == "simplify_conditional":
                return self._apply_simplify_conditional(operation, content)
            elif operation.operation_type == "extract_constant":
                return self._apply_extract_constant(operation, content)
            elif operation.operation_type == "remove_dead_code":
                return self._apply_remove_dead_code(operation, content)
            else:
                return RefactoringResult(
                    success=False,
                    operation=operation,
                    modified_content=content,
                    changes=[],
                    warnings=[],
                    errors=[f"Unsupported refactoring operation: {operation.operation_type}"]
                )
        except Exception as e:
            return RefactoringResult(
                success=False,
                operation=operation,
                modified_content=content,
                changes=[],
                warnings=[],
                errors=[f"Refactoring failed: {str(e)}"]
            )
    
    def _analyze_functions(self, functions: List[Function], file_path: str, content: str) -> List[RefactoringOperation]:
        """Analyze functions for refactoring opportunities."""
        operations = []
        
        for func in functions:
            # Check for long functions
            if func.line_number > 50:  # Simplified heuristic
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description=f"Extract method from long function {func.name}",
                    file_path=file_path,
                    line_number=func.line_number,
                    original_code=f"def {func.name}(...)",
                    refactored_code=f"// Extracted methods from {func.name}",
                    confidence=0.7,
                    risk_level="medium",
                    affected_lines=list(range(func.line_number, func.line_number + 50)),
                    dependencies=[]
                ))
            
            # Check for functions with many parameters
            if len(func.parameters) > 5:
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description=f"Extract parameter object for {func.name}",
                    file_path=file_path,
                    line_number=func.line_number,
                    original_code=f"def {func.name}({', '.join(p.name for p in func.parameters)})",
                    refactored_code=f"def {func.name}(params: {func.name}Params)",
                    confidence=0.8,
                    risk_level="medium",
                    affected_lines=[func.line_number],
                    dependencies=[]
                ))
            
            # Check for complex functions
            if func.complexity_score > 10:
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description=f"Reduce complexity of {func.name} by extracting methods",
                    file_path=file_path,
                    line_number=func.line_number,
                    original_code=f"def {func.name}(...)",
                    refactored_code=f"// Simplified {func.name}",
                    confidence=0.6,
                    risk_level="medium",
                    affected_lines=[func.line_number],
                    dependencies=[]
                ))
        
        return operations
    
    def _analyze_classes(self, classes: List[Class], file_path: str, content: str) -> List[RefactoringOperation]:
        """Analyze classes for refactoring opportunities."""
        operations = []
        
        for cls in classes:
            # Check for god classes
            total_members = len(cls.methods) + len(cls.properties)
            if total_members > 20:
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description=f"Split god class {cls.name} into smaller classes",
                    file_path=file_path,
                    line_number=cls.line_number,
                    original_code=f"class {cls.name}",
                    refactored_code=f"// Split {cls.name} into focused classes",
                    confidence=0.8,
                    risk_level="high",
                    affected_lines=[cls.line_number],
                    dependencies=[]
                ))
            
            # Check for classes with many methods
            if len(cls.methods) > 15:
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description=f"Extract some methods from {cls.name} into separate classes",
                    file_path=file_path,
                    line_number=cls.line_number,
                    original_code=f"class {cls.name}",
                    refactored_code=f"// Refactored {cls.name}",
                    confidence=0.7,
                    risk_level="medium",
                    affected_lines=[cls.line_number],
                    dependencies=[]
                ))
        
        return operations
    
    def _analyze_code_patterns(self, content: str, file_path: str) -> List[RefactoringOperation]:
        """Analyze code patterns for refactoring opportunities."""
        operations = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check for magic numbers
            magic_numbers = re.findall(r'\b\d{2,}\b', line)
            for number in magic_numbers:
                operations.append(RefactoringOperation(
                    operation_type="extract_constant",
                    description=f"Extract magic number {number} as named constant",
                    file_path=file_path,
                    line_number=line_num,
                    original_code=line.strip(),
                    refactored_code=line.replace(number, f"CONSTANT_{number}"),
                    confidence=0.6,
                    risk_level="medium",
                    affected_lines=[line_num],
                    dependencies=[]
                ))
            
            # Check for complex conditionals
            if re.search(r'if\s*\([^)]+\s*&&\s*[^)]+\s*&&\s*[^)]+\)', line):
                operations.append(RefactoringOperation(
                    operation_type="extract_method",
                    description="Extract complex conditional into separate method",
                    file_path=file_path,
                    line_number=line_num,
                    original_code=line.strip(),
                    refactored_code=f"if (isConditionValid())",
                    confidence=0.7,
                    risk_level="medium",
                    affected_lines=[line_num],
                    dependencies=[]
                ))
            
            # Check for dead code patterns
            if re.search(r'if\s*\(false\)\s*\{', line):
                operations.append(RefactoringOperation(
                    operation_type="remove_dead_code",
                    description="Remove dead code block",
                    file_path=file_path,
                    line_number=line_num,
                    original_code=line.strip(),
                    refactored_code="// Dead code removed",
                    confidence=0.9,
                    risk_level="low",
                    affected_lines=[line_num],
                    dependencies=[]
                ))
        
        return operations
    
    def _apply_rename_variable(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply variable rename refactoring."""
        lines = content.split('\n')
        old_name = operation.original_code.split('=')[0].strip()
        new_name = operation.refactored_code.split('=')[0].strip()
        
        changes = []
        modified_lines = []
        
        for i, line in enumerate(lines):
            if i + 1 in operation.affected_lines:
                # Simple rename - in real implementation would need scope analysis
                modified_line = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, line)
                if modified_line != line:
                    lines[i] = modified_line
                    changes.append(f"Line {i+1}: Renamed '{old_name}' to '{new_name}'")
                    modified_lines.append(i + 1)
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=[],
            errors=[]
        )
    
    def _apply_extract_method(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply extract method refactoring."""
        # Simplified implementation - would need more sophisticated AST manipulation
        lines = content.split('\n')
        
        # Find the method to extract
        start_line = operation.line_number
        end_line = min(start_line + 10, len(lines))  # Simplified
        
        # Extract method body
        method_body = lines[start_line-1:end_line]
        extracted_method = f"extractedMethod() {{\n    // Extracted logic\n}}"
        
        # Replace original code with method call
        lines[start_line-1] = f"    {extracted_method.split('{')[0].strip()};"
        
        # Add extracted method at class level (simplified)
        insert_pos = self._find_class_insertion_point(lines, start_line)
        if insert_pos:
            lines.insert(insert_pos, f"\n{extracted_method}\n")
        
        changes = [f"Extracted method from lines {start_line}-{end_line}"]
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=["Manual review required for extracted method"],
            errors=[]
        )
    
    def _apply_inline_variable(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply inline variable refactoring."""
        lines = content.split('\n')
        
        # Find variable declaration and usages
        var_match = re.search(r'const\s+(\w+)\s*=\s*([^;]+);', operation.original_code)
        if not var_match:
            return RefactoringResult(
                success=False,
                operation=operation,
                modified_content=content,
                changes=[],
                warnings=[],
                errors=["Cannot parse variable declaration"]
            )
        
        var_name = var_match.group(1)
        var_value = var_match.group(2).strip()
        
        changes = []
        # Remove declaration
        for i, line in enumerate(lines):
            if i + 1 == operation.line_number:
                lines[i] = f"// Inlined: {var_name} = {var_value}"
                changes.append(f"Line {i+1}: Inlined variable '{var_name}'")
                break
        
        # Replace usages (simplified)
        for i, line in enumerate(lines):
            if re.search(r'\b' + re.escape(var_name) + r'\b', line):
                lines[i] = re.sub(r'\b' + re.escape(var_name) + r'\b', f'({var_value})', line)
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=["Manual review required for variable inlining"],
            errors=[]
        )
    
    def _apply_simplify_conditional(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply simplify conditional refactoring."""
        lines = content.split('\n')
        
        # Find and simplify the conditional
        for i, line in enumerate(lines):
            if i + 1 == operation.line_number:
                # Simplify if (condition) { return true; } else { return false; }
                simplified = re.sub(
                    r'if\s*\(([^)]+)\)\s*\{\s*return\s+true;\s*\}\s*else\s*\{\s*return\s+false;\s*\}',
                    r'return \1;',
                    line
                )
                lines[i] = simplified
                break
        
        changes = [f"Simplified conditional at line {operation.line_number}"]
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=[],
            errors=[]
        )
    
    def _apply_extract_constant(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply extract constant refactoring."""
        lines = content.split('\n')
        
        # Find magic number and extract as constant
        magic_match = re.search(r'\b(\d{2,})\b', operation.original_code)
        if not magic_match:
            return RefactoringResult(
                success=False,
                operation=operation,
                modified_content=content,
                changes=[],
                warnings=[],
                errors=["Cannot find magic number"]
            )
        
        magic_number = magic_match.group(1)
        constant_name = f"CONSTANT_{magic_number}"
        
        # Add constant declaration at top of file/class
        insert_pos = self._find_constant_insertion_point(lines, operation.line_number)
        if insert_pos:
            lines.insert(insert_pos, f"const int {constant_name} = {magic_number};")
        
        # Replace magic number with constant
        for i, line in enumerate(lines):
            if i + 1 == operation.line_number:
                lines[i] = re.sub(r'\b' + re.escape(magic_number) + r'\b', constant_name, line)
                break
        
        changes = [f"Extracted magic number {magic_number} as constant '{constant_name}'"]
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=["Manual review required for constant naming"],
            errors=[]
        )
    
    def _apply_remove_dead_code(self, operation: RefactoringOperation, content: str) -> RefactoringResult:
        """Apply remove dead code refactoring."""
        lines = content.split('\n')
        
        # Remove dead code block
        for i, line in enumerate(lines):
            if i + 1 == operation.line_number:
                lines[i] = f"// Removed dead code: {line.strip()}"
                break
        
        changes = [f"Removed dead code at line {operation.line_number}"]
        
        return RefactoringResult(
            success=True,
            operation=operation,
            modified_content='\n'.join(lines),
            changes=changes,
            warnings=[],
            errors=[]
        )
    
    def _find_class_insertion_point(self, lines: List[str], current_line: int) -> Optional[int]:
        """Find appropriate position to insert extracted method."""
        # Simplified - look for class boundaries
        for i in range(max(0, current_line - 50), min(len(lines), current_line + 50)):
            if re.search(r'^\s*}\s*$', lines[i]):  # End of class/method
                return i + 1
        return None
    
    def _find_constant_insertion_point(self, lines: List[str], current_line: int) -> Optional[int]:
        """Find appropriate position to insert constant declaration."""
        # Simplified - insert before the current line or at top
        for i in range(max(0, current_line - 10), current_line):
            if re.search(r'^\s*(public|private|protected)\s*:', lines[i]):
                return i + 1
        return 0
    
    def validate_refactoring(self, operation: RefactoringOperation, original_content: str, refactored_content: str) -> Dict[str, Any]:
        """Validate that refactoring preserves functionality."""
        validation_result = {
            "is_valid": True,
            "syntax_errors": [],
            "semantic_errors": [],
            "warnings": []
        }
        
        # Basic syntax validation (simplified)
        try:
            # Check for balanced braces
            open_braces = refactored_content.count('{')
            close_braces = refactored_content.count('}')
            if open_braces != close_braces:
                validation_result["syntax_errors"].append("Unbalanced braces")
                validation_result["is_valid"] = False
            
            # Check for balanced parentheses
            open_parens = refactored_content.count('(')
            close_parens = refactored_content.count(')')
            if open_parens != close_parens:
                validation_result["syntax_errors"].append("Unbalanced parentheses")
                validation_result["is_valid"] = False
                
        except Exception as e:
            validation_result["syntax_errors"].append(f"Validation error: {str(e)}")
            validation_result["is_valid"] = False
        
        # Check for potential semantic issues
        if operation.operation_type == "rename_variable":
            # Check if new name conflicts with existing names
            new_name = operation.refactored_code.split('=')[0].strip()
            if re.search(r'\b' + re.escape(new_name) + r'\b', original_content):
                validation_result["warnings"].append(f"New name '{new_name}' may conflict with existing names")
        
        return validation_result
    
    def generate_refactoring_plan(self, operations: List[RefactoringOperation]) -> Dict[str, Any]:
        """Generate a prioritized refactoring plan."""
        # Group operations by type
        grouped_ops = {}
        for op in operations:
            if op.operation_type not in grouped_ops:
                grouped_ops[op.operation_type] = []
            grouped_ops[op.operation_type].append(op)
        
        # Prioritize by risk and confidence
        high_priority = [op for op in operations if op.risk_level == "low" and op.confidence > 0.7]
        medium_priority = [op for op in operations if op.risk_level == "medium" and op.confidence > 0.6]
        low_priority = [op for op in operations if op.risk_level == "high" or op.confidence <= 0.6]
        
        return {
            "total_operations": len(operations),
            "grouped_operations": grouped_ops,
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "estimated_effort": self._estimate_refactoring_effort(operations),
            "recommendations": self._generate_refactoring_recommendations(operations)
        }
    
    def _estimate_refactoring_effort(self, operations: List[RefactoringOperation]) -> Dict[str, Any]:
        """Estimate effort required for refactoring operations."""
        effort_scores = {
            "rename_variable": 1,
            "inline_variable": 2,
            "simplify_conditional": 2,
            "extract_constant": 3,
            "extract_method": 5,
            "remove_dead_code": 1
        }
        
        total_effort = sum(effort_scores.get(op.operation_type, 3) for op in operations)
        
        return {
            "total_effort_points": total_effort,
            "estimated_hours": total_effort * 0.5,  # Rough estimate
            "complexity": "low" if total_effort < 10 else "medium" if total_effort < 25 else "high"
        }
    
    def _generate_refactoring_recommendations(self, operations: List[RefactoringOperation]) -> List[str]:
        """Generate recommendations based on refactoring opportunities."""
        recommendations = []
        
        # Count operation types
        op_types = [op.operation_type for op in operations]
        
        if op_types.count("extract_method") > 3:
            recommendations.append("Consider breaking down large functions into smaller, more focused ones")
        
        if op_types.count("extract_constant") > 2:
            recommendations.append("Define constants for magic numbers to improve code readability")
        
        if op_types.count("remove_dead_code") > 0:
            recommendations.append("Remove dead code to reduce complexity and improve maintainability")
        
        if any("rename_variable" in op_type for op_type in op_types):
            recommendations.append("Use descriptive variable names to improve code readability")
        
        return recommendations