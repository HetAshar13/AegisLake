from pathlib import Path

import duckdb


def test_delta_snapshot_excludes_replaced_authorization_file():
    table = (Path(__file__).resolve().parents[1] / "data/lakehouse/silver_authorizations").as_posix()
    with duckdb.connect() as db:
        active = db.execute("select count(*) from delta_scan(?)", [table]).fetchone()[0]
        physical = db.execute("select count(*) from read_parquet(?)", [f"{table}/*.parquet"]).fetchone()[0]
    assert active == 100
    assert physical == 200
