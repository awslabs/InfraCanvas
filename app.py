# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import time
import sys

import boto3
import streamlit as st
from botocore.config import Config
from botocore.exceptions import ClientError

from prompts import get_initial_prompt, get_final_prompt

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
model_id = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
native_request = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 10000,
    "temperature": 0.2,
    "messages": [],
}


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
            }
        )


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
    # Create containers for code display
    header_container = st.empty()
    progress_container = st.empty()
    code_container = st.empty()
    status_container = st.empty()

    # Initialize progress bar
    progress_bar = progress_container.progress(0)
    progress = 0

    # Initialize code accumulator
    full_code = ""

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
                        # Accumulate code
                        full_code += chunk_text

                        # Update the display with syntax highlighting
                        language = IAC_FORMATS.get(iac_format)
                        code_container.code(full_code + "▌", language=language)

                        # Update progress
                        progress = min(progress + 2, 99)
                        progress_bar.progress(progress)

                        # Small delay to make the streaming visible (intentional for UX)
                        time.sleep(0.01)  # noqa: arbitrary-sleep

        # Final updates
        progress_bar.progress(100)
        status_container.markdown("*Code generation complete ✓*")
        code_container.code(full_code, language=IAC_FORMATS.get(iac_format))

        # Add download button after code generation
        st.download_button(
            label="📥 Download Code",
            data=full_code,
            file_name=f"infrastructure.{IAC_FORMATS.get(iac_format)}",
            mime="text/plain",
        )

        return full_code

    except Exception as e:
        status_container.error(f"Error during code generation: {str(e)}")
        return None


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
        with st.sidebar.expander("Answer Questions"):
            submit, responses, iac_format, additional_notes = create_response_form(
                st.session_state.questions
            )

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


if __name__ == "__main__":
    main()
