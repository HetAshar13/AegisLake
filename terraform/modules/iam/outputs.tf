output "role_name" {
  description = "The name of the IAM role for Spark workers"
  value       = aws_iam_role.spark_worker_role.name
}

output "role_arn" {
  description = "The ARN of the IAM role for Spark workers"
  value       = aws_iam_role.spark_worker_role.arn
}

output "instance_profile_arn" {
  description = "The ARN of the IAM instance profile"
  value       = aws_iam_instance_profile.spark_worker_instance_profile.arn
}

output "policy_arn" {
  description = "The ARN of the scoped lakehouse access policy"
  value       = aws_iam_policy.lakehouse_access_policy.arn
}
