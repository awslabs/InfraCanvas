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
  region = var.aws_region
}

# Missing variable declaration
# variable "aws_region" is referenced but not defined

resource "aws_s3_bucket" "broken" {
  bucket = "test-bucket"
  
  # Invalid attribute
  invalid_attribute = "value"
  
  # Missing closing brace for tags
  tags = {
    Name = "Broken Bucket"
    # Missing closing brace
}

resource "aws_instance" "broken_instance" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
  
  # Reference to non-existent resource
  subnet_id = aws_subnet.nonexistent.id
  
  # Invalid block structure
  network_interface
    device_index = 0
  }
}

# Duplicate resource name
resource "aws_s3_bucket" "broken" {
  bucket = "duplicate-name"
}

# Invalid resource type
resource "aws_invalid_resource" "test" {
  property = "value"
}

output "broken_output" {
  # Reference to non-existent resource attribute
  value = aws_s3_bucket.nonexistent.arn
}
