"""Publish the notes on source values, writing ``data/relational/data_notes.csv``.

Values in the CDB90 source data are kept as they are, even when another source shows them to be
wrong. ``src-data/local/data_notes.csv`` records those problems instead: which value, what is wrong
with it and the source that says so. This script checks that each note points at a real battle,
table and column, and that the value it quotes is the one in the table.
"""

import csv
from pathlib import Path

CURATED = Path("src-data/local/data_notes.csv")
RELATIONAL = Path("data/relational")
OUTPUT = RELATIONAL / "data_notes.csv"
COLUMNS = ["isqno", "attacker", "table_name", "column_name", "value", "note", "source"]


def read_table(name: str) -> list[dict[str, str]]:
    """Read a relational table."""
    with (RELATIONAL / f"{name}.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_note(note: dict[str, str], rows: list[dict[str, str]]) -> None:
    """Stop unless ``note`` quotes a value that is in the rows of its table."""
    matches = [
        row
        for row in rows
        if row["isqno"] == note["isqno"]
        and (not note["attacker"] or row.get("attacker") == note["attacker"])
    ]
    if not any(row.get(note["column_name"], None) == note["value"] for row in matches):
        message = f"note does not match the data: {note}"
        raise SystemExit(message)


def main() -> None:
    """Check and write the notes, ordered by battle."""
    with CURATED.open(newline="", encoding="utf-8") as f:
        notes = list(csv.DictReader(f))
    tables: dict[str, list[dict[str, str]]] = {}
    for note in notes:
        name = note["table_name"]
        check_note(note, tables.setdefault(name, read_table(name)))
    notes.sort(key=lambda n: (int(n["isqno"]), n["attacker"], n["table_name"], n["column_name"]))
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(COLUMNS)
        for note in notes:
            attacker = int(note["attacker"]) if note["attacker"] else ""
            writer.writerow(
                [int(note["isqno"]), attacker, *[note[c] for c in COLUMNS[2:]]],
            )


if __name__ == "__main__":
    main()
