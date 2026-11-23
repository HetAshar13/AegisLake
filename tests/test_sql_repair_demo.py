import json
import sqlite3
import subprocess
import sys

import pytest

from aegis_agent import sql_repair_demo as repair


@pytest.fixture
def pending(tmp_path):
    directory = tmp_path / "review"
    return directory, repair.prepare(directory)


def test_sql_repair_can_be_approved_from_a_new_process(pending):
    directory, proposal = pending
    assert proposal["status"] == "PENDING"
    assert proposal["lineage"]["upstream_tables"] == ["payment_input"]
    assert "+    amount_minor as reported_minor" in proposal["diff"]
    assert proposal["before"][0][2] == 1000000
    assert proposal["shadow"][0][2] == 10000
    assert proposal["before"][1] == proposal["shadow"][1]
    cli = [sys.executable, "-m", "aegis_agent.sql_repair_demo"]
    command = [
        *cli, "approve", str(directory),
        "--reviewer", "Demo reviewer", "--proposal", proposal["proposal_id"],
    ]
    applied = json.loads(subprocess.check_output(command, text=True))
    assert applied["status"] == "APPLIED"
    assert applied["applied"] == proposal["shadow"]
    assert json.loads(subprocess.check_output(command, text=True)) == applied
    assert json.loads(
        subprocess.check_output([*cli, "status", str(directory)], text=True)
    ) == applied


def test_rejection_stops_before_application(pending, monkeypatch):
    directory, proposal = pending

    def unexpected_build(*args):
        pytest.fail("Rejection must leave the model unbuilt")

    monkeypatch.setattr(repair, "build_model", unexpected_build)
    rejected = repair.review(directory, "reject", "Demo reviewer", proposal["proposal_id"])
    assert rejected["status"] == "REJECTED"
    assert "applied" not in rejected
    with pytest.raises(ValueError, match="already has a decision"):
        repair.review(directory, "approve", "Demo reviewer", proposal["proposal_id"])


def test_repair_refuses_changed_and_wrong_proposals(pending):
    directory, proposal = pending
    with pytest.raises(ValueError, match="does not match"):
        repair.review(directory, "approve", "Demo reviewer", "not-the-proposal")
    proposal["candidate"] = "select 1"
    with sqlite3.connect(directory / "review.sqlite") as db:
        db.execute("update review set receipt = ?", (json.dumps(proposal),))
    with pytest.raises(ValueError, match="changed after validation"):
        repair.review(directory, "approve", "Demo reviewer", proposal["proposal_id"])


def test_an_unchanged_model_fails_shadow_validation():
    original = (repair.FIXTURE / repair.MODEL).read_text(encoding="utf-8")
    before = [["card_eur", "EUR", 1000000], repair.EXPECTED[1]]
    with pytest.raises(ValueError, match="Shadow build"):
        repair.validate_shadow(original, before)
