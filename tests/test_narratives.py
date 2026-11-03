"""Tests for the HERO narratives table and the parser that makes it."""

import csv
import re
from datetime import date
from pathlib import Path

from scripts import narratives

TABLE = Path("data/relational/battle_narratives.csv")


def read_table() -> list[dict[str, str]]:
    """Read the narratives table."""
    with TABLE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_parse_heading_accepts_the_formats_in_the_volumes() -> None:
    """Headings are emphasized in different ways, and may end with (O.S.), a period or a comma."""
    expected = {
        "<u>**Yvonne and Odette Positions, Sector Toulon, Verdun, 13/14 April 1918**</u>": (
            "Yvonne and Odette Positions, Sector Toulon, Verdun",
            date(1918, 4, 13),
        ),
        "<u>Sedgemoor, 6 July 1685 (O.S.)</u>": ("Sedgemoor", date(1685, 7, 6)),
        "_Prestonpans, 21 September 1745_": ("Prestonpans", date(1745, 9, 21)),
        "<u>Kut-el-Amara, 27-28 September, 1915</u>": ("Kut-el-Amara", date(1915, 9, 27)),
        "## __Soviet Counteroffensive at Moscow, 5 December 1941-7 January 1942__": (
            "Soviet Counteroffensive at Moscow",
            date(1941, 12, 5),
        ),
    }
    for raw, (title, start) in expected.items():
        parsed = narratives.parse_heading(raw)
        assert parsed is not None, raw
        assert (parsed[1], parsed[2]) == (title, start)


def test_parse_heading_rejects_other_lines() -> None:
    """Section headings, sentences and the Significance and Sources paragraphs are not headings."""
    for raw in (
        "<u>WORLD WAR I (WESTERN FRONT, 1918)</u>",
        "In April 1918 the 2d Division took over the sector.",
        "<u>Significance:</u> The attack failed in May 1918",
        "<u>Sources:</u> M.19; M.20; N.15.",
    ):
        assert narratives.parse_heading(raw) is None, raw


def test_expand_sources_gives_citations_and_volumes() -> None:
    """Codes become citations; a third number is the volume; unknown codes are marked."""
    entries = {
        ("B", 11): "Gindely, Anton. History of the Thirty Years' War. 2 vols. New York, 1898."
    }
    text = narratives.expand_sources("B.11.1; B.11; Z.9; B.11.1", entries)
    assert text.split("\n") == [
        "Gindely, Anton. History of the Thirty Years' War. 2 vols. New York, 1898. (vol. 1)",
        "Gindely, Anton. History of the Thirty Years' War. 2 vols. New York, 1898.",
        "Z.9 (not defined in the bibliography)",
    ]


def test_bibliography_repeats_the_author_of_a_ditto_entry() -> None:
    """An entry that starts with a ditto mark gets the author of the entry before it."""
    entries = narratives.bibliography()
    assert entries[("M", 20)].startswith("US Army. Translations of War Diaries")
    assert entries[("L", 8)].startswith("Dupuy, Col. Trevor N. The Military History")
    assert not [key for key, text in entries.items() if re.match(r"^[_.\-–—]", text)]


def test_table_has_one_narrative_per_battle() -> None:
    """Each battle has at most one narrative, and nearly all of the first 600 have one."""
    rows = read_table()
    isqnos = [int(row["isqno"]) for row in rows]
    assert len(isqnos) == len(set(isqnos))
    assert sum(isqno <= 600 for isqno in isqnos) == 585
    assert [isqno for isqno in isqnos if isqno > 600] == [601, *range(602, 626)]


def test_fields_are_clean_text() -> None:
    """No OCR markup, source codes or ditto marks are left in the fields."""
    for row in read_table():
        for field in ("narrative", "significance", "sources"):
            assert not re.search(r"</?u>|\*\*|<td>|<table>", row[field]), (row["isqno"], field)
        assert "______" not in row["sources"], row["isqno"]
        for line in row["sources"].split("\n"):
            assert not re.match(r"^[A-Z]{1,2}\.\d+(\.\d+)?\s*[;,.]?$", line), (row["isqno"], line)


def test_most_narratives_have_all_three_fields() -> None:
    """Almost every narrative has a significance and sources."""
    rows = read_table()
    assert sum(bool(row["narrative"]) for row in rows) >= len(rows) - 3
    assert sum(bool(row["significance"]) for row in rows) >= len(rows) - 8
    assert sum(bool(row["sources"]) for row in rows) >= len(rows) - 12


def test_yvonne_and_odette_narrative() -> None:
    """Battle 333 is parsed into its three fields, with the full citations."""
    (row,) = (row for row in read_table() if row["isqno"] == "333")
    assert row["hero_volume"] == "4"
    assert row["narrative"].startswith("The US 2d Division took up positions")
    assert row["narrative"].endswith("repelling the assault.")
    assert row["significance"].startswith("The engagement gave the troops")
    assert row["sources"].split("\n") == [
        "US Army. Records of the Second Division (Regular). 9 vols.",
        "US Army. Translations of War Diaries of German Units Opposed to the Second Division "
        "(Regular), Chateau Thierry, 1918. 4 vols.",
        "Stallings, Laurence. The Doughboys. New York, 1963.",
    ]


def test_engagements_of_the_1988_report() -> None:
    """The 24 engagements of AD-A201404 are parsed, whatever the OCR made of "(R)" in a heading."""
    engagements = narratives.split_engagements()
    assert len(engagements) == 24
    assert {n.document for n in engagements} == {"AD-A201404"}
    assert "Krinkelt-Rocherath I, 17 December 1944" in {n.heading for n in engagements}


def test_engagement_narrative_and_its_operation_sources() -> None:
    """Battle 603 has its narrative, significance and the sources of the Sidi Bou Zid operation."""
    (row,) = (row for row in read_table() if row["isqno"] == "603")
    assert row["document"] == "AD-A201404"
    assert row["hero_volume"] == ""
    assert row["narrative"].startswith("The Germans") or row["narrative"]
    assert row["significance"].startswith("Half the armored strength of the 1st Armored Division")
    lines = row["sources"].split("\n")
    assert len(lines) == 12
    assert lines[0].startswith("RG407, Box 14916, 601-TK(1)-0.2")
    assert "R following an engagement name" not in row["significance"]
    # the engagements of an operation share one list of sources
    (other,) = (r for r in read_table() if r["isqno"] == "602")
    assert other["sources"] == row["sources"]
