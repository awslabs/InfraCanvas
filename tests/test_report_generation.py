#!/usr/bin/env python3
"""
Test script to verify report generation and scoring functionality.
"""
import os
import tempfile
from datetime import datetime

from validators.base import (
    ValidationResult,
    ValidationIssue,
    Severity
)
from validators.report import ReportGenerator


def test_report_generation():
    """Test basic report generation."""
    print("Testing report generation...")
    print()
    
    # Create sample validation results
    results = [
        ValidationResult(
            validator_name="TestSyntaxValidator",
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    category="syntax",
                    message="Missing required property 'Type'",
                    line_number=10,
                    resource="MyResource",
                    remediation="Add 'Type' property to resource definition"
                ),
                ValidationIssue(
                    severity=Severity.MEDIUM,
                    category="syntax",
                    message="Unused parameter 'Environment'",
                    line_number=5
                )
            ],
            execution_time=0.5
        ),
        ValidationResult(
            validator_name="TestSecurityValidator",
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.HIGH,
                    category="security",
                    message="S3 bucket is publicly accessible",
                    resource="MyBucket",
                    remediation="Set PublicAccessBlockConfiguration"
                ),
                ValidationIssue(
                    severity=Severity.LOW,
                    category="security",
                    message="Missing encryption at rest",
                    resource="MyBucket"
                )
            ],
            execution_time=1.2
        ),
        ValidationResult(
            validator_name="TestBestPracticesValidator",
            passed=True,
            issues=[
                ValidationIssue(
                    severity=Severity.INFO,
                    category="best_practice",
                    message="Consider adding tags for cost tracking"
                )
            ],
            execution_time=0.3
        )
    ]
    
    # Generate report
    generator = ReportGenerator()
    report = generator.generate_report(
        results=results,
        iac_format="cloudformation",
        code_length=1500,
        execution_time_total=2.0
    )
    
    # Verify report contents
    print(f"✓ Report generated successfully")
    print(f"  Format: {report.iac_format}")
    print(f"  Total issues: {report.total_issues}")
    print(f"  Execution time: {report.execution_time_total}s")
    print()
    
    return report


def test_readiness_scoring():
    """Test deployment readiness scoring."""
    print("Testing deployment readiness scoring...")
    print()
    
    # Create results with various severity levels
    results = [
        ValidationResult(
            validator_name="SyntaxValidator",
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.HIGH,
                    category="syntax",
                    message="Syntax error"
                )
            ],
            execution_time=0.5
        ),
        ValidationResult(
            validator_name="SecurityValidator",
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.MEDIUM,
                    category="security",
                    message="Security warning"
                ),
                ValidationIssue(
                    severity=Severity.LOW,
                    category="security",
                    message="Minor security issue"
                )
            ],
            execution_time=1.0
        )
    ]
    
    generator = ReportGenerator()
    score = generator.calculate_readiness_score(results)
    
    print(f"✓ Readiness score calculated")
    print(f"  Overall: {score.overall_score}/100")
    print(f"  Syntax: {score.syntax_score}/100")
    print(f"  Security: {score.security_score}/100")
    print(f"  Best Practices: {score.best_practices_score}/100")
    print(f"  Deployment: {score.deployment_score}/100")
    print(f"  Status: {score.status}")
    print(f"  Blocking issues: {len(score.blocking_issues)}")
    print()
    
    return score


def test_export_functionality():
    """Test JSON and HTML export."""
    print("Testing export functionality...")
    print()
    
    # Create sample report
    results = [
        ValidationResult(
            validator_name="TestValidator",
            passed=True,
            issues=[],
            execution_time=0.5
        )
    ]
    
    generator = ReportGenerator()
    report = generator.generate_report(
        results=results,
        iac_format="terraform",
        code_length=1000,
        execution_time_total=0.5
    )
    
    # Test JSON export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json_path = f.name
    
    try:
        generator.export_json(report, json_path)
        json_size = os.path.getsize(json_path)
        print(f"✓ JSON export successful ({json_size} bytes)")
    finally:
        os.unlink(json_path)
    
    # Test HTML export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_path = f.name
    
    try:
        generator.export_html(report, html_path)
        html_size = os.path.getsize(html_path)
        print(f"✓ HTML export successful ({html_size} bytes)")
    finally:
        os.unlink(html_path)
    
    print()


def test_scoring_edge_cases():
    """Test scoring with edge cases."""
    print("Testing scoring edge cases...")
    print()
    
    generator = ReportGenerator()
    
    # Test 1: Critical syntax issue (should be not_ready)
    results_critical = [
        ValidationResult(
            validator_name="SyntaxValidator",
            passed=False,
            issues=[
                ValidationIssue(
                    severity=Severity.CRITICAL,
                    category="syntax",
                    message="Critical syntax error"
                )
            ],
            execution_time=0.5
        )
    ]
    score = generator.calculate_readiness_score(results_critical)
    assert score.status == "not_ready", "Critical syntax issue should result in not_ready"
    assert len(score.blocking_issues) > 0, "Should have blocking issues"
    print(f"✓ Critical syntax issue: {score.status} (score: {score.overall_score})")
    
    # Test 2: No issues (should be ready)
    results_clean = [
        ValidationResult(
            validator_name="AllValidator",
            passed=True,
            issues=[],
            execution_time=0.5
        )
    ]
    score = generator.calculate_readiness_score(results_clean)
    assert score.status == "ready", "No issues should result in ready"
    assert score.overall_score == 100.0, "Perfect score expected"
    print(f"✓ No issues: {score.status} (score: {score.overall_score})")
    
    # Test 3: Minor issues (should be ready_with_warnings or ready)
    results_minor = [
        ValidationResult(
            validator_name="BestPracticesValidator",
            passed=True,
            issues=[
                ValidationIssue(
                    severity=Severity.LOW,
                    category="best_practice",
                    message="Minor best practice violation"
                ),
                ValidationIssue(
                    severity=Severity.INFO,
                    category="best_practice",
                    message="Informational message"
                )
            ],
            execution_time=0.5
        )
    ]
    score = generator.calculate_readiness_score(results_minor)
    assert score.status in ["ready", "ready_with_warnings"], "Minor issues should not block"
    print(f"✓ Minor issues: {score.status} (score: {score.overall_score})")
    
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Report Generation and Scoring Tests")
    print("=" * 60)
    print()
    
    try:
        # Run tests
        test_report_generation()
        test_readiness_scoring()
        test_export_functionality()
        test_scoring_edge_cases()
        
        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
