# InfraCanvas

## Description

It is a tool that is used to generate CloudFormation/CDK/Terraform code from architecture diagram. It analyses the file asks a set of relevant
questions regarding the target infrastructure environment and also regarding the application, then it generates teh IaC code.

## Prerequisites

- Python
- AWS account
- Access to Bedrock model Claude Sonnet 3.7 in your AWS account

## Installation and Local Running of Code

To locally run the code you must have python installed in your system as a prerequisite. Then follow these steps:-

- Clone the repository
- Go to the terminal of the project repository
- Configure AWS profile
- Run `python3 -m venv .venv`
- Run `source .venv/bin/activate`
- Install dependencies `pip install -r requirements.txt`
- For running the code use `streamlit run app.py`

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

