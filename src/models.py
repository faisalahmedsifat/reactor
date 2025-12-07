from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    MODERATE = "moderate"
    DANGEROUS = "dangerous"


class CommandIntent(BaseModel):
    task_description: str
    category: Literal[
        "file_operation",
        "environment_setup",
        "package_management",
        "git_operation",
        "system_info",
        "process_management",
        "network_operation",
        "analysis",
        "information_gathering",
        "code_review",  # NEW: Analytical categories
        "other",
    ]
    key_entities: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    user_intent_confidence: float = Field(ge=0.0, le=1.0)
    is_analytical: bool = Field(default=False)  # NEW: Flag for routing


class Command(BaseModel):
    cmd: str
    description: str
    reasoning: str
    risk_level: RiskLevel
    reversible: bool
    dependencies: List[int] = Field(default_factory=list)


class ExecutionPlan(BaseModel):
    commands: List[Command]
    overall_strategy: str
    potential_issues: List[str] = Field(default_factory=list)
    estimated_duration_seconds: Optional[int] = None


class ExecutionResult(BaseModel):
    command: str
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    timestamp: datetime = Field(default_factory=datetime.now)
