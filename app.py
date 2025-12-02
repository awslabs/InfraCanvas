# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import time
import sys
import logging
import re
from datetime import datetime
from io import StringIO

import boto3
import streamlit as st
from botocore.config import Config
from botocore.exceptions import ClientError

from prompts import get_initial_prompt, get_final_prompt
from validators.orchestrator import ValidationOrchestrator
from validators.base import ValidationConfig
from ui.validation_panel import ValidationResultsPanel
from config import load_config, save_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

APP_TITLE = "INFRA-CANVAS APPLICATION"
IAC_FORMATS = {
    "CloudFormation": "yaml",
    "Terraform": "hcl",
    "AWS CDK (Python)": "python",
    "AWS CDK (TypeScript)": "typescript",
    "AWS CDK (Java)": "java",
}
client = boto3.client(
    service_name="bedrock-runtime",
    config=Config(retries={"max_attempts": 3}, read_timeout=300, connect_timeout=300),
)
model_id = "us.anthropic.claude-sonnet-4-20250514-v1:0"
native_request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 10000,
    "temperature": 0.2,
    "messages": [],
}


# Custom log handler to capture logs for UI display
class StreamlitLogHandler(logging.Handler):
    """Custom log handler that stores logs in session state for UI display."""
    
    def __init__(self):
        super().__init__()
        self.log_buffer = []
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_buffer.append({
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'message': msg
            })
            # Keep only last 100 log entries
            if len(self.log_buffer) > 100:
                self.log_buffer.pop(0)
        except Exception:
            self.handleError(record)
    
    def get_logs(self):
        return self.log_buffer
    
    def clear_logs(self):
        self.log_buffer.clear()


# Session State Initialization
def initialize_session_state():
    if "responses" not in st.session_state:
        st.session_state.update(
            {
                "responses": {},
                "questions": [],
                "context_history": "",
                "current_file": None,
                "streaming_complete": False,
                "validation_report": None,
                "generated_code": None,
                "selected_iac_format": None,
            }
        )
    
    # Initialize validation config if not present
    if "validation_config" not in st.session_state:
        st.session_state.validation_config = load_config()
    
    # Initialize auto-validation setting
    if "auto_validate" not in st.session_state:
        st.session_state.auto_validate = True
    
    # Initialize log handler for UI display
    if "log_handler" not in st.session_state:
        st.session_state.log_handler = StreamlitLogHandler()
        # Add handler to root logger to capture all validation logs
        root_logger = logging.getLogger()
        root_logger.addHandler(st.session_state.log_handler)
    
    # Initialize show_logs setting
    if "show_logs" not in st.session_state:
        st.session_state.show_logs = False


# Question generation and handling
def generate_questions(uploaded_file, context_history, text_input):
    with st.spinner("Generating questions..."):
        response_text = get_bedrock_response(uploaded_file, context_history, text_input)
        questions = response_text[0].split("?")
        st.session_state.context_history = response_text[1]
        return [q.strip() for q in questions if q.strip()]


# Response form handling
def create_response_form(questions):
    responses = {}
    with st.form("response_form"):
        for i, question in enumerate(questions):
            if question:
                responses[f"response_{i}"] = st.text_input(
                    key=f"response{i}", label=f"{question}?"
                )

        selected_format = st.selectbox(
            "Select IAC Format", options=list(IAC_FORMATS.keys())
        )

        notes = st.text_area("Additional Notes/Requirements")

        submit = st.form_submit_button(label="Submit Responses")

        return submit, responses, selected_format, notes


def get_bedrock_response(file, context, textinput):
    prompt = get_initial_prompt(file, textinput)
    native_request["messages"] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    request = json.dumps(native_request)
    try:
        response = client.invoke_model(modelId=model_id, body=request)
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        sys.exit(1)

    model_response = json.loads(response["body"].read())
    response_text = model_response["content"][0]["text"]
    context += response_text
    return response_text, context


def get_bedrock_response_stream(
    file, qa_string, context_history, iac_format, additional_notes
):
    prompt = get_final_prompt(
        file, additional_notes, iac_format, qa_string, context_history
    )

    native_request["messages"] = [
        {
            "role": "user",
            "content": [{"type": "text", "text": prompt}],
        }
    ]

    request = json.dumps(native_request)

    try:
        response = client.invoke_model_with_response_stream(
            modelId=model_id, body=request
        )
        return response

    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        sys.exit(1)


def stream_code_display(iac_format, response_stream):
    import re
    
    # Create containers for display
    header_container = st.empty()
    progress_container = st.empty()
    content_container = st.empty()
    status_container = st.empty()

    # Initialize progress bar
    progress_bar = progress_container.progress(0)
    progress = 0

    # Initialize response accumulator
    full_response = ""

    # Display initial header
    header_container.markdown(f"### Generated {iac_format} Code")
    status_container.markdown("*Generating code... ▌*")

    try:
        # Process the streaming response
        for event in response_stream.get("body"):
            if "chunk" in event:
                chunk = json.loads(event["chunk"]["bytes"].decode())
                if "delta" in chunk and "text" in chunk["delta"]:
                    chunk_text = chunk["delta"]["text"]
                    if chunk_text:
                        # Accumulate response
                        full_response += chunk_text

                        # Update progress
                        progress = min(progress + 2, 99)
                        progress_bar.progress(progress)

                        # Small delay to make the streaming visible
                        time.sleep(0.01)  # noqa: arbitrary-sleep

        # Final updates
        progress_bar.progress(100)
        status_container.markdown("*Code generation complete ✓*")
        progress_container.empty()
        
        # Extract code from markdown code blocks
        code_pattern = r'```(?:\w+)?\s*\n(.*?)\n```'
        code_matches = re.findall(code_pattern, full_response, re.DOTALL)
        
        if code_matches:
            # Extract the actual code (first code block)
            extracted_code = code_matches[0].strip()
            
            # Split response into parts: before code, code, after code
            parts = re.split(code_pattern, full_response, maxsplit=1, flags=re.DOTALL)
            
            # Render markdown content before code
            if parts[0].strip():
                st.markdown(parts[0].strip())
            
            # Display code with syntax highlighting
            st.code(extracted_code, language=IAC_FORMATS.get(iac_format))
            
            # Render markdown content after code (if any)
            if len(parts) > 2 and parts[2].strip():
                st.markdown(parts[2].strip())
            
            # Add download button
            st.download_button(
                label="📥 Download Code",
                data=extracted_code,
                file_name=f"infrastructure.{IAC_FORMATS.get(iac_format)}",
                mime="text/plain",
            )
            
            return extracted_code
        else:
            # No code blocks found, render as markdown
            st.markdown(full_response)
            return full_response

    except Exception as e:
        status_container.error(f"Error during code generation: {str(e)}")
        return None


def run_validation(code: str, iac_format: str):
    """
    Run validation on generated code and store results in session state.
    
    Args:
        code: The generated IaC code
        iac_format: The format of the code (e.g., "CloudFormation", "Terraform")
    """
    logger.info(f"Starting validation for {iac_format} code")
    
    with st.spinner("🔍 Validating generated code..."):
        try:
            # Use validation configuration from session state
            config = st.session_state.validation_config
            
            # Initialize orchestrator
            orchestrator = ValidationOrchestrator(config)
            logger.debug(f"Initialized ValidationOrchestrator with config: {config}")
            
            # Map UI format names to validator format names
            format_mapping = {
                "CloudFormation": "cloudformation",
                "Terraform": "terraform",
                "AWS CDK (Python)": "cdk",
                "AWS CDK (TypeScript)": "cdk",
                "AWS CDK (Java)": "cdk",
            }
            
            validator_format = format_mapping.get(iac_format, iac_format.lower())
            logger.info(f"Mapped UI format '{iac_format}' to validator format '{validator_format}'")
            
            # Run validation
            start_time = datetime.now()
            report = orchestrator.validate(code, validator_format)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Store report in session state
            st.session_state.validation_report = report
            
            logger.info(f"Validation completed in {execution_time:.2f} seconds")
            logger.info(f"Validation results: {report.total_issues} issues found, "
                       f"readiness score: {report.readiness_score.overall_score:.0f}/100, "
                       f"status: {report.readiness_score.status}")
            
            st.success("✅ Validation complete!")
            
        except Exception as e:
            logger.error(f"Validation failed with error: {str(e)}", exc_info=True)
            st.error(f"❌ Validation failed: {str(e)}")
            st.session_state.validation_report = None





def render_validation_settings():
    """
    Render validation configuration settings in the sidebar.
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Validation Settings")
    
    # Auto-validation toggle
    auto_validate = st.sidebar.checkbox(
        "Automatic Validation",
        value=st.session_state.auto_validate,
        help="Automatically validate code after generation"
    )
    st.session_state.auto_validate = auto_validate
    
    # Show logs toggle
    show_logs = st.sidebar.checkbox(
        "Show Validation Logs",
        value=st.session_state.show_logs,
        help="Display detailed validation logs for troubleshooting"
    )
    st.session_state.show_logs = show_logs
    
    # Log level selector (only show if logs are enabled)
    if show_logs:
        log_level = st.sidebar.selectbox(
            "Log Level",
            options=["INFO", "DEBUG", "WARNING", "ERROR"],
            index=0,
            help="Set the minimum log level to display"
        )
        
        # Update log handler level
        if "log_handler" in st.session_state:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR
            }
            st.session_state.log_handler.setLevel(level_map.get(log_level, logging.INFO))
            
            # Also update the root logger level for validators
            logging.getLogger('validators').setLevel(level_map.get(log_level, logging.INFO))
    
    with st.sidebar.expander("Validation Categories", expanded=False):
        # Syntax validation
        enable_syntax = st.checkbox(
            "Syntax Validation",
            value=st.session_state.validation_config.enable_syntax_validation,
            help="Check for syntax errors and template validity"
        )
        
        # Security scanning
        enable_security = st.checkbox(
            "Security Scanning",
            value=st.session_state.validation_config.enable_security_scanning,
            help="Scan for security vulnerabilities and misconfigurations"
        )
        
        # Best practices
        enable_best_practices = st.checkbox(
            "Best Practices",
            value=st.session_state.validation_config.enable_best_practices,
            help="Check compliance with IaC best practices"
        )
        
        # Dry run validation
        enable_dry_run = st.checkbox(
            "Dry-Run Validation",
            value=st.session_state.validation_config.enable_dry_run,
            help="Verify deployment readiness with dry-run checks"
        )
    
    with st.sidebar.expander("Security Thresholds", expanded=False):
        # Max critical issues
        max_critical = st.number_input(
            "Max Critical Issues",
            min_value=0,
            max_value=10,
            value=st.session_state.validation_config.max_critical_security_issues,
            help="Maximum allowed critical security issues (0 = none allowed)"
        )
        
        # Max high issues
        max_high = st.number_input(
            "Max High Issues",
            min_value=0,
            max_value=20,
            value=st.session_state.validation_config.max_high_security_issues,
            help="Maximum allowed high severity security issues"
        )
    
    with st.sidebar.expander("Advanced Settings", expanded=False):
        # Timeout
        timeout = st.number_input(
            "Validation Timeout (seconds)",
            min_value=30,
            max_value=600,
            value=st.session_state.validation_config.validation_timeout_seconds,
            help="Maximum time allowed for validation to complete"
        )
        
        # AWS region
        aws_region = st.text_input(
            "AWS Region",
            value=st.session_state.validation_config.aws_region,
            help="AWS region for dry-run validation"
        )
        
        # Use AWS validation
        use_aws = st.checkbox(
            "Use AWS API Validation",
            value=st.session_state.validation_config.use_aws_validation,
            help="Use AWS CloudFormation API for template validation"
        )
    
    # Apply settings button
    if st.sidebar.button("💾 Apply Settings", use_container_width=True):
        # Update validation config
        st.session_state.validation_config = ValidationConfig(
            enable_syntax_validation=enable_syntax,
            enable_security_scanning=enable_security,
            enable_best_practices=enable_best_practices,
            enable_dry_run=enable_dry_run,
            max_critical_security_issues=max_critical,
            max_high_security_issues=max_high,
            validation_timeout_seconds=timeout,
            aws_region=aws_region,
            use_aws_validation=use_aws,
            checkov_skip_checks=st.session_state.validation_config.checkov_skip_checks,
            cfn_lint_ignore_checks=st.session_state.validation_config.cfn_lint_ignore_checks
        )
        
        # Save to config file
        try:
            save_config(st.session_state.validation_config)
            st.sidebar.success("✅ Settings saved!")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to save settings: {str(e)}")
    
    # Reset to defaults button
    if st.sidebar.button("🔄 Reset to Defaults", use_container_width=True):
        st.session_state.validation_config = load_config()
        st.sidebar.success("✅ Settings reset to defaults!")
        st.rerun()


def render_validation_logs():
    """
    Render validation logs in the UI for troubleshooting.
    """
    if not st.session_state.show_logs:
        return
    
    st.markdown("---")
    st.markdown("## 📋 Validation Logs")
    
    # Get logs from handler
    if "log_handler" in st.session_state:
        logs = st.session_state.log_handler.get_logs()
        
        if not logs:
            st.info("No validation logs available yet. Logs will appear after running validation.")
            return
        
        # Add clear logs button
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ Clear Logs", use_container_width=True):
                st.session_state.log_handler.clear_logs()
                st.rerun()
        
        # Display logs in a container with color coding
        log_container = st.container()
        with log_container:
            for log_entry in reversed(logs):  # Show most recent first
                timestamp = log_entry['timestamp'].strftime('%H:%M:%S')
                level = log_entry['level']
                message = log_entry['message']
                
                # Color code by log level
                if level == 'ERROR' or level == 'CRITICAL':
                    st.markdown(f"🔴 `{timestamp}` **{level}**: {message}")
                elif level == 'WARNING':
                    st.markdown(f"🟡 `{timestamp}` **{level}**: {message}")
                elif level == 'INFO':
                    st.markdown(f"🔵 `{timestamp}` **{level}**: {message}")
                else:  # DEBUG
                    st.markdown(f"⚪ `{timestamp}` **{level}**: {message}")





def main():
    initialize_session_state()

    # Application header
    st.title(f":blue[{APP_TITLE}]")

    # Sidebar setup
    with st.sidebar:
        st.header("Upload & Input")
        uploaded_file = st.file_uploader("Choose a file")
        text_input = st.text_area(
            "Enter additional details regarding architecture here"
        )

        if uploaded_file:
            if st.button("Generate Questions"):
                st.session_state.questions = generate_questions(
                    uploaded_file, st.session_state.context_history, text_input
                )

    # Question and response handling
    if st.session_state.questions:
        with st.sidebar.expander("Answer Questions", expanded=True):
            submit, responses, iac_format, additional_notes = create_response_form(
                st.session_state.questions
            )
        
        # Render validation settings in sidebar after questions
        render_validation_settings()

        if submit:
            st.sidebar.success("Responses submitted!")
            qa_string = "\n".join(
                f"{q.strip()}? Answer:- {responses.get(f'response_{i}', '')}"
                for i, q in enumerate(st.session_state.questions)
            )

            # Create code display containers
            # code_tab = st.tabs(["Generated Code"])

            with st.spinner(f"Generating {iac_format} code..."):
                # Get the response iterator from cfn_generation
                response_stream = get_bedrock_response_stream(
                    uploaded_file,
                    qa_string,
                    st.session_state.context_history,
                    iac_format,
                    additional_notes,
                )

                if response_stream:
                    generated_code = stream_code_display(iac_format, response_stream)

                if generated_code:
                    st.session_state.cfn_code = generated_code
                    st.session_state.generated_code = generated_code
                    st.session_state.selected_iac_format = iac_format
                    
                    # Run validation after code generation if auto-validation is enabled
                    if st.session_state.auto_validate:
                        run_validation(generated_code, iac_format)
                    else:
                        st.info("ℹ️ Automatic validation is disabled. Use the 'Re-validate Code' button to validate manually.")
    
    # Display validation results if available
    if st.session_state.validation_report:
        ValidationResultsPanel.render(st.session_state.validation_report)
        
        # Display validation logs if enabled
        render_validation_logs()


if __name__ == "__main__":
    main()
