"""Tests for the battle link and coordinate scripts and the tables they publish."""

import csv
from pathlib import Path
from typing import Any

import pytest

from scripts import coordinates, links

DATA = Path("data/relational")
VALID_MATCH = {"battle", "campaign", "war"}
VALID_PRECISION = {"battle", "place", "campaign", "region", "war"}
# battles for which no credible link or coordinates were found
NO_LINK = {333, 644, 646, 660}


def read(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of rows."""
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


class FakeResponse:
    """A stand-in for ``requests.Response``."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Do nothing: the fake never fails."""

    def json(self) -> dict[str, Any]:
        """Return the canned payload."""
        return self.payload


def test_resolve_titles_follows_redirects(monkeypatch: pytest.MonkeyPatch) -> None:
    """A redirected title resolves to the target's Wikidata item and title."""
    payload = {
        "query": {
            "redirects": [{"from": "Old name", "to": "New name"}],
            "pages": [{"title": "New name", "pageprops": {"wikibase_item": "Q1"}}],
        }
    }
    monkeypatch.setattr(links.requests, "get", lambda *a, **k: FakeResponse(payload))
    assert links.resolve_titles(["Old name"]) == {"Old name": ("Q1", "New name")}


def test_resolve_titles_rejects_disambiguation(monkeypatch: pytest.MonkeyPatch) -> None:
    """A disambiguation page stops the build rather than linking a battle to it."""
    pageprops = {"wikibase_item": "Q2", "disambiguation": ""}
    payload = {"query": {"pages": [{"title": "Battle of X", "pageprops": pageprops}]}}
    monkeypatch.setattr(links.requests, "get", lambda *a, **k: FakeResponse(payload))
    with pytest.raises(SystemExit):
        links.resolve_titles(["Battle of X"])


def test_resolve_titles_rejects_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A title that does not exist stops the build."""
    payload = {"query": {"pages": [{"title": "Nope", "missing": True}]}}
    monkeypatch.setattr(links.requests, "get", lambda *a, **k: FakeResponse(payload))
    with pytest.raises(SystemExit):
        links.resolve_titles(["Nope"])


def test_fetch_coordinates_parses_points(monkeypatch: pytest.MonkeyPatch) -> None:
    """WKT points are (longitude latitude); the result is (latitude, longitude)."""
    bindings = [
        {
            "item": {"value": "http://www.wikidata.org/entity/Q1"},
            "coord": {"value": "Point(2.5 51.25)"},
        },
        {
            "item": {"value": "http://www.wikidata.org/entity/Q1"},
            "coord": {"value": "Point(9 9)"},
        },
    ]
    payload = {"results": {"bindings": bindings}}
    monkeypatch.setattr(coordinates.requests, "get", lambda *a, **k: FakeResponse(payload))
    assert coordinates.fetch_coordinates(["Q1"]) == {"Q1": (51.25, 2.5)}


def test_every_battle_is_linked_except_known_gaps() -> None:
    """Each battle has at least one link, apart from the four with no credible article."""
    battles = {int(r["isqno"]) for r in read(DATA / "battles.csv")}
    linked = {int(r["isqno"]) for r in read(DATA / "battle_links.csv")}
    assert linked <= battles
    assert battles - linked == NO_LINK


def test_link_table_is_well_formed() -> None:
    """Links use valid match levels and Wikidata IDs, and are not duplicated."""
    rows = read(DATA / "battle_links.csv")
    assert {r["match"] for r in rows} <= VALID_MATCH
    assert all(r["wikidata_id"].startswith("Q") for r in rows)
    keys = [(r["isqno"], r["wikidata_id"]) for r in rows]
    assert len(keys) == len(set(keys))


def test_coordinates_are_valid() -> None:
    """Coordinates are in range, one per battle, with a known precision."""
    rows = read(DATA / "battle_coordinates.csv")
    battles = {r["isqno"] for r in read(DATA / "battles.csv")}
    assert len({r["isqno"] for r in rows}) == len(rows)
    assert {r["isqno"] for r in rows} <= battles
    assert {r["precision"] for r in rows} <= VALID_PRECISION
    assert all(-90 <= float(r["latitude"]) <= 90 for r in rows)
    assert all(-180 <= float(r["longitude"]) <= 180 for r in rows)
    assert len(rows) >= 640
