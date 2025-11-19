# InfraCanvas Test Suite

This directory contains all tests for the InfraCanvas IaC validation system.

## Test Structure

### Unit Tests

- **`test_config.py`** - Configuration management tests
  - Loading/saving configuration
  - Environment variable overrides
  - Configuration merging

- **`test_report_generation.py`** - Report generation and scoring tests
  - Report structure validation
  - Deployment readiness scoring
  - JSON/HTML export functionality

- **`test_orchestrator_cdk.py`** - Orchestrator initialization tests
  - Validator registration
  - Format-specific validator selection
  - Q Developer integration

### Integration Tests

- **`test_integration.py`** - End-to-end validation tests
  - CloudFormation validation flows
  - Terraform validation flows
  - CDK validation flows
  - Deployment readiness scoring
  - Parallel validator execution
  - Report generation

## Test Fixtures

The `fixtures/` directory contains sample IaC code for testing:

```
fixtures/
├── cloudformation/
│   ├── valid_template.yaml
│   ├── syntax_error.yaml
│   └── security_issues.yaml
├── terraform/
│   ├── valid_config.tf
│   ├── syntax_error.tf
│   └── security_issues.tf
└── cdk/
    ├── valid_app.py
    ├── syntax_error.py
    └── security_issues.py
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_config.py
```

### Run with Verbose Output
```bash
pytest tests/ -v
```

### Run with Coverage
```bash
pytest tests/ --cov=validators --cov=config --cov-report=html
```

## Test Requirements

- **pytest>=7.0.0** - Test framework
- **boto3>=1.38.0** - AWS SDK (for Q Developer validator)
- **streamlit>=1.45.1** - UI framework

## Notes

- Integration tests use Q Developer validator (requires AWS credentials and Bedrock access)
- Some tests may be skipped if optional tools are not installed
- Test fixtures are minimal examples designed to trigger specific validation scenarios
