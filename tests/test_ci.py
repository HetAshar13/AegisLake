"""
AegisLake CI/CD Automated Verification Suite
Validates GitHub Actions workflow YAML configuration, quality gate jobs, and triggers.
"""

from pathlib import Path
import yaml
import pytest


CI_WORKFLOW = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "ci.yml"


class TestCICDPipeline:
    """Verifies that the GitHub Actions CI/CD configuration defines all required quality gates."""

    def test_workflow_file_exists_and_valid_yaml(self):
        """Asserts ci.yml exists and parses as valid YAML."""
        assert CI_WORKFLOW.exists(), ".github/workflows/ci.yml does not exist"
        data = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        assert "name" in data
        assert "jobs" in data

    def test_workflow_triggers_on_main(self):
        """Asserts workflow triggers on push and pull_request to main."""
        data = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        triggers = data.get("on") or data.get(True, {})
        assert "push" in triggers
        assert "pull_request" in triggers
        assert "main" in triggers["push"]["branches"]
        assert "main" in triggers["pull_request"]["branches"]

    def test_all_quality_gate_jobs_defined(self):
        """Asserts lint, test, dbt-validation, and deploy-dry-run jobs exist."""
        data = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        jobs = data.get("jobs", {})
        expected_jobs = ["lint", "test", "dbt-validation", "deploy-dry-run"]
        for j in expected_jobs:
            assert j in jobs, f"Missing required CI job: {j}"

    def test_test_job_installs_java_for_spark(self):
        """Asserts the test job sets up Java 17 for PySpark Catalyst execution."""
        data = yaml.safe_load(CI_WORKFLOW.read_text(encoding="utf-8"))
        test_job = data["jobs"]["test"]
        steps = test_job.get("steps", [])
        java_steps = [s for s in steps if "setup-java" in str(s.get("uses", ""))]
        assert len(java_steps) >= 1, "test job must include actions/setup-java for PySpark"
        assert java_steps[0].get("with", {}).get("java-version") == "17"
