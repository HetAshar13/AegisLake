"""
AegisLake Databricks Job Task: dbt Kimball Marts Runner
Executes dbt compile, dbt run, and dbt test against the Unity Catalog Delta Lake warehouse.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd: list[str], cwd: Path) -> int:
    """Executes a command and streams output to stdout."""
    print(f"[AegisLake DAB Task] Executing: {' '.join(cmd)} in {cwd}")
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8"
    )
    for line in iter(process.stdout.readline, ""):
        print(line, end="")
    process.stdout.close()
    return process.wait()


def main():
    repo_root = Path(__file__).resolve().parent.parent
    dbt_dir = repo_root / "aegis_dbt"

    print("==================================================================")
    print(" AegisLake Databricks Workflow: dbt Kimball Dimensional Modeling ")
    print("==================================================================")

    # 1. dbt deps (ensure dbt packages are ready)
    ret = run_command(["dbt", "deps"], cwd=dbt_dir)
    if ret != 0:
        print("Warning: dbt deps completed with returncode", ret)

    # 2. dbt run (build star schema models)
    ret = run_command(["dbt", "run", "--profiles-dir", "."], cwd=dbt_dir)
    if ret != 0:
        print("ERROR: dbt run failed!")
        sys.exit(ret)

    # 3. dbt test (verify Great Expectations & balanced ledger invariants)
    ret = run_command(["dbt", "test", "--profiles-dir", "."], cwd=dbt_dir)
    if ret != 0:
        print("ERROR: dbt test failed! Invariant check breached.")
        sys.exit(ret)

    print("==================================================================")
    print(" SUCCESS: All dbt Kimball models and invariant tests VERIFIED!   ")
    print("==================================================================")


if __name__ == "__main__":
    main()
