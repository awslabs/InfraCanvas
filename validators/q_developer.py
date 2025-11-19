"""
Amazon Q Developer validator for AI-powered IaC code validation.
"""
import json
import time
import logging
from typing import List, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from validators.base import BaseValidator, ValidationResult, ValidationIssue, Severity

logger = logging.getLogger(__name__)


class QDeveloperValidator(BaseValidator):
    """
    Validates IaC code using Amazon Q Developer via Bedrock.
    
    Provides AI-powered validation including:
    - Syntax and structural analysis
    - Security best practices
    - Cost optimization suggestions
    - AWS Well-Architected Framework compliance
    - Logical consistency checks
    """
    
    def __init__(
        self, 
        iac_format: str,
        model_id: str = "us.anthropic.claude-sonnet-4-20250514-v1:0",
        region: str = "us-east-1",
        boto_session: Optional[object] = None
    ):
        """
        Initialize Q Developer validator.
        
        Args:
            iac_format: The IaC format (cloudformation, terraform, cdk)
            model_id: Bedrock model ID to use for validation (default: Claude Sonnet 4.5)
            region: AWS region for Bedrock client
            boto_session: Optional boto3 Session object
        """
        self.iac_format = iac_format.lower()
        self.model_id = model_id
        self.region = region
        self.boto_session = boto_session
        self._bedrock_client = None
    
    def get_name(self) -> str:
        """Return validator name."""
        return f"Amazon Q Developer Validator ({self.iac_format.upper()})"
    
    def is_available(self) -> bool:
        """Check if boto3 is available and AWS credentials are configured."""
        if not BOTO3_AVAILABLE:
            return False
        
        try:
            session = self.boto_session or boto3.Session()
            session.client('bedrock-runtime', region_name=self.region)
            return True
        except (NoCredentialsError, Exception):
            return False
    
    def validate(self, code: str, temp_dir: str) -> ValidationResult:
        """
        Validate IaC code using Amazon Q Developer.
        
        Args:
            code: The IaC code to validate
            temp_dir: Temporary directory (not used for Q Developer)
            
        Returns:
            ValidationResult with AI-powered validation findings
        """
        start_time = time.time()
        issues = []
        
        if not BOTO3_AVAILABLE:
            issues.append(ValidationIssue(
                severity=Severity.HIGH,
                category="deployment",
                message="boto3 library not available for Q Developer validation",
                remediation="Install boto3: pip install boto3"
            ))
            execution_time = time.time() - start_time
            return ValidationResult(
                validator_name=self.get_name(),
                passed=False,
                issues=issues,
                execution_time=execution_time,
                metadata={"tool": "q-developer", "boto3_available": False}
            )
        
        try:
            # Initialize Bedrock client
            if self._bedrock_client is None:
                session = self.boto_session or boto3.Session()
                self._bedrock_client = session.client(
                    'bedrock-runtime', 
                    region_name=self.region
                )
            
            # Create validation prompt
            prompt = self._create_validation_prompt(code)
            
            # Call Bedrock model
            response = self._invoke_model(prompt)
            
            # Parse response and extract issues
            issues = self._parse_validation_response(response)
            
            # Add success message if no critical issues
            if not any(i.severity in [Severity.CRITICAL, Severity.HIGH] for i in issues):
                issues.insert(0, ValidationIssue(
                    severity=Severity.INFO,
                    category="deployment",
                    message="Amazon Q Developer validation completed successfully",
                    remediation=None
                ))
        
        except NoCredentialsError:
            issues.append(ValidationIssue(
                severity=Severity.HIGH,
                category="deployment",
                message="AWS credentials not found or not configured",
                remediation="Configure AWS credentials using AWS CLI or environment variables"
            ))
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            
            issues.append(ValidationIssue(
                severity=Severity.HIGH,
                category="deployment",
                message=f"Q Developer validation failed: {error_message}",
                remediation="Check AWS credentials and Bedrock model access permissions",
                rule_id=error_code
            ))
        
        except Exception as e:
            logger.error(f"Unexpected error during Q Developer validation: {e}", exc_info=True)
            issues.append(ValidationIssue(
                severity=Severity.HIGH,
                category="deployment",
                message=f"Unexpected error during Q Developer validation: {str(e)}",
                remediation="Check AWS configuration and network connectivity"
            ))
        
        execution_time = time.time() - start_time
        passed = len([i for i in issues if i.severity in [Severity.CRITICAL, Severity.HIGH]]) == 0
        
        return ValidationResult(
            validator_name=self.get_name(),
            passed=passed,
            issues=issues,
            execution_time=execution_time,
            metadata={
                "tool": "q-developer",
                "model_id": self.model_id,
                "iac_format": self.iac_format
            }
        )
    
    def _create_validation_prompt(self, code: str) -> str:
        """
        Create validation prompt for Q Developer.
        
        Args:
            code: The IaC code to validate
            
        Returns:
            Formatted prompt for the model
        """
        format_name = {
            'cloudformation': 'AWS CloudFormation',
            'terraform': 'Terraform',
            'cdk': 'AWS CDK'
        }.get(self.iac_format, self.iac_format)
        
        prompt = f"""You are an expert AWS infrastructure code reviewer and security analyst. Analyze the following {format_name} code and provide a comprehensive validation report.

Review the code for:
1. **Syntax and Structure**: Identify any syntax errors, malformed resources, or structural issues
2. **Security**: Check for security vulnerabilities, misconfigurations, and compliance issues including:
   - Unencrypted resources (S3, EBS, RDS, etc.)
   - Overly permissive IAM policies or security groups
   - Public access to sensitive resources
   - Missing encryption in transit and at rest
   - Hardcoded credentials or secrets
3. **Best Practices**: Validate against AWS Well-Architected Framework:
   - Operational excellence
   - Security
   - Reliability (multi-AZ, backups)
   - Performance efficiency
   - Cost optimization
4. **Deployment Readiness**: Check if the code can be successfully deployed:
   - Missing required parameters or variables
   - Invalid resource references
   - Circular dependencies
   - Resource naming conflicts

{format_name} Code:
```
{code}
```

Provide your analysis in the following JSON format:
{{
  "issues": [
    {{
      "severity": "critical|high|medium|low|info",
      "category": "syntax|security|best_practice|deployment",
      "message": "Brief description of the issue",
      "resource": "Resource name or identifier (if applicable)",
      "line_number": null,
      "remediation": "Specific guidance on how to fix this issue",
      "rule_id": "Rule or check identifier (if applicable)"
    }}
  ],
  "summary": "Overall assessment of the code quality and deployment readiness"
}}

Important:
- Use "critical" severity for issues that prevent deployment or pose immediate security risks
- Use "high" severity for significant security vulnerabilities or major best practice violations
- Use "medium" severity for moderate issues that should be addressed
- Use "low" severity for minor improvements
- Use "info" severity for informational messages or successful validations
- Be specific in remediation guidance with actionable steps
- If the code is valid and follows best practices, include an info-level issue confirming this

Return ONLY the JSON response, no additional text."""
        
        return prompt
    
    def _invoke_model(self, prompt: str) -> str:
        """
        Invoke Bedrock model with the validation prompt.
        
        Args:
            prompt: The validation prompt
            
        Returns:
            Model response text
        """
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "temperature": 0.1,  # Low temperature for consistent, focused analysis
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = self._bedrock_client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body),
            contentType="application/json",
            accept="application/json"
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract text from Claude response format
        if 'content' in response_body and len(response_body['content']) > 0:
            return response_body['content'][0]['text']
        
        raise ValueError("Invalid response format from Bedrock model")
    
    def _parse_validation_response(self, response: str) -> List[ValidationIssue]:
        """
        Parse Q Developer validation response into ValidationIssue objects.
        
        Args:
            response: JSON response from the model
            
        Returns:
            List of ValidationIssue objects
        """
        issues = []
        
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[json_start:json_end]
            validation_data = json.loads(json_str)
            
            # Parse issues
            for issue_data in validation_data.get('issues', []):
                # Map severity string to Severity enum
                severity_str = issue_data.get('severity', 'medium').lower()
                severity_map = {
                    'critical': Severity.CRITICAL,
                    'high': Severity.HIGH,
                    'medium': Severity.MEDIUM,
                    'low': Severity.LOW,
                    'info': Severity.INFO
                }
                severity = severity_map.get(severity_str, Severity.MEDIUM)
                
                # Create ValidationIssue
                issue = ValidationIssue(
                    severity=severity,
                    category=issue_data.get('category', 'deployment'),
                    message=issue_data.get('message', 'Unknown issue'),
                    line_number=issue_data.get('line_number'),
                    resource=issue_data.get('resource'),
                    remediation=issue_data.get('remediation'),
                    rule_id=issue_data.get('rule_id')
                )
                issues.append(issue)
            
            # Log summary if available
            if 'summary' in validation_data:
                logger.info(f"Q Developer Summary: {validation_data['summary']}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Q Developer response as JSON: {e}")
            logger.debug(f"Response content: {response[:500]}")
            
            # Create fallback issue
            issues.append(ValidationIssue(
                severity=Severity.MEDIUM,
                category="deployment",
                message="Q Developer validation completed but response format was unexpected",
                remediation="Check validation logs for details"
            ))
        
        except Exception as e:
            logger.error(f"Error parsing Q Developer response: {e}")
            issues.append(ValidationIssue(
                severity=Severity.MEDIUM,
                category="deployment",
                message=f"Error parsing Q Developer response: {str(e)}",
                remediation="Check validation configuration"
            ))
        
        return issues
