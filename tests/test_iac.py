"""
AegisLake Infrastructure-as-Code (IaC) Automated Verification Suite
Validates Terraform security policies, KMS key rotation, S3 bucket ownership,
and least-privilege IAM scoping without incurring AWS cloud spend ($0 cost guarantee).
"""

import os
import re
from pathlib import Path
import pytest


TERRAFORM_DIR = Path(__file__).resolve().parent.parent / "terraform"


class TestTerraformLakehouseArchitecture:
    """Verifies that all declarative Terraform files strictly adhere to enterprise banking standards."""

    def test_terraform_file_hierarchy(self):
        """Asserts all expected root and module Terraform files exist."""
        expected_files = [
            TERRAFORM_DIR / "main.tf",
            TERRAFORM_DIR / "variables.tf",
            TERRAFORM_DIR / "outputs.tf",
            TERRAFORM_DIR / "terraform.tfvars.example",
            TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf",
            TERRAFORM_DIR / "modules" / "s3_lakehouse" / "variables.tf",
            TERRAFORM_DIR / "modules" / "s3_lakehouse" / "outputs.tf",
            TERRAFORM_DIR / "modules" / "iam" / "main.tf",
            TERRAFORM_DIR / "modules" / "iam" / "variables.tf",
            TERRAFORM_DIR / "modules" / "iam" / "outputs.tf",
        ]
        for tf_file in expected_files:
            assert tf_file.exists(), f"Missing required Terraform file: {tf_file}"

    def test_kms_cmk_key_rotation_enabled(self):
        """Asserts customer-managed KMS key mandates automatic 365-day rotation (SOX/DORA requirement)."""
        s3_main = (TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf").read_text(encoding="utf-8")
        assert "resource \"aws_kms_key\"" in s3_main
        assert "enable_key_rotation     = true" in s3_main or "enable_key_rotation = true" in s3_main
        assert "deletion_window_in_days = 30" in s3_main

    def test_s3_bucket_owner_enforced(self):
        """Asserts legacy S3 ACLs are completely disabled via BucketOwnerEnforced."""
        s3_main = (TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf").read_text(encoding="utf-8")
        assert "resource \"aws_s3_bucket_ownership_controls\"" in s3_main
        assert 'object_ownership = "BucketOwnerEnforced"' in s3_main

    def test_s3_complete_public_access_block(self):
        """Asserts all four S3 public access block vectors are strictly enforced."""
        s3_main = (TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf").read_text(encoding="utf-8")
        assert "resource \"aws_s3_bucket_public_access_block\"" in s3_main
        for flag in ["block_public_acls", "block_public_policy", "ignore_public_acls", "restrict_public_buckets"]:
            match = re.search(rf"{flag}\s*=\s*true", s3_main)
            assert match, f"Public access block missing or not set to true: {flag}"

    def test_s3_server_side_kms_encryption(self):
        """Asserts S3 bucket applies SSE-KMS with customer key by default."""
        s3_main = (TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf").read_text(encoding="utf-8")
        assert "resource \"aws_s3_bucket_server_side_encryption_configuration\"" in s3_main
        assert 'sse_algorithm     = "aws:kms"' in s3_main or 'sse_algorithm = "aws:kms"' in s3_main
        assert "bucket_key_enabled = true" in s3_main

    def test_medallion_prefixes_provisioned(self):
        """Asserts Bronze, Silver, Gold, and Quarantine prefixes are systematically declared."""
        s3_main = (TERRAFORM_DIR / "modules" / "s3_lakehouse" / "main.tf").read_text(encoding="utf-8")
        for prefix in ["bronze/", "silver/", "gold/", "quarantine/"]:
            assert f'"{prefix}"' in s3_main, f"Missing Medallion storage prefix: {prefix}"

    def test_iam_least_privilege_scoping(self):
        """Asserts IAM policy does not use dangerous wildcards and strictly scopes access to Medallion prefixes."""
        iam_main = (TERRAFORM_DIR / "modules" / "iam" / "main.tf").read_text(encoding="utf-8")
        
        # Deny wildcard s3 on all resources
        assert '"s3:*"' not in iam_main, "Security violation: Wildcard s3:* detected in IAM policy"
        assert 'resources = ["*"]' not in iam_main, "Security violation: Global wildcard resource detected"

        # Verify scoped prefix access
        for prefix in ["bronze/*", "silver/*", "gold/*", "quarantine/*"]:
            assert prefix in iam_main, f"IAM policy missing scoped prefix: {prefix}"

        # Verify KMS permissions scoped to CMK key
        assert "kms:GenerateDataKey" in iam_main
        assert "kms:Decrypt" in iam_main
        assert "resources = [var.kms_key_arn]" in iam_main
