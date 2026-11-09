variable "environment" {
  description = "Deployment environment (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project identifier used in naming and resource tags"
  type        = string
  default     = "aegislake"
}

variable "aws_region" {
  description = "Target AWS Region"
  type        = string
  default     = "eu-west-1"
}

variable "enable_versioning" {
  description = "Enable S3 bucket versioning for financial audit retention"
  type        = bool
  default     = true
}
