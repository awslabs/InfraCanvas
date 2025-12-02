#!/usr/bin/env python3
from aws_cdk import (
    App,
    Stack,
    Environment,
    aws_s3 as s3,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_iam as iam,
    RemovalPolicy
)
from constructs import Construct


class InsecureStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Unencrypted S3 bucket with public access
        insecure_bucket = s3.Bucket(
            self,
            "InsecureBucket",
            # Missing encryption
            # Missing public access block
            public_read_access=True,  # Public access enabled
            removal_policy=RemovalPolicy.DESTROY
        )

        # VPC for other resources
        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=2
        )

        # Security group with open ingress
        open_sg = ec2.SecurityGroup(
            self,
            "OpenSecurityGroup",
            vpc=vpc,
            description="Security group with open access",
            allow_all_outbound=True
        )
        
        # Open SSH to the world
        open_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(22),
            "SSH from anywhere"
        )
        
        # Open RDP to the world
        open_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(3389),
            "RDP from anywhere"
        )

        # Unencrypted RDS database
        insecure_db = rds.DatabaseInstance(
            self,
            "InsecureDatabase",
            engine=rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_8_0
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            # Missing storage_encrypted=True
            publicly_accessible=True,  # Publicly accessible
            removal_policy=RemovalPolicy.DESTROY
        )

        # Overly permissive IAM role
        overly_permissive_role = iam.Role(
            self,
            "OverlyPermissiveRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ]
        )
        
        # Add wildcard policy
        overly_permissive_role.add_to_policy(
            iam.PolicyStatement(
                actions=["*"],
                resources=["*"],
                effect=iam.Effect.ALLOW
            )
        )

        # EC2 instance with public IP and no encryption
        insecure_instance = ec2.Instance(
            self,
            "InsecureInstance",
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T2,
                ec2.InstanceSize.MICRO
            ),
            machine_image=ec2.MachineImage.latest_amazon_linux(),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=open_sg,
            role=overly_permissive_role
            # Missing block device encryption
        )


app = App()
InsecureStack(
    app,
    "InsecureStack",
    env=Environment(
        account="123456789012",
        region="us-east-1"
    )
)
app.synth()
