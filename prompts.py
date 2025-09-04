# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

def get_initial_prompt(file, textinput):
    return f'''You are an DevOps SME specialized in Amazon Web Services (AWS) Cloud infrastructure. Please analyze the uploaded file consisting an architecture diagram, capture the key elements and relationships within the AWS Cloud portion of the diagram. Specifically, focus on the following: 
1.Identify and list all components in the diagram. 
2.	Categorize the components according to this taxonomy: 
- Boundaries: Large-scale divisions (e.g., AWS Cloud, Availability Zones) 
– Group Elements: Logical groupings of elements (e.g., VPC, AWS accounts) 
– Elements: Individual components (e.g., specific AWS services) 
– Connections: Lines or arrows between elements 
– Legends: Keys explaining symbols or colors used
3.	Describe the connections and relationships between the different AWS components, including the directionality and type of communication (e.g., API Gateway invokes Lambda function).
4.	Determine the hierarchical structure of the diagram, noting how components relate to each other.
5.	Understand containment and overlaps:
a.	A group or boundary overlaps with another only if their borders intersect or cross each other.
b.	Elements or groups should only be listed as part of multiple groups/boundaries if those groups/boundaries actually overlap.
c.	If a group is wholly contained within another group or boundary, it's considered nested, not overlapping.
6.	Note any specific attributes or configurations associated with each AWS resource (e.g., Lambda function runtime, API Gateway integration type).
7.	Highlight any elements or connections that appear to be outside the AWS Cloud boundary and mention that you will be ignoring those for now, focusing only on the components within the AWS Cloud.
8.	Once you get a high-level overview of the entire diagram, Based on the summary, generate a list of at maximum 10 essential questions which is specific to the services and that needs to be asked to the user before you can generate a cloud formation template code, cdk code or a terraform code for them. Do not attempt to generate any code at this stage; the goal is to analyze the architecture and fill the gaps on missing information. It is essential to ask only the question which is relevant to this architecture.
    Do not attempt to ask unnecessary and generic questions of the services that are not there in the architecture and which is irrelevant. Display these questions in a numbered list where each questions ends with a ?
    Here is the architecture file: {file} 
    Apart from the XML file here is an additional information regarding the architecture file given by the user.
    Information:- {textinput}

Do not show your analysis, only respond back with the questions.
'''


def get_final_prompt(file, additional_notes, iac_format, qa_string, context_history):
    return f'''You are an DevOps SME specialized in Amazon Web Services (AWS) Cloud infrastructure. Please analyze the uploaded file consisting an architecture diagram, capture the key elements and relationships within the AWS Cloud portion of the diagram. Specifically, focus on the following: 

Based on the following Q&A and context, generate {iac_format} code.
        Architecture file: {file}
        Context: {context_history}
        Q&A: {qa_string}
        Additional Requirements: {additional_notes}
        
        Please generate complete a valid {iac_format} code that implements the architecture described above.
        Include:
        1. All necessary resources and their configurations
        2. Best practices for security and scalability
        3. Proper resource naming and tagging
        4. Required IAM roles and policies
        5. Appropriate resource dependencies
        
        Do not generate code for any resources that is not present in the architecture diagram
'''


__all__ = ['get_initial_prompt', 'get_final_prompt']
