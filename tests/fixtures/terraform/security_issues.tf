terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Unencrypted S3 bucket
resource "aws_s3_bucket" "unencrypted" {
  bucket = "unencrypted-bucket"
  # Missing encryption configuration
  # Missing public access block
}

# Overly permissive IAM policy
resource "aws_iam_role" "overly_permissive" {
  name = "overly-permissive-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "wildcard_policy" {
  name = "wildcard-policy"
  role = aws_iam_role.overly_permissive.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "*"  # Wildcard action
        Effect   = "Allow"
        Resource = "*"  # Wildcard resource
      }
    ]
  })
}

# Security group with open ingress
resource "aws_security_group" "open_sg" {
  name        = "open-security-group"
  description = "Security group with open access"
  vpc_id      = "vpc-12345678"

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to the world
  }

  ingress {
    description = "RDP from anywhere"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Open to the world
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS instance without encryption
resource "aws_db_instance" "unencrypted_db" {
  identifier           = "unencrypted-db"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  username             = "admin"
  # password intentionally omitted; use a secrets manager reference / variable instead of a hardcoded value
  publicly_accessible  = true  # Publicly accessible
  skip_final_snapshot  = true
  # Missing storage_encrypted = true
}

# EC2 instance with public IP and no encryption
resource "aws_instance" "insecure_instance" {
  ami                         = "ami-0c55b159cbfafe1f0"
  instance_type               = "t2.micro"
  associate_public_ip_address = true
  
  # No encryption for root volume
  root_block_device {
    volume_size = 20
    # Missing encrypted = true
  }

  # Metadata service v1 (insecure)
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "optional"  # Should be "required" for IMDSv2
  }
}
