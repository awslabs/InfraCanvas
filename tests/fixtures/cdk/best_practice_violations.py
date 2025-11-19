#!/usr/bin/env python3
from aws_cdk import (
    App,
    Stack,
    aws_s3 as s3,
    aws_ec2 as ec2,
    RemovalPolicy
)
from constructs import Construct


class PoorPracticesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Missing tags
        untagged_bucket = s3.Bucket(
            self,
            "UntaggedBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            # Missing tags
        )

        # Poor naming convention
        b1 = s3.Bucket(
            self,
            "b1",  # Non-descriptive construct ID
            bucket_name="mybucket",  # Non-descriptive bucket name
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # Hardcoded values
        vpc = ec2.Vpc(
            self,
            "HardcodedVPC",
            cidr="10.0.0.0/16",  # Hardcoded CIDR
            max_azs=2,
            nat_gateways=1
        )

        # Missing removal policy for important resources
        important_bucket = s3.Bucket(
            self,
            "ImportantBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=True
            # Missing removal_policy=RemovalPolicy.RETAIN
        )

        # Using default removal policy (RETAIN) without explicit declaration
        # This is implicit and not clear to readers
        another_bucket = s3.Bucket(
            self,
            "AnotherBucket",
            encryption=s3.BucketEncryption.S3_MANAGED
        )

        # No description for the stack
        # Stack should have a description parameter

        # Missing environment specification
        # Should specify account and region


# Missing environment configuration
app = App()
PoorPracticesStack(app, "PoorPracticesStack")
# Missing explicit env parameter
app.synth()
