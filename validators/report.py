"""
Report generation and scoring for validation results.
"""
import json
from datetime import datetime
from typing import List, Dict
from collections import defaultdict

from validators.base import (
    ValidationResult,
    ValidationReport,
    ValidationIssue,
    DeploymentReadinessScore,
    Severity
)


class ReportGenerator:
    """Generates comprehensive validation reports and calculates deployment readiness scores."""
    
    # Weights for each validation category
    CATEGORY_WEIGHTS = {
        "syntax": 0.30,          # 30% - Must pass for deployment
        "security": 0.30,        # 30% - Critical for production
        "best_practice": 0.20,   # 20% - Important but not blocking
        "deployment": 0.20       # 20% - Dry-run validation
    }
    
    # Point deductions by severity
    SEVERITY_PENALTIES = {
        Severity.CRITICAL: 20,
        Severity.HIGH: 10,
        Severity.MEDIUM: 5,
        Severity.LOW: 2,
        Severity.INFO: 1
    }
    
    def generate_report(
        self,
        results: List[ValidationResult],
        iac_format: str,
        code_length: int,
        execution_time_total: float
    ) -> ValidationReport:
        """
        Generate comprehensive validation report.
        
        Args:
            results: List of ValidationResult objects from validators
            iac_format: The IaC format that was validated
            code_length: Length of the validated code
            execution_time_total: Total execution time for all validators
            
        Returns:
            ValidationReport with aggregated results and scoring
        """
        # Aggregate all issues
        all_issues = []
        for result in results:
            all_issues.extend(result.issues)
        
        # Count issues by severity
        issues_by_severity = self._count_by_severity(all_issues)
        
        # Count issues by category
        issues_by_category = self._count_by_category(all_issues)
        
        # Calculate deployment readiness score
        readiness_score = self.calculate_readiness_score(results)
        
        # Create report
        report = ValidationReport(
            iac_format=iac_format,
            code_length=code_length,
            timestamp=datetime.now(),
            results=results,
            readiness_score=readiness_score,
            total_issues=len(all_issues),
            issues_by_severity=issues_by_severity,
            issues_by_category=issues_by_category,
            execution_time_total=execution_time_total
        )
        
        return report
    
    def calculate_readiness_score(
        self, 
        results: List[ValidationResult]
    ) -> DeploymentReadinessScore:
        """
        Calculate deployment readiness score with weighted categories.
        
        Args:
            results: List of ValidationResult objects
            
        Returns:
            DeploymentReadinessScore with breakdown by category
        """
        # Group issues by category
        issues_by_category = defaultdict(list)
        for result in results:
            for issue in result.issues:
                issues_by_category[issue.category].append(issue)
        
        # Calculate category scores (start at 100, deduct points)
        syntax_score = self._calculate_category_score(
            issues_by_category.get("syntax", [])
        )
        security_score = self._calculate_category_score(
            issues_by_category.get("security", [])
        )
        best_practices_score = self._calculate_category_score(
            issues_by_category.get("best_practice", [])
        )
        deployment_score = self._calculate_category_score(
            issues_by_category.get("deployment", [])
        )
        
        # Calculate weighted overall score
        overall_score = (
            syntax_score * self.CATEGORY_WEIGHTS["syntax"] +
            security_score * self.CATEGORY_WEIGHTS["security"] +
            best_practices_score * self.CATEGORY_WEIGHTS["best_practice"] +
            deployment_score * self.CATEGORY_WEIGHTS["deployment"]
        )
        
        # Identify blocking issues
        blocking_issues = self._identify_blocking_issues(issues_by_category)
        
        # Determine status
        status = self._determine_status(
            overall_score, 
            syntax_score, 
            security_score, 
            deployment_score,
            blocking_issues
        )
        
        return DeploymentReadinessScore(
            overall_score=round(overall_score, 2),
            syntax_score=round(syntax_score, 2),
            security_score=round(security_score, 2),
            best_practices_score=round(best_practices_score, 2),
            deployment_score=round(deployment_score, 2),
            status=status,
            blocking_issues=blocking_issues
        )
    
    def _calculate_category_score(self, issues: List[ValidationIssue]) -> float:
        """
        Calculate score for a single category (0-100).
        
        Args:
            issues: List of issues in this category
            
        Returns:
            Score from 0-100
        """
        score = 100.0
        
        for issue in issues:
            penalty = self.SEVERITY_PENALTIES.get(issue.severity, 0)
            score -= penalty
        
        # Ensure score doesn't go below 0
        return max(0.0, score)
    
    def _identify_blocking_issues(
        self, 
        issues_by_category: Dict[str, List[ValidationIssue]]
    ) -> List[ValidationIssue]:
        """
        Identify issues that block deployment.
        
        Args:
            issues_by_category: Issues grouped by category
            
        Returns:
            List of blocking issues
        """
        blocking = []
        
        # Critical syntax issues block deployment
        for issue in issues_by_category.get("syntax", []):
            if issue.severity == Severity.CRITICAL:
                blocking.append(issue)
        
        # Critical security issues block deployment
        for issue in issues_by_category.get("security", []):
            if issue.severity == Severity.CRITICAL:
                blocking.append(issue)
        
        # Critical deployment issues block deployment
        for issue in issues_by_category.get("deployment", []):
            if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
                blocking.append(issue)
        
        return blocking
    
    def _determine_status(
        self,
        overall_score: float,
        syntax_score: float,
        security_score: float,
        deployment_score: float,
        blocking_issues: List[ValidationIssue]
    ) -> str:
        """
        Determine deployment readiness status.
        
        Args:
            overall_score: Overall weighted score
            syntax_score: Syntax validation score
            security_score: Security scanning score
            deployment_score: Deployment validation score
            blocking_issues: List of blocking issues
            
        Returns:
            Status string: "ready", "ready_with_warnings", or "not_ready"
        """
        # If there are blocking issues, not ready
        if blocking_issues:
            return "not_ready"
        
        # If syntax or deployment failed completely, not ready
        if syntax_score == 0 or deployment_score == 0:
            return "not_ready"
        
        # If overall score is below 60, not ready
        if overall_score < 60:
            return "not_ready"
        
        # If score is between 60-79, ready with warnings
        if overall_score < 80:
            return "ready_with_warnings"
        
        # Score >= 80, ready
        return "ready"
    
    def _count_by_severity(
        self, 
        issues: List[ValidationIssue]
    ) -> Dict[Severity, int]:
        """Count issues grouped by severity."""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.severity] += 1
        return dict(counts)
    
    def _count_by_category(
        self, 
        issues: List[ValidationIssue]
    ) -> Dict[str, int]:
        """Count issues grouped by category."""
        counts = defaultdict(int)
        for issue in issues:
            counts[issue.category] += 1
        return dict(counts)
    
    def export_json(self, report: ValidationReport, output_path: str):
        """
        Export report as JSON file.
        
        Args:
            report: ValidationReport to export
            output_path: Path to write JSON file
        """
        # Convert report to dictionary
        report_dict = {
            "iac_format": report.iac_format,
            "code_length": report.code_length,
            "timestamp": report.timestamp.isoformat(),
            "total_issues": report.total_issues,
            "execution_time_total": report.execution_time_total,
            "readiness_score": {
                "overall_score": report.readiness_score.overall_score,
                "syntax_score": report.readiness_score.syntax_score,
                "security_score": report.readiness_score.security_score,
                "best_practices_score": report.readiness_score.best_practices_score,
                "deployment_score": report.readiness_score.deployment_score,
                "status": report.readiness_score.status,
                "blocking_issues_count": len(report.readiness_score.blocking_issues)
            },
            "issues_by_severity": {
                k.value: v for k, v in report.issues_by_severity.items()
            },
            "issues_by_category": report.issues_by_category,
            "results": [
                {
                    "validator_name": result.validator_name,
                    "passed": result.passed,
                    "execution_time": result.execution_time,
                    "issues_count": len(result.issues),
                    "issues": [
                        {
                            "severity": issue.severity.value,
                            "category": issue.category,
                            "message": issue.message,
                            "line_number": issue.line_number,
                            "resource": issue.resource,
                            "remediation": issue.remediation,
                            "rule_id": issue.rule_id
                        }
                        for issue in result.issues
                    ]
                }
                for result in report.results
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report_dict, f, indent=2)
    
    def export_html(self, report: ValidationReport, output_path: str):
        """
        Export report as formatted HTML file.
        
        Args:
            report: ValidationReport to export
            output_path: Path to write HTML file
        """
        # Generate HTML content
        html_content = self._generate_html_report(report)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _generate_html_report(self, report: ValidationReport) -> str:
        """Generate HTML content for report."""
        # Status color mapping
        status_colors = {
            "ready": "#28a745",
            "ready_with_warnings": "#ffc107",
            "not_ready": "#dc3545"
        }
        
        status_color = status_colors.get(
            report.readiness_score.status, 
            "#6c757d"
        )
        
        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>IaC Validation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .score-section {{
            background-color: {status_color};
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            text-align: center;
        }}
        .score-value {{
            font-size: 48px;
            font-weight: bold;
        }}
        .score-status {{
            font-size: 24px;
            margin-top: 10px;
        }}
        .category-scores {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .category-card {{
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .category-card h3 {{
            margin: 0 0 10px 0;
            color: #495057;
            font-size: 14px;
        }}
        .category-card .score {{
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        th {{
            background-color: #007bff;
            color: white;
        }}
        .severity-critical {{ color: #dc3545; font-weight: bold; }}
        .severity-high {{ color: #fd7e14; font-weight: bold; }}
        .severity-medium {{ color: #ffc107; font-weight: bold; }}
        .severity-low {{ color: #17a2b8; }}
        .severity-info {{ color: #6c757d; }}
        .summary {{
            background-color: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>IaC Validation Report</h1>
        
        <div class="summary">
            <p><strong>Format:</strong> {report.iac_format}</p>
            <p><strong>Timestamp:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Code Length:</strong> {report.code_length} characters</p>
            <p><strong>Execution Time:</strong> {report.execution_time_total:.2f} seconds</p>
            <p><strong>Total Issues:</strong> {report.total_issues}</p>
        </div>
        
        <div class="score-section">
            <div class="score-value">{report.readiness_score.overall_score:.0f}/100</div>
            <div class="score-status">{report.readiness_score.status.replace('_', ' ').title()}</div>
        </div>
        
        <div class="category-scores">
            <div class="category-card">
                <h3>Syntax</h3>
                <div class="score">{report.readiness_score.syntax_score:.0f}</div>
            </div>
            <div class="category-card">
                <h3>Security</h3>
                <div class="score">{report.readiness_score.security_score:.0f}</div>
            </div>
            <div class="category-card">
                <h3>Best Practices</h3>
                <div class="score">{report.readiness_score.best_practices_score:.0f}</div>
            </div>
            <div class="category-card">
                <h3>Deployment</h3>
                <div class="score">{report.readiness_score.deployment_score:.0f}</div>
            </div>
        </div>
        
        <h2>Validation Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Validator</th>
                    <th>Status</th>
                    <th>Issues</th>
                    <th>Time (s)</th>
                </tr>
            </thead>
            <tbody>
"""
        
        for result in report.results:
            status = "✓ Passed" if result.passed else "✗ Failed"
            html += f"""
                <tr>
                    <td>{result.validator_name}</td>
                    <td>{status}</td>
                    <td>{len(result.issues)}</td>
                    <td>{result.execution_time:.2f}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
        
        <h2>Issues Found</h2>
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Category</th>
                    <th>Message</th>
                    <th>Resource</th>
                    <th>Line</th>
                </tr>
            </thead>
            <tbody>
"""
        
        # Add all issues
        for result in report.results:
            for issue in result.issues:
                severity_class = f"severity-{issue.severity.value}"
                html += f"""
                <tr>
                    <td class="{severity_class}">{issue.severity.value.upper()}</td>
                    <td>{issue.category}</td>
                    <td>{issue.message}</td>
                    <td>{issue.resource or '-'}</td>
                    <td>{issue.line_number or '-'}</td>
                </tr>
"""
        
        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        
        return html
