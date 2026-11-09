output "lakehouse_bucket_name" {
  description = "Name of the provisioned financial Lakehouse S3 bucket"
  value       = module.s3_lakehouse.bucket_id
}

output "lakehouse_bucket_arn" {
  description = "ARN of the provisioned financial Lakehouse S3 bucket"
  value       = module.s3_lakehouse.bucket_arn
}

output "kms_key_arn" {
  description = "ARN of the customer-managed KMS key"
  value       = module.s3_lakehouse.kms_key_arn
}

output "spark_worker_role_arn" {
  description = "ARN of the IAM role for PySpark & Databricks workers"
  value       = module.iam.role_arn
}

output "spark_worker_instance_profile_arn" {
  description = "ARN of the IAM instance profile for PySpark workers"
  value       = module.iam.instance_profile_arn
}
