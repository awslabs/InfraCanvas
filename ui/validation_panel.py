# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
UI components for displaying validation results.
"""
import streamlit as st
import json
from typing import List, Dict
from datetime import datetime
from validators.base import ValidationReport, ValidationIssue, Severity
from validators.report import ReportGenerator


class ValidationResultsPanel:
    """UI component for rendering validation results."""
    
    @staticmethod
    def render(report: ValidationReport):
        """
        Render validation results in Streamlit UI.
        
        Args:
            report: ValidationReport containing validation results
        """
        if not report:
            return
        
        st.markdown("---")
        st.markdown("## 🔍 Validation Results")
        
        # Render deployment readiness score
        ValidationResultsPanel.render_score_gauge(report)
        
        # Render issue summary
        ValidationResultsPanel.render_issue_summary(report)
        
        # Render detailed issues by category
        ValidationResultsPanel.render_issues_by_category(report)
        
        # Render download buttons
        ValidationResultsPanel.render_download_buttons(report)
    
    @staticmethod
    def render_score_gauge(report: ValidationReport):
        """
        Display deployment readiness score with color-coded indicator.
        
        Args:
            report: ValidationReport containing readiness score
        """
        score = report.readiness_score
        
        # Determine color based on score
        if score.overall_score >= 80:
            color = "green"
            emoji = "✅"
        elif score.overall_score >= 60:
            color = "orange"
            emoji = "⚠️"
        else:
            color = "red"
            emoji = "❌"
        
        # Display score with color-coded styling
        col1, col2, col3 = st.columns([2, 1, 2])
        
        with col1:
            st.markdown(f"### {emoji} Deployment Readiness")
            st.markdown(f"**Status:** :{color}[{score.status.replace('_', ' ').title()}]")
        
        with col2:
            # Display score as a large number
            st.markdown(
                f"<div style='text-align: center;'>"
                f"<h1 style='color: {color}; font-size: 4em; margin: 0;'>{score.overall_score:.0f}</h1>"
                f"<p style='margin: 0;'>out of 100</p>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown("### Score Breakdown")
            st.markdown(f"**Syntax:** {score.syntax_score:.0f}/100")
            st.markdown(f"**Security:** {score.security_score:.0f}/100")
            st.markdown(f"**Best Practices:** {score.best_practices_score:.0f}/100")
            st.markdown(f"**Deployment:** {score.deployment_score:.0f}/100")
        
        # Display blocking issues if any
        if score.blocking_issues:
            st.error(f"🚫 **{len(score.blocking_issues)} Blocking Issue(s) Found**")
            for issue in score.blocking_issues[:3]:  # Show first 3 blocking issues
                st.markdown(f"- {issue.message}")
            if len(score.blocking_issues) > 3:
                st.markdown(f"*...and {len(score.blocking_issues) - 3} more*")
    
    @staticmethod
    def render_issue_summary(report: ValidationReport):
        """
        Render summary of issues by severity.
        
        Args:
            report: ValidationReport containing issues
        """
        if report.total_issues == 0:
            st.success("🎉 No issues found! Your code looks great.")
            return
        
        st.markdown(f"### 📊 Issue Summary ({report.total_issues} total)")
        
        # Create columns for severity breakdown
        cols = st.columns(5)
        
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
        severity_colors = {
            Severity.CRITICAL: "red",
            Severity.HIGH: "orange",
            Severity.MEDIUM: "blue",
            Severity.LOW: "gray",
            Severity.INFO: "green"
        }
        severity_emojis = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🔵",
            Severity.LOW: "⚪",
            Severity.INFO: "🟢"
        }
        
        for idx, severity in enumerate(severity_order):
            count = report.issues_by_severity.get(severity, 0)
            with cols[idx]:
                emoji = severity_emojis[severity]
                st.markdown(
                    f"<div style='text-align: center;'>"
                    f"<p style='font-size: 2em; margin: 0;'>{emoji}</p>"
                    f"<h3 style='margin: 0;'>{count}</h3>"
                    f"<p style='margin: 0; font-size: 0.8em;'>{severity.value.title()}</p>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
    @staticmethod
    def render_issues_by_category(report: ValidationReport):
        """
        Render issues grouped by category with expandable sections.
        
        Args:
            report: ValidationReport containing categorized issues
        """
        if report.total_issues == 0:
            return
        
        st.markdown("### 📋 Detailed Issues")
        
        # Group issues by category
        issues_by_category = ValidationResultsPanel._group_issues_by_category(report)
        
        # Category metadata
        category_info = {
            "syntax": {"emoji": "📝", "title": "Syntax Validation"},
            "security": {"emoji": "🔒", "title": "Security Scanning"},
            "best_practice": {"emoji": "⭐", "title": "Best Practices"},
            "deployment": {"emoji": "🚀", "title": "Deployment Readiness"}
        }
        
        # Render each category
        for category, issues in issues_by_category.items():
            if not issues:
                continue
            
            info = category_info.get(category, {"emoji": "📌", "title": category.title()})
            
            with st.expander(
                f"{info['emoji']} {info['title']} ({len(issues)} issue{'s' if len(issues) != 1 else ''})",
                expanded=(category in ["syntax", "security"] and len(issues) > 0)
            ):
                ValidationResultsPanel.render_issue_table(issues)
    
    @staticmethod
    def render_issue_table(issues: List[ValidationIssue]):
        """
        Display issues in a formatted table.
        
        Args:
            issues: List of ValidationIssue objects to display
        """
        if not issues:
            st.info("No issues in this category")
            return
        
        # Sort issues by severity
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4
        }
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.severity, 5))
        
        # Render each issue
        for idx, issue in enumerate(sorted_issues):
            ValidationResultsPanel._render_single_issue(issue, idx)
    
    @staticmethod
    def _render_single_issue(issue: ValidationIssue, index: int):
        """
        Render a single issue with all details.
        
        Args:
            issue: ValidationIssue to render
            index: Index of the issue for unique keys
        """
        # Severity badge styling
        severity_colors = {
            Severity.CRITICAL: "#ff4444",
            Severity.HIGH: "#ff8800",
            Severity.MEDIUM: "#4488ff",
            Severity.LOW: "#888888",
            Severity.INFO: "#44ff44"
        }
        
        color = severity_colors.get(issue.severity, "#888888")
        
        # Create container for issue
        with st.container():
            col1, col2 = st.columns([1, 10])
            
            with col1:
                st.markdown(
                    f"<div style='background-color: {color}; color: white; "
                    f"padding: 5px; border-radius: 5px; text-align: center; "
                    f"font-weight: bold; font-size: 0.8em;'>"
                    f"{issue.severity.value.upper()}"
                    f"</div>",
                    unsafe_allow_html=True
                )
            
            with col2:
                # Issue message
                st.markdown(f"**{issue.message}**")
                
                # Additional details
                details = []
                if issue.resource:
                    details.append(f"**Resource:** `{issue.resource}`")
                if issue.line_number:
                    details.append(f"**Line:** {issue.line_number}")
                if issue.rule_id:
                    details.append(f"**Rule:** `{issue.rule_id}`")
                
                if details:
                    st.markdown(" | ".join(details))
                
                # Remediation guidance
                if issue.remediation:
                    with st.expander("💡 How to fix", expanded=False):
                        st.markdown(issue.remediation)
            
            st.markdown("---")
    
    @staticmethod
    def _group_issues_by_category(report: ValidationReport) -> Dict[str, List[ValidationIssue]]:
        """
        Group all issues by category.
        
        Args:
            report: ValidationReport containing results
            
        Returns:
            Dictionary mapping category names to lists of issues
        """
        issues_by_category = {
            "syntax": [],
            "security": [],
            "best_practice": [],
            "deployment": []
        }
        
        for result in report.results:
            for issue in result.issues:
                category = issue.category
                if category in issues_by_category:
                    issues_by_category[category].append(issue)
        
        return issues_by_category
    
    @staticmethod
    def render_download_buttons(report: ValidationReport):
        """
        Render download buttons for JSON and HTML report formats.
        
        Args:
            report: ValidationReport to export
        """
        st.markdown("---")
        st.markdown("### 📥 Download Reports")
        
        col1, col2 = st.columns(2)
        
        # Generate report generator instance
        report_gen = ReportGenerator()
        
        with col1:
            # JSON download button
            json_data = ValidationResultsPanel._generate_json_report(report)
            st.download_button(
                label="📄 Download JSON Report",
                data=json_data,
                file_name=f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # HTML download button
            html_data = ValidationResultsPanel._generate_html_report(report)
            st.download_button(
                label="🌐 Download HTML Report",
                data=html_data,
                file_name=f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                mime="text/html",
                use_container_width=True
            )
    
    @staticmethod
    def _generate_json_report(report: ValidationReport) -> str:
        """
        Generate JSON report from ValidationReport.
        
        Args:
            report: ValidationReport to convert
            
        Returns:
            JSON string representation of the report
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
                "blocking_issues": [
                    {
                        "severity": issue.severity.value,
                        "category": issue.category,
                        "message": issue.message,
                        "line_number": issue.line_number,
                        "resource": issue.resource,
                        "remediation": issue.remediation,
                        "rule_id": issue.rule_id
                    }
                    for issue in report.readiness_score.blocking_issues
                ]
            },
            "issues_by_severity": {
                severity.value: count 
                for severity, count in report.issues_by_severity.items()
            },
            "issues_by_category": report.issues_by_category,
            "results": [
                {
                    "validator_name": result.validator_name,
                    "passed": result.passed,
                    "execution_time": result.execution_time,
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
        
        return json.dumps(report_dict, indent=2)
    
    @staticmethod
    def _generate_html_report(report: ValidationReport) -> str:
        """
        Generate HTML report from ValidationReport.
        
        Args:
            report: ValidationReport to convert
            
        Returns:
            HTML string representation of the report
        """
        # Determine status color
        score = report.readiness_score.overall_score
        if score >= 80:
            status_color = "#28a745"
            status_text = "Ready"
        elif score >= 60:
            status_color = "#ffc107"
            status_text = "Ready with Warnings"
        else:
            status_color = "#dc3545"
            status_text = "Not Ready"
        
        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>InfraCanvas Validation Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .score-card {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }}
        .score-number {{
            font-size: 72px;
            font-weight: bold;
            color: {status_color};
            margin: 20px 0;
        }}
        .status-badge {{
            display: inline-block;
            background-color: {status_color};
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: bold;
        }}
        .score-breakdown {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-top: 30px;
        }}
        .score-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .score-item h3 {{
            margin: 0 0 10px 0;
            color: #666;
            font-size: 14px;
        }}
        .score-item .value {{
            font-size: 32px;
            font-weight: bold;
            color: #333;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card .count {{
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card .label {{
            color: #666;
            font-size: 14px;
        }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #007bff; }}
        .low {{ color: #6c757d; }}
        .info {{ color: #28a745; }}
        .issues-section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .issue {{
            border-left: 4px solid #ddd;
            padding: 15px;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .issue.critical {{ border-left-color: #dc3545; }}
        .issue.high {{ border-left-color: #fd7e14; }}
        .issue.medium {{ border-left-color: #007bff; }}
        .issue.low {{ border-left-color: #6c757d; }}
        .issue.info {{ border-left-color: #28a745; }}
        .issue-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}
        .severity-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            color: white;
            margin-right: 10px;
        }}
        .severity-badge.critical {{ background-color: #dc3545; }}
        .severity-badge.high {{ background-color: #fd7e14; }}
        .severity-badge.medium {{ background-color: #007bff; }}
        .severity-badge.low {{ background-color: #6c757d; }}
        .severity-badge.info {{ background-color: #28a745; }}
        .issue-message {{
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .issue-details {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .remediation {{
            background: #e7f3ff;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            font-size: 14px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 InfraCanvas Validation Report</h1>
        <p>Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>IaC Format: {report.iac_format} | Code Length: {report.code_length} characters</p>
    </div>
    
    <div class="score-card">
        <h2>Deployment Readiness Score</h2>
        <div class="score-number">{report.readiness_score.overall_score:.0f}</div>
        <div class="status-badge">{status_text}</div>
        
        <div class="score-breakdown">
            <div class="score-item">
                <h3>Syntax</h3>
                <div class="value">{report.readiness_score.syntax_score:.0f}</div>
            </div>
            <div class="score-item">
                <h3>Security</h3>
                <div class="value">{report.readiness_score.security_score:.0f}</div>
            </div>
            <div class="score-item">
                <h3>Best Practices</h3>
                <div class="value">{report.readiness_score.best_practices_score:.0f}</div>
            </div>
            <div class="score-item">
                <h3>Deployment</h3>
                <div class="value">{report.readiness_score.deployment_score:.0f}</div>
            </div>
        </div>
    </div>
    
    <div class="summary-cards">
        <div class="summary-card">
            <div class="count critical">{report.issues_by_severity.get(Severity.CRITICAL, 0)}</div>
            <div class="label">Critical</div>
        </div>
        <div class="summary-card">
            <div class="count high">{report.issues_by_severity.get(Severity.HIGH, 0)}</div>
            <div class="label">High</div>
        </div>
        <div class="summary-card">
            <div class="count medium">{report.issues_by_severity.get(Severity.MEDIUM, 0)}</div>
            <div class="label">Medium</div>
        </div>
        <div class="summary-card">
            <div class="count low">{report.issues_by_severity.get(Severity.LOW, 0)}</div>
            <div class="label">Low</div>
        </div>
        <div class="summary-card">
            <div class="count info">{report.issues_by_severity.get(Severity.INFO, 0)}</div>
            <div class="label">Info</div>
        </div>
    </div>
"""
        
        # Add issues by category
        issues_by_category = ValidationResultsPanel._group_issues_by_category(report)
        
        category_titles = {
            "syntax": "📝 Syntax Validation",
            "security": "🔒 Security Scanning",
            "best_practice": "⭐ Best Practices",
            "deployment": "🚀 Deployment Readiness"
        }
        
        for category, issues in issues_by_category.items():
            if not issues:
                continue
            
            html += f"""
    <div class="issues-section">
        <h2>{category_titles.get(category, category.title())}</h2>
        <p>{len(issues)} issue(s) found</p>
"""
            
            for issue in issues:
                html += f"""
        <div class="issue {issue.severity.value}">
            <div class="issue-header">
                <span class="severity-badge {issue.severity.value}">{issue.severity.value.upper()}</span>
            </div>
            <div class="issue-message">{issue.message}</div>
"""
                
                details = []
                if issue.resource:
                    details.append(f"Resource: {issue.resource}")
                if issue.line_number:
                    details.append(f"Line: {issue.line_number}")
                if issue.rule_id:
                    details.append(f"Rule: {issue.rule_id}")
                
                if details:
                    html += f'<div class="issue-details">{" | ".join(details)}</div>'
                
                if issue.remediation:
                    html += f'<div class="remediation"><strong>💡 How to fix:</strong> {issue.remediation}</div>'
                
                html += """
        </div>
"""
            
            html += """
    </div>
"""
        
        # Add footer
        html += f"""
    <div class="footer">
        <p>Report generated by InfraCanvas Validation System</p>
        <p>Execution Time: {report.execution_time_total:.2f} seconds</p>
    </div>
</body>
</html>
"""
        
        return html
