output "bucket_id" {
  description = "The name of the S3 lakehouse bucket"
  value       = aws_s3_bucket.lakehouse_bucket.id
}

output "bucket_arn" {
  description = "The ARN of the S3 lakehouse bucket"
  value       = aws_s3_bucket.lakehouse_bucket.arn
}

output "kms_key_arn" {
  description = "The ARN of the customer-managed KMS key"
  value       = aws_kms_key.lakehouse_key.arn
}

output "kms_key_id" {
  description = "The ID of the customer-managed KMS key"
  value       = aws_kms_key.lakehouse_key.key_id
}
