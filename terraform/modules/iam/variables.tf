variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "lakehouse_bucket_arn" {
  description = "ARN of the S3 lakehouse bucket"
  type        = string
}

variable "lakehouse_bucket_id" {
  description = "Name/ID of the S3 lakehouse bucket"
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the KMS encryption key"
  type        = string
}
