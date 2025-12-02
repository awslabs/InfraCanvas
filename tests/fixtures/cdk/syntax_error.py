#!/usr/bin/env python3
from aws_cdk import (
    App,
    Stack,
    aws_s3 as s3,
    aws_ec2 as ec2
)
from constructs import Construct


class BrokenStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Missing required parameter
        bucket = s3.Bucket(
            self,
            # Missing required id parameter
        )
        
        # Invalid property name
        vpc = ec2.Vpc(
            self,
            "VPC",
            invalid_property="value",  # This property doesn't exist
            max_azs=2
        )
        
        # Reference to undefined variable
        security_group = ec2.SecurityGroup(
            self,
            "SG",
            vpc=undefined_vpc  # This variable doesn't exist
        )
        
        # Syntax error - missing closing parenthesis
        instance = ec2.Instance(
            self,
            "Instance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T2,
                ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            vpc=vpc
        # Missing closing parenthesis


# Missing app.synth() call
app = App()
BrokenStack(app, "BrokenStack"
# Missing closing parenthesis
