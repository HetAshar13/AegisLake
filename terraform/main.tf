terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # For production, an S3 backend with DynamoDB state locking is configured here:
  # backend "s3" {
  #   bucket         = "aegislake-terraform-state-prod"
  #   key            = "lakehouse/terraform.tfstate"
  #   region         = "eu-west-1"
  #   dynamodb_table = "aegislake-terraform-locks"
  #   encrypt        = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AegisLake"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Owner       = "Het Hargovind Ashar"
      Compliance  = "SOX-404-EU-DORA"
    }
  }
}

# =====================================================================
# S3 Lakehouse & Customer-Managed KMS Key Module
# =====================================================================

module "s3_lakehouse" {
  source = "./modules/s3_lakehouse"

  environment       = var.environment
  project_name      = var.project_name
  aws_region        = var.aws_region
  enable_versioning = var.enable_versioning
}

# =====================================================================
# IAM Least-Privilege Compute Worker Module
# =====================================================================

module "iam" {
  source = "./modules/iam"

  environment          = var.environment
  project_name         = var.project_name
  lakehouse_bucket_arn = module.s3_lakehouse.bucket_arn
  lakehouse_bucket_id  = module.s3_lakehouse.bucket_id
  kms_key_arn          = module.s3_lakehouse.kms_key_arn
}
