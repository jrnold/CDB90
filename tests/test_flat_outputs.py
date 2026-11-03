"""Tests for the flat tables, the SQLite database and the Data Package."""

import sqlite3
from pathlib import Path

import duckdb
import pytest
from frictionless import Package, validate

FLAT = Path("data/flat")


def scalar(query: str) -> int:
    """Run a query that returns one integer."""
    relation = duckdb.sql(query)
    assert relation is not None
    value = relation.fetchall()[0][0]
    assert isinstance(value, int)
    return value


def test_flat_table_sizes() -> None:
    """One row per battle, and two rows (attacker, defender) per battle."""
    assert scalar(f"SELECT count(DISTINCT isqno) FROM '{FLAT}/battles.parquet'") == 660
    assert scalar(f"SELECT count(*) FROM '{FLAT}/battles.parquet'") == 660
    assert scalar(f"SELECT count(*) FROM '{FLAT}/sides.parquet'") == 1320
    assert (
        scalar(f"SELECT count(DISTINCT (isqno, is_attacker)) FROM '{FLAT}/sides.parquet'") == 1320
    )


@pytest.mark.parametrize("name", ["battles", "sides"])
def test_csv_and_parquet_hold_the_same_rows(name: str) -> None:
    """The CSV and Parquet versions of a flat table agree."""
    csv = f"read_csv('{FLAT}/{name}.csv')"
    parquet = f"'{FLAT}/{name}.parquet'"
    assert scalar(f"SELECT count(*) FROM (SELECT * FROM {csv} EXCEPT SELECT * FROM {parquet})") == 0
    assert scalar(f"SELECT count(*) FROM (SELECT * FROM {parquet} EXCEPT SELECT * FROM {csv})") == 0
    assert scalar(f"SELECT count(*) FROM {csv}") == scalar(f"SELECT count(*) FROM {parquet}")


def test_outcome_is_from_each_sides_point_of_view() -> None:
    """The attacker's outcome is `wina` and the defender's is its negative."""
    query = f"""
        SELECT count(*)
        FROM '{FLAT}/sides.parquet' AS s JOIN '{FLAT}/battles.parquet' AS b USING (isqno)
        WHERE s.outcome IS DISTINCT FROM (CASE WHEN s.is_attacker THEN b.wina ELSE -b.wina END)
    """
    assert scalar(query) == 0


def test_sqlite_columns_are_matched_by_name(sqlite_db: Path) -> None:
    """Regression: the first SQLite builds loaded columns by position, scrambling three tables."""
    conn = sqlite3.connect(sqlite_db)
    try:
        row = conn.execute(
            "SELECT attacker, nam FROM belligerents WHERE isqno = 1 AND attacker = 1"
        ).fetchone()
        assert row == (1, "SP NETHERLANDS ARMY")
        assert conn.execute("SELECT count(*) FROM battles").fetchone() == (660,)
        # a header row is not data, and empty cells are NULL
        assert conn.execute("SELECT count(*) FROM battles WHERE isqno = 'isqno'").fetchone() == (0,)
        assert conn.execute("SELECT count(*) FROM battles WHERE wina IS NULL").fetchone() == (2,)
    finally:
        conn.close()


def test_data_package_is_valid() -> None:
    """The data package validates with Frictionless, including the CSV data."""
    report = validate("datapackage.json")
    assert report.valid, report.flatten(["type", "message"])


def test_data_package_describes_only_the_flat_csvs() -> None:
    """The package lists the flat CSV tables and nothing else."""
    package = Package("datapackage.json")
    assert [r.path for r in package.resources] == [
        "data/flat/battles.csv",
        "data/flat/narratives.csv",
        "data/flat/sides.csv",
    ]
