"""Investigate and review a SQL repair in a disposable dbt project."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from difflib import unified_diff
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory

import duckdb

from aegis_agent.tools.lineage_parser import extract_column_lineage


FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "sql_repair"
MODEL = Path("models/payment_amounts.sql")
EXPECTED = [["card_eur", "EUR", 10000], ["card_jpy", "JPY", 10000]]
BROKEN_EXPRESSION = "case when currency = 'EUR' then amount_minor * 100 else amount_minor end"


def build_model(source: str) -> tuple[list, str]:
    """Build a fresh copy and read its output and actual compiled SQL."""
    with TemporaryDirectory(prefix="aegis-sql-repair-") as temp:
        project = Path(temp) / "project"
        shutil.copytree(FIXTURE, project)
        (project / MODEL).write_text(source, encoding="utf-8")
        # Inherited dbt options can redirect targets, artifacts or profiles.
        env = {key: value for key, value in os.environ.items() if not key.upper().startswith("DBT_")}
        env["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"
        result = subprocess.run(
            [
                sys.executable, "-c", "from dbt.cli.main import cli; cli()",
                "build", "--project-dir", ".", "--profiles-dir", ".", "--target", "local",
            ],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode:
            raise ValueError(f"dbt build failed:\n{result.stdout}\n{result.stderr}")
        compiled = project / "target" / "compiled" / "aegis_sql_repair" / MODEL
        with duckdb.connect(str(project / "demo.duckdb"), read_only=True) as db:
            rows = db.execute(
                "select case_id, currency, reported_minor from payment_amounts order by case_id"
            ).fetchall()
        return [list(row) for row in rows], compiled.read_text(encoding="utf-8")


def proposal_digest(candidate: str) -> str:
    """Bind the reviewed SQL to the checked-in inputs, profile and project."""
    snapshot = {
        p.relative_to(FIXTURE).as_posix(): p.read_text(encoding="utf-8")
        for p in FIXTURE.rglob("*") if p.is_file()
    }
    encoded = json.dumps({"fixture": snapshot, "candidate": candidate}, sort_keys=True)
    return sha256(encoded.encode()).hexdigest()


def validate_shadow(candidate: str, before: list) -> list:
    rows, _ = build_model(candidate)
    if rows != EXPECTED or rows == before or rows[1] != before[1]:
        raise ValueError("Shadow build did not fix the EUR row and preserve the comparison row.")
    return rows


def prepare(directory: Path) -> dict:
    if directory.exists():
        raise FileExistsError(f"Choose a fresh review directory: {directory}")
    source = (FIXTURE / MODEL).read_text(encoding="utf-8")
    before, compiled = build_model(source)
    if before != [["card_eur", "EUR", 1000000], EXPECTED[1]]:
        raise ValueError("The fixture did not reproduce the expected EUR conversion error.")
    lineage = extract_column_lineage(compiled, target_column="reported_minor")
    if (
        lineage["status"] != "SUCCESS"
        or "amount_minor" not in lineage["source_columns"]
        or "payment_input" not in lineage["upstream_tables"]
        or "amount_minor * 100" not in lineage["expression"]
        or source.count(BROKEN_EXPRESSION) != 1
    ):
        raise ValueError(f"Could not trace the expected compiled expression: {lineage}")

    # The source already supplies integer minor units. Keep the output in that unit.
    candidate = source.replace(BROKEN_EXPRESSION, "amount_minor", 1)
    shadow = validate_shadow(candidate, before)
    proposal = {
        "proposal_id": proposal_digest(candidate),
        "model": MODEL.as_posix(),
        "lineage": lineage,
        "before": before,
        "shadow": shadow,
        "diff": "".join(unified_diff(source.splitlines(True), candidate.splitlines(True), "before", "proposed")),
        "candidate": candidate,
        "status": "PENDING",
    }
    directory.mkdir(parents=True, exist_ok=False)
    with closing(sqlite3.connect(directory / "review.sqlite")) as db, db:
        db.execute("create table review (id integer primary key check (id = 1), receipt text not null)")
        db.execute("insert into review values (1, ?)", (json.dumps(proposal),))
    return proposal


def read_receipt(db: sqlite3.Connection) -> dict:
    row = db.execute("select receipt from review where id = 1").fetchone()
    if row is None:
        raise ValueError("This directory has no prepared review.")
    return json.loads(row[0])


def review(directory: Path, decision: str, reviewer: str, proposal_id: str) -> dict:
    if decision not in {"approve", "reject"} or not reviewer.strip():
        raise ValueError("Choose approve or reject and provide a reviewer name.")
    journal = (directory / "review.sqlite").resolve().as_uri()
    with closing(sqlite3.connect(journal + "?mode=rw", uri=True, timeout=120)) as db, db:
        db.execute("begin immediate")
        receipt = read_receipt(db)
        if proposal_id != receipt["proposal_id"]:
            raise ValueError("The supplied proposal ID does not match this review.")
        status = "APPLIED" if decision == "approve" else "REJECTED"
        if receipt["status"] != "PENDING":
            if receipt["status"] == status and receipt["reviewer"] == reviewer:
                return receipt
            raise ValueError(f"This proposal already has a decision: {receipt['status']}.")
        if decision == "approve":
            if proposal_digest(receipt["candidate"]) != proposal_id:
                raise ValueError("The proposed SQL or its fixture changed after validation.")
            receipt["applied"] = validate_shadow(receipt["candidate"], receipt["before"])
        receipt.update(status=status, reviewer=reviewer, decided_at=datetime.now(timezone.utc).isoformat())
        db.execute("update review set receipt = ? where id = 1", (json.dumps(receipt),))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare").add_argument("directory", type=Path)
    commands.add_parser("status").add_argument("directory", type=Path)
    for decision in ("approve", "reject"):
        command = commands.add_parser(decision)
        command.add_argument("directory", type=Path)
        command.add_argument("--reviewer", required=True)
        command.add_argument("--proposal", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            receipt = prepare(args.directory)
        elif args.command == "status":
            journal = (args.directory / "review.sqlite").resolve().as_uri()
            with closing(sqlite3.connect(journal + "?mode=ro", uri=True)) as db:
                receipt = read_receipt(db)
        else:
            receipt = review(args.directory, args.command, args.reviewer, args.proposal)
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
