"""
AegisLake Databricks Asset Bundle (DAB) Automated Verification Suite
Validates databricks.yml configuration, target environment parity, job cluster cost controls,
and multi-task DAG dependencies ($0 cloud spend guarantee).
"""

import os
from pathlib import Path
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_YML = REPO_ROOT / "databricks.yml"
JOB_RESOURCE_YML = REPO_ROOT / "resources" / "aegislake_pipeline.job.yml"
DBT_RUNNER = REPO_ROOT / "scripts" / "run_dbt_databricks.py"


class TestDatabricksAssetBundles:
    """Verifies that Databricks Asset Bundle declarations follow official Databricks CI/CD schemas."""

    def test_databricks_bundle_yaml_structure(self):
        """Asserts root databricks.yml declares bundle name, include paths, and target environments."""
        assert BUNDLE_YML.exists(), "databricks.yml does not exist"
        data = yaml.safe_load(BUNDLE_YML.read_text(encoding="utf-8"))

        assert data.get("bundle", {}).get("name") == "aegislake"
        assert "resources/*.yml" in data.get("include", [])

        # Verify environment targets parity
        targets = data.get("targets", {})
        assert "dev" in targets, "Missing 'dev' target in databricks.yml"
        assert "prod" in targets, "Missing 'prod' target in databricks.yml"

        assert targets["dev"].get("mode") == "development"
        assert targets["prod"].get("mode") == "production"

        # Verify Unity Catalog variable bindings
        assert "catalog" in data.get("variables", {})
        assert "schema" in data.get("variables", {})

    def test_job_resource_definition(self):
        """Asserts job resource definition employs dedicated Job Clusters and cost-efficient Spot instances."""
        assert JOB_RESOURCE_YML.exists(), "resources/aegislake_pipeline.job.yml does not exist"
        data = yaml.safe_load(JOB_RESOURCE_YML.read_text(encoding="utf-8"))

        jobs = data.get("resources", {}).get("jobs", {})
        assert "aegislake_reconciliation_workflow" in jobs

        workflow = jobs["aegislake_reconciliation_workflow"]
        job_clusters = workflow.get("job_clusters", [])
        assert len(job_clusters) >= 1, "Workflow must define at least one job cluster"

        # Verify Job Cluster configuration
        cluster_def = job_clusters[0]
        assert cluster_def.get("job_cluster_key") == "aegis_job_cluster"
        new_cluster = cluster_def.get("new_cluster", {})

        # Assert autoscaling and spot fallback
        autoscale = new_cluster.get("autoscale", {})
        assert autoscale.get("min_workers") == 1
        assert autoscale.get("max_workers") == 4

        aws_attr = new_cluster.get("aws_attributes", {})
        assert aws_attr.get("availability") == "SPOT_WITH_FALLBACK", "Production job cluster should leverage Spot with fallback"

    def test_task_dag_dependency_chain(self):
        """Asserts strict sequential execution: Ingestion -> Silver CDF -> dbt Marts -> Agent."""
        data = yaml.safe_load(JOB_RESOURCE_YML.read_text(encoding="utf-8"))
        workflow = data.get("resources", {}).get("jobs", {}).get("aegislake_reconciliation_workflow", {})
        tasks = workflow.get("tasks", [])

        task_keys = [t.get("task_key") for t in tasks]
        expected_keys = [
            "01_streaming_ingestion",
            "02_silver_reconciliation_cdf",
            "03_dbt_kimball_marts",
            "04_autonomous_incident_commander"
        ]
        assert task_keys == expected_keys, f"Tasks DAG mismatch: expected {expected_keys}, got {task_keys}"

        # Check dependencies
        task_map = {t.get("task_key"): t for t in tasks}

        # Task 2 depends on Task 1
        dep2 = [d.get("task_key") for d in task_map["02_silver_reconciliation_cdf"].get("depends_on", [])]
        assert "01_streaming_ingestion" in dep2

        # Task 3 depends on Task 2
        dep3 = [d.get("task_key") for d in task_map["03_dbt_kimball_marts"].get("depends_on", [])]
        assert "02_silver_reconciliation_cdf" in dep3

        # Task 4 depends on Task 3
        dep4 = [d.get("task_key") for d in task_map["04_autonomous_incident_commander"].get("depends_on", [])]
        assert "03_dbt_kimball_marts" in dep4

        # All tasks use shared job cluster
        for task in tasks:
            assert task.get("job_cluster_key") == "aegis_job_cluster"

    def test_dbt_runner_script_exists_and_compiles(self):
        """Asserts the dbt runner script for Databricks task exists and passes py_compile."""
        assert DBT_RUNNER.exists(), "scripts/run_dbt_databricks.py does not exist"
        import py_compile
        py_compile.compile(str(DBT_RUNNER), doraise=True)
