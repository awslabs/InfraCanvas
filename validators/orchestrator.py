"""
Validation orchestrator for coordinating validation workflow.
"""
import logging
import tempfile
import shutil
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Dict, List, Optional
from datetime import datetime

from validators.base import (
    BaseValidator,
    ValidationConfig,
    ValidationReport,
    ValidationResult
)
from validators.report import ReportGenerator

logger = logging.getLogger(__name__)


def extract_code_from_markdown(code: str, iac_format: str) -> str:
    """
    Extract code from markdown code blocks.
    
    For CloudFormation (YAML), extracts content between ```yaml and ```.
    For other formats, returns the code as-is if no code blocks are found.
    
    Args:
        code: The raw code that may contain markdown formatting
        iac_format: The IaC format (cloudformation, terraform, cdk)
        
    Returns:
        Extracted code without markdown formatting
    """
    # Determine the code block language identifier based on format
    if iac_format.lower() == 'cloudformation':
        # Look for ```yaml code blocks
        pattern = r'```yaml\s*\n(.*?)\n```'
    elif iac_format.lower() == 'terraform':
        # Look for ```hcl or ```terraform code blocks
        pattern = r'```(?:hcl|terraform)\s*\n(.*?)\n```'
    elif iac_format.lower() == 'cdk':
        # Look for ```python, ```typescript, or ```java code blocks
        pattern = r'```(?:python|typescript|java)\s*\n(.*?)\n```'
    else:
        # Default: look for any code block
        pattern = r'```\w*\s*\n(.*?)\n```'
    
    # Search for code blocks
    matches = re.findall(pattern, code, re.DOTALL | re.IGNORECASE)
    
    if matches:
        # If multiple code blocks found, concatenate them with newlines
        extracted_code = '\n\n'.join(matches)
        logger.info(f"Extracted {len(matches)} code block(s) from markdown for {iac_format} validation")
        return extracted_code.strip()
    
    # If no code blocks found, return original code
    logger.debug(f"No markdown code blocks found for {iac_format}, using original code")
    return code


class ValidationOrchestrator:
    """Coordinates validation workflow and manages validator lifecycle."""
    
    def __init__(self, config: ValidationConfig):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config: ValidationConfig with settings for validation
        """
        self.config = config
        self.validators: Dict[str, List[BaseValidator]] = {}
        self.report_generator = ReportGenerator()
        self._initialize_validators()
    
    def _initialize_validators(self):
        """Initialize format-specific validators using Amazon Q Developer."""
        from validators.q_developer import QDeveloperValidator
        
        # Use Q Developer for all IaC formats
        # Q Developer provides comprehensive validation including:
        # - Syntax and structure analysis
        # - Security scanning
        # - Best practices validation
        # - Deployment readiness checks
        
        cloudformation_validators = [
            QDeveloperValidator(
                iac_format='cloudformation',
                region=self.config.aws_region
            )
        ]
        
        terraform_validators = [
            QDeveloperValidator(
                iac_format='terraform',
                region=self.config.aws_region
            )
        ]
        
        cdk_validators = [
            QDeveloperValidator(
                iac_format='cdk',
                region=self.config.aws_region
            )
        ]
        
        self.validators = {
            'cloudformation': cloudformation_validators,
            'terraform': terraform_validators,
            'cdk': cdk_validators
        }
    
    def _get_validators_for_format(self, iac_format: str) -> List[BaseValidator]:
        """
        Return appropriate validators based on IaC format.
        
        Args:
            iac_format: The IaC format (cloudformation, terraform, cdk)
            
        Returns:
            List of validators for the specified format
        """
        format_lower = iac_format.lower()
        validators = self.validators.get(format_lower, [])
        
        # Filter to only available validators
        available_validators = [v for v in validators if v.is_available()]
        
        if not available_validators:
            logger.warning(f"No validators available for format: {iac_format}")
        
        return available_validators
    
    def validate(self, code: str, iac_format: str) -> ValidationReport:
        """
        Execute all validation checks and aggregate results.
        
        Args:
            code: The IaC code to validate (may contain markdown formatting)
            iac_format: The format of the code (cloudformation, terraform, cdk)
            
        Returns:
            ValidationReport with comprehensive validation results
        """
        start_time = datetime.now()
        
        # Extract code from markdown code blocks if present
        extracted_code = extract_code_from_markdown(code, iac_format)
        
        # Get validators for this format
        validators = self._get_validators_for_format(iac_format)
        
        if not validators:
            # Return fallback report if no validators available
            return self._create_fallback_report(
                iac_format, 
                extracted_code, 
                "No validators available for this format"
            )
        
        # Create temporary directory for validation
        temp_dir = tempfile.mkdtemp(prefix='infracanvas_validation_')
        
        try:
            # Run validators in parallel with extracted code
            results = self._run_validators_parallel(validators, extracted_code, temp_dir)
            
            # Calculate total execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Generate comprehensive report
            report = self.report_generator.generate_report(
                results=results,
                iac_format=iac_format,
                code_length=len(extracted_code),
                execution_time_total=execution_time
            )
            
            return report
            
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Failed to clean up temporary directory: {e}")
    
    def _run_validators_parallel(
        self, 
        validators: List[BaseValidator], 
        code: str, 
        temp_dir: str
    ) -> List[ValidationResult]:
        """
        Execute validators concurrently.
        
        Args:
            validators: List of validators to execute
            code: The IaC code to validate
            temp_dir: Temporary directory for validator execution
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        timeout = self.config.validation_timeout_seconds
        
        with ThreadPoolExecutor(max_workers=len(validators)) as executor:
            # Submit all validators
            future_to_validator = {
                executor.submit(self._run_single_validator, v, code, temp_dir): v
                for v in validators
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_validator, timeout=timeout):
                validator = future_to_validator[future]
                try:
                    result = future.result(timeout=60)  # Per-validator timeout
                    results.append(result)
                except TimeoutError:
                    logger.error(f"Validator {validator.get_name()} timed out")
                    # Create error result for timeout
                    results.append(self._create_timeout_result(validator))
                except Exception as e:
                    logger.error(f"Validator {validator.get_name()} failed: {e}")
                    # Create error result for failure
                    results.append(self._create_error_result(validator, str(e)))
        
        return results
    
    def _run_single_validator(
        self, 
        validator: BaseValidator, 
        code: str, 
        temp_dir: str
    ) -> ValidationResult:
        """
        Run a single validator with error handling.
        
        Args:
            validator: The validator to execute
            code: The IaC code to validate
            temp_dir: Temporary directory for validator execution
            
        Returns:
            ValidationResult from the validator
        """
        try:
            return validator.validate(code, temp_dir)
        except Exception as e:
            logger.error(f"Error running validator {validator.get_name()}: {e}")
            raise
    
    def _create_timeout_result(self, validator: BaseValidator) -> ValidationResult:
        """Create a ValidationResult for a timed-out validator."""
        from validators.base import ValidationIssue, Severity
        
        return ValidationResult(
            validator_name=validator.get_name(),
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.HIGH,
                    category="deployment",
                    message=f"Validator {validator.get_name()} timed out",
                    remediation="Check validator configuration and system resources"
                )
            ],
            execution_time=self.config.validation_timeout_seconds,
            metadata={"error": "timeout"}
        )
    
    def _create_error_result(
        self, 
        validator: BaseValidator, 
        error_message: str
    ) -> ValidationResult:
        """Create a ValidationResult for a failed validator."""
        from validators.base import ValidationIssue, Severity
        
        return ValidationResult(
            validator_name=validator.get_name(),
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.HIGH,
                    category="deployment",
                    message=f"Validator {validator.get_name()} failed: {error_message}",
                    remediation="Check validator installation and configuration"
                )
            ],
            execution_time=0.0,
            metadata={"error": error_message}
        )
    
    def _create_fallback_report(
        self, 
        iac_format: str, 
        code: str, 
        message: str
    ) -> ValidationReport:
        """Create a fallback report when no validators are available."""
        from validators.base import DeploymentReadinessScore, Severity
        
        return ValidationReport(
            iac_format=iac_format,
            code_length=len(code),
            timestamp=datetime.now(),
            results=[],
            readiness_score=DeploymentReadinessScore(
                overall_score=0.0,
                syntax_score=0.0,
                security_score=0.0,
                best_practices_score=0.0,
                deployment_score=0.0,
                status="not_ready",
                blocking_issues=[]
            ),
            total_issues=0,
            issues_by_severity={},
            issues_by_category={},
            execution_time_total=0.0
        )
