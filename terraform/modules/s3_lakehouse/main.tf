# =====================================================================
# AWS KMS Customer-Managed Key (CMK) with Automatic Key Rotation
# =====================================================================

resource "aws_kms_key" "lakehouse_key" {
  description             = "AegisLake Financial Lakehouse Customer-Managed Encryption Key"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "${var.project_name}-kms-cmk-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    Compliance  = "SOX-404-EU-DORA"
  }
}

resource "aws_kms_alias" "lakehouse_key_alias" {
  name          = "alias/${var.project_name}-lakehouse-${var.environment}"
  target_key_id = aws_kms_key.lakehouse_key.key_id
}

# =====================================================================
# S3 Financial Lakehouse Bucket
# =====================================================================

resource "aws_s3_bucket" "lakehouse_bucket" {
  bucket = "${var.project_name}-lakehouse-${var.environment}-${var.aws_region}"

  tags = {
    Name        = "${var.project_name}-lakehouse-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
    DataLayer   = "Medallion-Lakehouse"
    Compliance  = "SOX-404-EU-DORA"
  }
}

# Enforce BucketOwnerEnforced to disable legacy S3 ACLs and take full ownership of all third-party uploads
resource "aws_s3_bucket_ownership_controls" "ownership" {
  bucket = aws_s3_bucket.lakehouse_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Complete Public Access Block (Zero Public Exposure)
resource "aws_s3_bucket_public_access_block" "public_block" {
  bucket = aws_s3_bucket.lakehouse_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Default Server-Side Encryption with Customer-Managed KMS Key (SSE-KMS)
resource "aws_s3_bucket_server_side_encryption_configuration" "encryption" {
  bucket = aws_s3_bucket.lakehouse_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.lakehouse_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

# S3 Versioning for Regulatory Audit Trail & Immutable Financial History
resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.lakehouse_bucket.id

  versioning_configuration {
    status = var.enable_versioning ? "Enabled" : "Suspended"
  }
}

# Medallion Architecture S3 Prefixes (Bronze, Silver, Gold, Quarantine)
resource "aws_s3_object" "medallion_prefixes" {
  for_each = toset([
    "bronze/",
    "silver/",
    "gold/",
    "quarantine/"
  ])

  bucket       = aws_s3_bucket.lakehouse_bucket.id
  key          = each.value
  content_type = "application/x-directory"
}

# S3 Lifecycle Policy: Transition older transaction versions to Glacier after 90 days
resource "aws_s3_bucket_lifecycle_configuration" "lakehouse_lifecycle" {
  bucket = aws_s3_bucket.lakehouse_bucket.id

  rule {
    id     = "archive-historical-audit-snapshots"
    status = "Enabled"

    filter {
      prefix = ""
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}
