variable "environment" {
  description = "Target deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Global project identifier"
  type        = string
  default     = "aegislake"
}

variable "aws_region" {
  description = "AWS region for Lakehouse deployment"
  type        = string
  default     = "eu-west-1"
}

variable "enable_versioning" {
  description = "Enable S3 bucket versioning for financial audit retention"
  type        = bool
  default     = true
}
