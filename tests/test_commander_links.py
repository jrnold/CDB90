"""Tests for the commander links and the notes on source values."""

import csv
from pathlib import Path
from typing import Any

import pytest

from scripts import commander_links, data_notes

DATA = Path("data/relational")
CONFIDENCE = {"high", "medium", "low"}


def read(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of rows."""
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class FakeResponse:
    """A stand-in for ``requests.Response``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Do nothing."""

    def json(self) -> dict[str, Any]:
        """Return the payload."""
        return self.payload


def entity(qid: str, kind: str = "Q5") -> dict[str, Any]:
    """Make a Wikidata entity."""
    claim = {"mainsnak": {"datavalue": {"value": {"id": kind}}}}
    return {
        "id": qid,
        "labels": {"en": {"value": "A Person"}},
        "claims": {"P31": [claim]},
        "sitelinks": {"enwiki": {"title": "A Person"}},
    }


def test_fetch_items_returns_label_and_title(monkeypatch: pytest.MonkeyPatch) -> None:
    """A person's label and article are returned."""
    payload = {"entities": {"Q1": entity("Q1")}}
    monkeypatch.setattr(commander_links.requests, "get", lambda *a, **k: FakeResponse(payload))
    assert commander_links.fetch_items(["Q1"]) == {"Q1": ("A Person", "A Person")}


@pytest.mark.parametrize(
    "item",
    [entity("Q1", kind="Q178561"), entity("Q2"), {"id": "Q1", "missing": ""}],
    ids=["not a person", "redirect", "missing"],
)
def test_fetch_items_stops_on_bad_items(
    monkeypatch: pytest.MonkeyPatch, item: dict[str, Any]
) -> None:
    """A battle, a redirected item or a missing item stops the build."""
    payload = {"entities": {"Q1": item}}
    monkeypatch.setattr(commander_links.requests, "get", lambda *a, **k: FakeResponse(payload))
    with pytest.raises(SystemExit):
        commander_links.fetch_items(["Q1"])


def test_check_rows_requires_every_named_commander() -> None:
    """The curated rows must be exactly the named commanders, once each."""
    named = {"isqno": "1", "attacker": "0", "commanders": "GRANT"}
    unnamed = {"isqno": "2", "attacker": "0", "commanders": ""}
    commander_links.check_rows([named], [named, unnamed])
    with pytest.raises(SystemExit):
        commander_links.check_rows([], [named])
    with pytest.raises(SystemExit):
        commander_links.check_rows([named, named], [named])
    with pytest.raises(SystemExit):
        commander_links.check_rows([named, unnamed], [named])


def test_curated_links_cover_every_named_commander() -> None:
    """The published table's source has a row for each named commander."""
    commander_links.check_rows(
        read(Path("src-data/local/commander_links.csv")), read(DATA / "commanders.csv")
    )


def test_link_table_is_well_formed() -> None:
    """Links are Wikidata IDs with a known confidence, and most commanders are linked."""
    rows = read(DATA / "commander_links.csv")
    assert all(r["wikidata_id"].startswith("Q") for r in rows)
    assert {r["confidence"] for r in rows} <= CONFIDENCE
    assert all(r["wikipedia_url"] or not r["wikipedia_title"] for r in rows)
    assert len(rows) >= 1150


@pytest.mark.parametrize(
    ("isqno", "commander", "qid"),
    [
        ("179", "JACKSON", "Q216124"),
        ("444", "MG BAADE", "Q66251"),
        ("443", "MG ZIEHLBERG", "Q92327"),
        ("262", "GEN MOLTKE", "Q57130"),
        ("599", "MG PELED", "Q12409614"),
    ],
)
def test_known_links_are_the_listed_person(isqno: str, commander: str, qid: str) -> None:
    """Links name the listed person: not an opponent, a namesake or the actual commander."""
    rows = read(DATA / "commander_links.csv")
    found = {r["wikidata_id"] for r in rows if (r["isqno"], r["commanders"]) == (isqno, commander)}
    assert found == {qid}


def test_notes_quote_the_data() -> None:
    """Every published note quotes a value that is in its table."""
    notes = read(DATA / "data_notes.csv")
    assert notes
    for note in notes:
        data_notes.check_note(note, read(DATA / f"{note['table_name']}.csv"))


def test_check_note_stops_on_a_value_not_in_the_table() -> None:
    """A note that quotes the wrong value or side stops the build."""
    rows = [{"isqno": "1", "attacker": "0", "tank": "14"}]
    note = {"isqno": "1", "attacker": "0", "column_name": "tank", "value": "14"}
    data_notes.check_note(note, rows)
    with pytest.raises(SystemExit):
        data_notes.check_note({**note, "value": "15"}, rows)
    with pytest.raises(SystemExit):
        data_notes.check_note({**note, "attacker": "1"}, rows)
