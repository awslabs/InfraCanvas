"""
Base classes and data models for IaC validation system.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict


class Severity(Enum):
    """Severity levels for validation issues."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a single validation issue found in IaC code."""
    severity: Severity
    category: str  # "syntax", "security", "best_practice", "deployment"
    message: str
    line_number: Optional[int] = None
    resource: Optional[str] = None
    remediation: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Results from a single validator execution."""
    validator_name: str
    passed: bool
    issues: List[ValidationIssue]
    execution_time: float
    metadata: Optional[Dict] = None


@dataclass
class DeploymentReadinessScore:
    """Deployment readiness scoring breakdown."""
    overall_score: float  # 0-100
    syntax_score: float
    security_score: float
    best_practices_score: float
    deployment_score: float
    status: str  # "ready", "ready_with_warnings", "not_ready"
    blocking_issues: List[ValidationIssue] = field(default_factory=list)


@dataclass
class ValidationReport:
    """Comprehensive validation report aggregating all results."""
    iac_format: str
    code_length: int
    timestamp: datetime
    results: List[ValidationResult]
    readiness_score: DeploymentReadinessScore
    total_issues: int
    issues_by_severity: Dict[Severity, int]
    issues_by_category: Dict[str, int]
    execution_time_total: float
    
    def get_blocking_issues(self) -> List[ValidationIssue]:
        """Return issues that block deployment."""
        return self.readiness_score.blocking_issues
    
    def get_issues_by_severity(self, severity: Severity) -> List[ValidationIssue]:
        """Filter issues by severity level."""
        all_issues = []
        for result in self.results:
            all_issues.extend(result.issues)
        return [issue for issue in all_issues if issue.severity == severity]
    
    def is_deployment_ready(self) -> bool:
        """Check if code is ready for deployment."""
        return self.readiness_score.status == "ready"


@dataclass
class ValidationConfig:
    """Configuration options for validation system."""
    enable_syntax_validation: bool = True
    enable_security_scanning: bool = True
    enable_best_practices: bool = True
    enable_dry_run: bool = True
    
    # Security thresholds
    max_critical_security_issues: int = 0
    max_high_security_issues: int = 3
    
    # Timeout settings
    validation_timeout_seconds: int = 120
    
    # Tool-specific settings
    checkov_skip_checks: Optional[List[str]] = None
    cfn_lint_ignore_checks: Optional[List[str]] = None
    
    # AWS settings for dry-run validation
    aws_region: str = "us-east-1"
    use_aws_validation: bool = True


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    @abstractmethod
    def validate(self, code: str, temp_dir: str) -> ValidationResult:
        """
        Execute validation and return results.
        
        Args:
            code: The IaC code to validate
            temp_dir: Temporary directory for validator execution
            
        Returns:
            ValidationResult containing issues found
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if validator tool is installed and accessible.
        
        Returns:
            True if validator is available, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Return validator name for reporting.
        
        Returns:
            Human-readable validator name
        """
        pass
