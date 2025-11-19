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

# Missing tags
resource "aws_s3_bucket" "untagged" {
  bucket = "untagged-bucket"
  # Missing tags for resource management
}

# Poor naming convention
resource "aws_s3_bucket" "b1" {
  bucket = "mybucket"  # Non-descriptive name
}

# Hardcoded values instead of variables
resource "aws_instance" "hardcoded" {
  ami               = "ami-0c55b159cbfafe1f0"  # Hardcoded AMI
  instance_type     = "t2.micro"
  availability_zone = "us-east-1a"  # Hardcoded AZ
  subnet_id         = "subnet-12345678"  # Hardcoded subnet
}

# Missing lifecycle rules for important resources
resource "aws_db_instance" "important_db" {
  identifier          = "important-db"
  engine              = "postgres"
  engine_version      = "14"
  instance_class      = "db.t3.micro"
  allocated_storage   = 100
  username            = "admin"
  password            = "ChangeMe123!"
  storage_encrypted   = true
  skip_final_snapshot = true
  # Missing lifecycle { prevent_destroy = true } for important data
}

# Missing descriptions
variable "some_var" {
  type    = string
  default = "value"
  # Missing description
}

# No output descriptions
output "bucket_id" {
  value = aws_s3_bucket.b1.id
  # Missing description
}

# Missing provider version constraints
# Provider block should have version constraints

# Resource without proper error handling
resource "aws_s3_bucket" "no_error_handling" {
  bucket = "bucket-name-that-might-conflict"
  # No depends_on or lifecycle rules to handle conflicts
}
