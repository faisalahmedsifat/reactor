"""
src/reactor/feedback.py

Feedback formatting and presentation components.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .config import ReactorConfig


class FeedbackFormatter:
    """Formats reactor feedback for agents"""
    
    def __init__(self, config: ReactorConfig):
        self.config = config
    
    def format_feedback(self, 
                      file_path: str,
                      validation_result,
                      impact_result,
                      auto_fix_result,
                      operation: str = "write") -> Dict[str, Any]:
        """
        Format comprehensive feedback for agents
        
        Args:
            file_path: Path to the file that was processed
            validation_result: Result from validation step
            impact_result: Result from impact analysis
            auto_fix_result: Result from auto-fix step
            operation: Type of operation (write, modify, etc.)
            
        Returns:
            Formatted feedback dictionary
        """
        feedback = {
            "status": "success",
            "file": file_path,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            
            "validation": self._format_validation(validation_result),
            "impact": self._format_impact(impact_result),
            "auto_fixes": self._format_auto_fixes(auto_fix_result),
            
            "summary": {},
            "suggestions": [],
            "warnings": [],
            "errors": []
        }
        
        # Build summary
        feedback["summary"] = self._build_summary(validation_result, impact_result, auto_fix_result)
        
        # Generate suggestions
        if self.config.get("feedback.include_suggestions", True):
            feedback["suggestions"] = self._generate_suggestions(
                validation_result, impact_result, auto_fix_result
            )
        
        # Collect warnings and errors
        feedback["warnings"].extend(validation_result.warnings)
        feedback["warnings"].extend(impact_result.warnings)
        feedback["errors"].extend(validation_result.errors)
        feedback["errors"].extend(impact_result.errors)
        
        # Determine overall status
        if feedback["errors"]:
            feedback["status"] = "error"
        elif feedback["warnings"]:
            feedback["status"] = "warning"
        
        return feedback
    
    def _format_validation(self, validation_result) -> Dict[str, Any]:
        """Format validation results"""
        validation = {
            "syntax": "valid" if validation_result.is_valid else "invalid",
            "imports": "valid",
            "types": "not_checked"
        }
        
        # Add syntax details if available
        if hasattr(validation_result, 'details') and validation_result.details:
            syntax_details = validation_result.details.get("syntax", {})
            if syntax_details:
                validation["syntax_details"] = syntax_details
            
            # Add import details
            import_details = validation_result.details.get("imports", {})
            if import_details:
                validation["imports"] = "valid" if validation_result.is_valid else "invalid"
                validation["import_details"] = import_details
        
        # Add line number for syntax errors
        if validation_result.line_number:
            validation["error_line"] = validation_result.line_number
        
        return validation
    
    def _format_impact(self, impact_result) -> Dict[str, Any]:
        """Format impact analysis results"""
        impact = {
            "level": "minimal",
            "affected_files": [],
            "breaking_changes": [],
            "api_changes": []
        }
        
        if hasattr(impact_result, 'details') and impact_result.details:
            details = impact_result.details
            
            impact["level"] = details.get("impact_level", "minimal")
            impact["affected_files"] = details.get("affected_files", [])
            impact["breaking_changes"] = details.get("breaking_changes", [])
            impact["api_changes"] = details.get("api_changes", [])
            impact["affected_file_count"] = details.get("affected_file_count", 0)
        
        return impact
    
    def _format_auto_fixes(self, auto_fix_result) -> Dict[str, Any]:
        """Format auto-fix results"""
        auto_fixes = {
            "applied": [],
            "failed": [],
            "count": 0
        }
        
        if hasattr(auto_fix_result, 'fixes_applied'):
            auto_fixes["applied"] = auto_fix_result.fixes_applied
            auto_fixes["count"] = len(auto_fix_result.fixes_applied)
        
        if hasattr(auto_fix_result, 'fixes_failed'):
            auto_fixes["failed"] = auto_fix_result.fixes_failed
        
        return auto_fixes
    
    def _build_summary(self, validation_result, impact_result, auto_fix_result) -> Dict[str, Any]:
        """Build summary of results"""
        summary = {
            "validation_status": "passed" if validation_result.is_valid else "failed",
            "impact_level": "minimal",
            "fixes_applied": 0,
            "overall_health": "good"
        }
        
        # Add impact level
        if hasattr(impact_result, 'details') and impact_result.details:
            summary["impact_level"] = impact_result.details.get("impact_level", "minimal")
        
        # Add fixes count
        if hasattr(auto_fix_result, 'fixes_applied'):
            summary["fixes_applied"] = len(auto_fix_result.fixes_applied)
        
        # Determine overall health
        if not validation_result.is_valid:
            summary["overall_health"] = "error"
        elif validation_result.warnings or (hasattr(impact_result, 'warnings') and impact_result.warnings):
            summary["overall_health"] = "warning"
        elif summary["impact_level"] in ["high", "medium"]:
            summary["overall_health"] = "caution"
        
        return summary
    
    def _generate_suggestions(self, validation_result, impact_result, auto_fix_result) -> List[str]:
        """Generate actionable suggestions for the agent"""
        suggestions = []
        max_suggestions = self.config.get_max_suggestions()
        
        try:
            # Syntax-related suggestions
            if not validation_result.is_valid:
                if validation_result.errors:
                    suggestions.append("Fix syntax errors before proceeding")
                if validation_result.line_number:
                    suggestions.append(f"Check line {validation_result.line_number} for syntax issues")
            
            # Import-related suggestions
            if hasattr(validation_result, 'details') and validation_result.details:
                import_details = validation_result.details.get("imports", {})
                if import_details.get("invalid_imports", 0) > 0:
                    suggestions.append("Fix invalid import statements")
                if import_details.get("missing_modules", 0) > 0:
                    suggestions.append("Install missing modules or update import paths")
            
            # Impact-related suggestions
            if hasattr(impact_result, 'details') and impact_result.details:
                details = impact_result.details
                
                breaking_changes = details.get("breaking_changes", [])
                if breaking_changes:
                    suggestions.append(f"Review {len(breaking_changes)} breaking change(s)")
                    suggestions.append("Update dependent files that use changed APIs")
                
                affected_files = details.get("affected_files", [])
                if len(affected_files) > 0:
                    suggestions.append(f"Check {len(affected_files)} affected file(s) for compatibility")
                    # List specific files if not too many
                    if len(affected_files) <= 3:
                        for file in affected_files[:2]:
                            suggestions.append(f"Update: {file}")
                
                # API change suggestions
                api_changes = details.get("api_changes", [])
                if api_changes:
                    suggestions.append("Consider updating documentation for API changes")
            
            # Auto-fix suggestions
            if hasattr(auto_fix_result, 'fixes_failed') and auto_fix_result.fixes_failed:
                suggestions.append("Some auto-fixes failed - apply manually")
            
            # General suggestions based on configuration
            if self.config.get_verbosity() == "detailed":
                if validation_result.is_valid and not impact_result.details.get("breaking_changes"):
                    suggestions.append("✓ Code looks good - no issues detected")
            
        except Exception:
            # If suggestion generation fails, provide generic suggestions
            suggestions.append("Review the detailed results for more information")
        
        # Limit suggestions
        return suggestions[:max_suggestions]
    
    def format_minimal_feedback(self, file_path: str, validation_result, impact_result) -> Dict[str, Any]:
        """Format minimal feedback for verbosity level 'minimal'"""
        feedback = {
            "status": "success" if validation_result.is_valid else "error",
            "file": file_path,
            "validation": {
                "syntax": "valid" if validation_result.is_valid else "invalid"
            }
        }
        
        if not validation_result.is_valid:
            feedback["errors"] = validation_result.errors[:1]  # Only first error
        
        if hasattr(impact_result, 'details') and impact_result.details:
            affected_count = impact_result.details.get("affected_file_count", 0)
            if affected_count > 0:
                feedback["impact"] = {
                    "affected_files": affected_count
                }
        
        return feedback
    
    def format_detailed_feedback(self, 
                              file_path: str,
                              validation_result,
                              impact_result,
                              auto_fix_result,
                              operation: str = "write") -> Dict[str, Any]:
        """Format detailed feedback for verbosity level 'detailed'"""
        feedback = self.format_feedback(file_path, validation_result, impact_result, auto_fix_result, operation)
        
        # Add additional details for verbose output
        feedback["diagnostics"] = {
            "validation_details": getattr(validation_result, 'details', {}),
            "impact_details": getattr(impact_result, 'details', {}),
            "auto_fix_details": getattr(auto_fix_result, 'details', {}),
            "configuration": {
                "validation_enabled": self.config.should_validate_syntax(),
                "import_checking": self.config.should_validate_imports(),
                "dependency_tracking": self.config.should_track_dependencies(),
                "auto_fixes_enabled": self.config.should_auto_fix_imports()
            }
        }
        
        return feedback
    
    def format_error_feedback(self, file_path: str, error_message: str, operation: str = "write") -> Dict[str, Any]:
        """Format feedback for when an error occurs during processing"""
        return {
            "status": "error",
            "file": file_path,
            "operation": operation,
            "timestamp": datetime.now().isoformat(),
            "error": error_message,
            "suggestions": [
                "Check file path and permissions",
                "Ensure file content is valid",
                "Try again with a smaller change"
            ]
        }
    
    def format_skipped_feedback(self, file_path: str, reason: str) -> Dict[str, Any]:
        """Format feedback for when a file is skipped"""
        return {
            "status": "skipped",
            "file": file_path,
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
            "message": f"File skipped: {reason}"
        }


class ProgressFormatter:
    """Formats progress feedback for long-running operations"""
    
    def __init__(self, config: ReactorConfig):
        self.config = config
    
    def format_progress(self, operation: str, current: int, total: int, details: Optional[str] = None) -> Dict[str, Any]:
        """Format progress update"""
        percentage = (current / total * 100) if total > 0 else 0
        
        return {
            "type": "progress",
            "operation": operation,
            "current": current,
            "total": total,
            "percentage": round(percentage, 1),
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
    
    def format_batch_summary(self, operation: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format summary of batch operation results"""
        total = len(results)
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "error")
        warnings = sum(1 for r in results if r.get("status") == "warning")
        
        return {
            "type": "batch_summary",
            "operation": operation,
            "total_files": total,
            "successful": successful,
            "failed": failed,
            "warnings": warnings,
            "success_rate": round((successful / total * 100) if total > 0 else 0, 1),
            "timestamp": datetime.now().isoformat(),
            "results": results if self.config.get_verbosity() == "detailed" else []
        }