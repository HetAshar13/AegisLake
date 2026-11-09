# =====================================================================
# IAM Assume Role Policy (Databricks / EC2 Worker Compute)
# =====================================================================

data "aws_iam_policy_document" "assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "spark_worker_role" {
  name               = "${var.project_name}-spark-worker-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json

  tags = {
    Name        = "${var.project_name}-spark-worker-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Role        = "Compute-Worker"
  }
}

# =====================================================================
# Least-Privilege Scoped Policy for Lakehouse Storage & KMS
# =====================================================================

data "aws_iam_policy_document" "lakehouse_access" {
  # 1. Bucket-Level Discovery & Metadata
  statement {
    sid    = "S3BucketListing"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation"
    ]
    resources = [var.lakehouse_bucket_arn]
  }

  # 2. Scoped Object Read/Write/Compaction on Medallion Prefixes ONLY
  statement {
    sid    = "S3MedallionPrefixAccess"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetObjectVersion"
    ]
    resources = [
      "${var.lakehouse_bucket_arn}/bronze/*",
      "${var.lakehouse_bucket_arn}/silver/*",
      "${var.lakehouse_bucket_arn}/gold/*",
      "${var.lakehouse_bucket_arn}/quarantine/*"
    ]
  }

  # 3. KMS Customer-Managed Key Decryption / Encryption for Lakehouse Data
  statement {
    sid    = "KMSLakehouseKeyAccess"
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt",
      "kms:Encrypt",
      "kms:DescribeKey"
    ]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_policy" "lakehouse_access_policy" {
  name        = "${var.project_name}-lakehouse-access-${var.environment}"
  description = "Least-privilege policy for AegisLake PySpark & Delta Lake compute workers"
  policy      = data.aws_iam_policy_document.lakehouse_access.json
}

resource "aws_iam_role_policy_attachment" "attach_lakehouse_policy" {
  role       = aws_iam_role.spark_worker_role.name
  policy_arn = aws_iam_policy.lakehouse_access_policy.arn
}

resource "aws_iam_instance_profile" "spark_worker_instance_profile" {
  name = "${var.project_name}-spark-worker-profile-${var.environment}"
  role = aws_iam_role.spark_worker_role.name
}
