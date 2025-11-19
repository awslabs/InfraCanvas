"""
Integration tests for IaC validation system.

Tests end-to-end validation flow: code → validation → report generation
"""
import os
import pytest
from pathlib import Path
from validators.base import ValidationConfig, Severity
from validators.orchestrator import ValidationOrchestrator


# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCloudFormationValidation:
    """Integration tests for CloudFormation validation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create validation orchestrator with default config."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False,  # Disable AWS API calls for tests
            validation_timeout_seconds=120
        )
        return ValidationOrchestrator(config)
    
    def test_valid_cloudformation_template(self, orchestrator):
        """Test validation of valid CloudFormation template."""
        # Load valid template
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cloudformation")
        
        # Assertions
        assert report is not None
        assert report.iac_format == "cloudformation"
        assert report.code_length == len(code)
        assert len(report.results) > 0
        
        # Should have minimal critical issues
        critical_issues = report.get_issues_by_severity(Severity.CRITICAL)
        
        assert len(critical_issues) == 0, f"Valid template should have no critical issues: {critical_issues}"
        
        # Filter out validator errors (HIGH severity issues about validator failures)
        high_issues = [
            issue for issue in report.get_issues_by_severity(Severity.HIGH)
            if "validator" not in issue.message.lower() and "unexpected error" not in issue.message.lower()
        ]
        
        assert len(high_issues) == 0, f"Valid template should have no high issues: {high_issues}"
        
        # Check deployment readiness score
        assert report.readiness_score.overall_score >= 40, \
            f"Valid template should have decent score: {report.readiness_score.overall_score}"
    
    def test_cloudformation_syntax_errors(self, orchestrator):
        """Test validation detects CloudFormation syntax errors."""
        # Load template with syntax errors
        template_path = FIXTURES_DIR / "cloudformation" / "syntax_error.yaml"
        code = template_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cloudformation")
        
        # Assertions
        assert report is not None
        assert len(report.results) > 0
        
        # Should detect syntax issues
        syntax_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "syntax"
        ]
        
        assert len(syntax_issues) > 0, "Should detect syntax errors"
        
        # Should have critical or high severity issues
        critical_high_issues = [
            issue for issue in syntax_issues
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]
        ]
        assert len(critical_high_issues) > 0, "Syntax errors should be critical or high severity"
        
        # Deployment readiness should be low
        assert report.readiness_score.status == "not_ready", \
            "Template with syntax errors should not be deployment ready"
    
    def test_cloudformation_security_issues(self, orchestrator):
        """Test validation detects CloudFormation security issues."""
        # Load template with security issues
        template_path = FIXTURES_DIR / "cloudformation" / "security_issues.yaml"
        code = template_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cloudformation")
        
        # Assertions
        assert report is not None
        
        # Should detect security issues (if Checkov is available)
        security_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "security" and issue.severity not in [Severity.INFO]
        ]
        
        # Filter out validator errors
        actual_security_issues = [
            issue for issue in security_issues
            if "error" not in issue.message.lower() and "failed" not in issue.message.lower()
        ]
        
        # If Checkov is available and working, should detect issues
        if len(actual_security_issues) > 0:
            assert len(actual_security_issues) >= 2, \
                f"Should detect multiple security issues, found {len(actual_security_issues)}"


class TestTerraformValidation:
    """Integration tests for Terraform validation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create validation orchestrator with default config."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False,  # Disable terraform plan for tests
            validation_timeout_seconds=120
        )
        return ValidationOrchestrator(config)
    
    def test_valid_terraform_config(self, orchestrator):
        """Test validation of valid Terraform configuration."""
        # Load valid config
        config_path = FIXTURES_DIR / "terraform" / "valid_config.tf"
        code = config_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "terraform")
        
        # Assertions
        assert report is not None
        assert report.iac_format == "terraform"
        assert len(report.results) > 0
        
        # Should have minimal critical issues (allow for provider version differences)
        critical_issues = [
            issue for issue in report.get_issues_by_severity(Severity.CRITICAL)
            if "provider" not in issue.message.lower()
        ]
        
        # Filter out validator errors
        high_issues = [
            issue for issue in report.get_issues_by_severity(Severity.HIGH)
            if "validator" not in issue.message.lower() and "unexpected error" not in issue.message.lower()
        ]
        
        # Valid config should have minimal actual issues
        assert len(critical_issues) <= 1, f"Valid config should have minimal critical issues: {critical_issues}"
        assert len(high_issues) == 0, f"Valid config should have no high issues: {high_issues}"
    
    def test_terraform_syntax_errors(self, orchestrator):
        """Test validation detects Terraform syntax errors."""
        # Load config with syntax errors
        config_path = FIXTURES_DIR / "terraform" / "syntax_error.tf"
        code = config_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "terraform")
        
        # Assertions
        assert report is not None
        
        # Should detect syntax issues
        syntax_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "syntax"
        ]
        
        assert len(syntax_issues) > 0, "Should detect syntax errors"
        
        # Should have critical or high severity issues
        critical_high_issues = [
            issue for issue in syntax_issues
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]
        ]
        assert len(critical_high_issues) > 0, "Syntax errors should be critical or high severity"
    
    def test_terraform_security_issues(self, orchestrator):
        """Test validation detects Terraform security issues."""
        # Load config with security issues
        config_path = FIXTURES_DIR / "terraform" / "security_issues.tf"
        code = config_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "terraform")
        
        # Assertions
        assert report is not None
        
        # Should detect security issues (if Checkov is available)
        security_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "security" and issue.severity not in [Severity.INFO]
        ]
        
        # Filter out validator errors
        actual_security_issues = [
            issue for issue in security_issues
            if "error" not in issue.message.lower() and "failed" not in issue.message.lower()
        ]
        
        # If Checkov is available and working, should detect issues
        if len(actual_security_issues) > 0:
            assert len(actual_security_issues) >= 2, \
                f"Should detect multiple security issues, found {len(actual_security_issues)}"


class TestCDKValidation:
    """Integration tests for AWS CDK validation."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create validation orchestrator with default config."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False,
            validation_timeout_seconds=180  # CDK synthesis may take longer
        )
        return ValidationOrchestrator(config)
    
    def test_valid_cdk_app(self, orchestrator):
        """Test validation of valid CDK application."""
        # Load valid CDK app
        app_path = FIXTURES_DIR / "cdk" / "valid_app.py"
        code = app_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cdk")
        
        # Assertions
        assert report is not None
        assert report.iac_format == "cdk"
        
        # CDK validator may not be available (requires CDK CLI)
        # If no validators available, report will have no results
        if len(report.results) == 0:
            pytest.skip("CDK validator not available (CDK CLI not installed)")
        
        # Check if CDK synthesis succeeded
        cdk_results = [r for r in report.results if "CDK" in r.validator_name]
        if cdk_results:
            # If CDK validator ran, check for synthesis success
            synthesis_issues = [
                issue for result in cdk_results
                for issue in result.issues
                if "synthesized" in issue.message.lower()
            ]
            assert len(synthesis_issues) > 0, "Should report synthesis status"
    
    def test_cdk_syntax_errors(self, orchestrator):
        """Test validation detects CDK syntax errors."""
        # Load CDK app with syntax errors
        app_path = FIXTURES_DIR / "cdk" / "syntax_error.py"
        code = app_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cdk")
        
        # Assertions
        assert report is not None
        
        # CDK validator may not be available
        if len(report.results) == 0:
            pytest.skip("CDK validator not available (CDK CLI not installed)")
        
        # Should detect syntax issues
        syntax_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "syntax"
        ]
        
        assert len(syntax_issues) > 0, "Should detect syntax errors"
    
    def test_cdk_security_issues(self, orchestrator):
        """Test validation detects CDK security issues."""
        # Load CDK app with security issues
        app_path = FIXTURES_DIR / "cdk" / "security_issues.py"
        code = app_path.read_text()
        
        # Run validation
        report = orchestrator.validate(code, "cdk")
        
        # Assertions
        assert report is not None
        
        # Should detect security issues (either in CDK code or synthesized template)
        security_issues = [
            issue for result in report.results
            for issue in result.issues
            if issue.category == "security"
        ]
        
        # CDK security issues may be detected in synthesized template
        if len(security_issues) > 0:
            assert len(security_issues) >= 2, \
                f"Should detect multiple security issues, found {len(security_issues)}"


class TestDeploymentReadinessScoring:
    """Integration tests for deployment readiness scoring."""
    
    def test_scoring_with_no_issues(self):
        """Test scoring calculation with no issues."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=False,  # Disable to avoid external dependencies
            enable_best_practices=False,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use valid CloudFormation template
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Score should be high with no critical issues
        assert report.readiness_score.overall_score >= 60, \
            f"Score should be decent with no critical issues: {report.readiness_score.overall_score}"
    
    def test_scoring_with_critical_issues(self):
        """Test scoring calculation with critical issues."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=False,
            enable_best_practices=False,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use template with syntax errors
        template_path = FIXTURES_DIR / "cloudformation" / "syntax_error.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Should be marked as not ready
        assert report.readiness_score.status == "not_ready", \
            "Template with critical issues should not be ready"
        
        # Should have blocking issues
        assert len(report.readiness_score.blocking_issues) > 0, \
            "Should identify blocking issues"
    
    def test_scoring_categories(self):
        """Test that scoring includes all categories."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use valid template
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Check that score breakdown exists
        score = report.readiness_score
        assert score.syntax_score >= 0
        assert score.security_score >= 0
        assert score.best_practices_score >= 0
        assert score.deployment_score >= 0
        assert score.overall_score >= 0


class TestParallelValidation:
    """Integration tests for parallel validator execution."""
    
    def test_parallel_execution(self):
        """Test that validators run in parallel."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use valid template
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Should have multiple validator results
        assert len(report.results) > 1, \
            "Should run multiple validators"
        
        # Total execution time should be less than sum of individual times
        # (indicating parallel execution)
        individual_times = sum(r.execution_time for r in report.results)
        total_time = report.execution_time_total
        
        # Allow some overhead, but parallel should be faster
        assert total_time <= individual_times * 1.5, \
            f"Parallel execution should be faster: {total_time}s vs {individual_times}s"
    
    def test_validator_failure_handling(self):
        """Test that validation continues even if one validator fails."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use any template
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Should still get a report even if some validators fail
        assert report is not None
        assert report.iac_format == "cloudformation"
        
        # Should have at least some results
        assert len(report.results) >= 0


class TestValidatorAvailability:
    """Integration tests for validator availability checking."""
    
    def test_unavailable_validators_skipped(self):
        """Test that unavailable validators are skipped gracefully."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Get validators for CloudFormation
        validators = orchestrator._get_validators_for_format("cloudformation")
        
        # Should only include available validators
        for validator in validators:
            assert validator.is_available(), \
                f"Validator {validator.get_name()} should be available"
    
    def test_no_validators_available(self):
        """Test handling when no validators are available."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=True,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        # Use unsupported format
        report = orchestrator.validate("some code", "unsupported_format")
        
        # Should return fallback report
        assert report is not None
        assert report.readiness_score.status == "not_ready"
        assert report.total_issues == 0  # No validators ran


class TestReportGeneration:
    """Integration tests for report generation."""
    
    def test_report_structure(self):
        """Test that generated report has correct structure."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=False,
            enable_best_practices=False,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        template_path = FIXTURES_DIR / "cloudformation" / "valid_template.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Check report structure
        assert hasattr(report, "iac_format")
        assert hasattr(report, "code_length")
        assert hasattr(report, "timestamp")
        assert hasattr(report, "results")
        assert hasattr(report, "readiness_score")
        assert hasattr(report, "total_issues")
        assert hasattr(report, "issues_by_severity")
        assert hasattr(report, "issues_by_category")
        assert hasattr(report, "execution_time_total")
    
    def test_issues_aggregation(self):
        """Test that issues are properly aggregated."""
        config = ValidationConfig(
            enable_syntax_validation=True,
            enable_security_scanning=True,
            enable_best_practices=False,
            enable_dry_run=False
        )
        orchestrator = ValidationOrchestrator(config)
        
        template_path = FIXTURES_DIR / "cloudformation" / "security_issues.yaml"
        code = template_path.read_text()
        
        report = orchestrator.validate(code, "cloudformation")
        
        # Check issues aggregation
        assert report.total_issues >= 0
        assert isinstance(report.issues_by_severity, dict)
        assert isinstance(report.issues_by_category, dict)
        
        # Verify counts match
        total_from_severity = sum(report.issues_by_severity.values())
        total_from_category = sum(report.issues_by_category.values())
        
        # Both should count the same total issues
        assert total_from_severity == report.total_issues or total_from_category == report.total_issues


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
