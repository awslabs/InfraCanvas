#!/usr/bin/env python3
from aws_cdk import (
    App,
    Stack,
    Environment,
    Tags,
    aws_s3 as s3,
    aws_ec2 as ec2,
    RemovalPolicy
)
from constructs import Construct


class ValidStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket with encryption and public access block
        bucket = s3.Bucket(
            self,
            "ExampleBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True
        )
        
        Tags.of(bucket).add("Environment", "dev")
        Tags.of(bucket).add("ManagedBy", "CDK")

        # VPC with proper configuration
        vpc = ec2.Vpc(
            self,
            "MainVPC",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )
        
        Tags.of(vpc).add("Name", "main-vpc")


app = App()
ValidStack(
    app,
    "ValidStack",
    env=Environment(
        account="123456789012",
        region="us-east-1"
    )
)
app.synth()
