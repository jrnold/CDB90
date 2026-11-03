"""Tests for ``create_data.py``."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

import create_data as cd

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src-data"
DATA_DIR = ROOT / "data"

#: Files in data/ that create_data.py does not write.
NOT_BUILT = {
    "LICENSE.md",
    "battle_coordinates.csv",
    "battle_links.csv",
    "flat",
}  # built by scripts/


def utc(*args: int) -> datetime:
    """Make a UTC date-time."""
    return datetime(*args, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------------------------
# Full build
# ---------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Build every table from a copy of src-data/ into a temporary directory."""
    tmp = tmp_path_factory.mktemp("build")
    src = tmp / "src-data"
    shutil.copytree(SRC_DIR, src, ignore=shutil.ignore_patterns("*.WKS", "datapackage"))
    data = tmp / "data"
    data.mkdir()
    cd.build(src, data)
    return src, data


def test_build_writes_every_table(built: tuple[Path, Path]) -> None:
    """The build writes every file in data/ except those that come from elsewhere."""
    _, data = built
    expected = {p.name for p in DATA_DIR.iterdir()} - NOT_BUILT
    assert {p.name for p in data.iterdir()} == expected


@pytest.mark.parametrize("name", sorted({p.name for p in DATA_DIR.iterdir()} - NOT_BUILT), ids=str)
def test_build_matches_committed_data(built: tuple[Path, Path], name: str) -> None:
    """Each table is byte-identical to the committed one."""
    _, data = built
    assert (data / name).read_bytes() == (DATA_DIR / name).read_bytes()


@pytest.mark.parametrize("name", ["CDB90-orig.csv", "CDB90-patched.csv"])
def test_build_matches_committed_cdb90(built: tuple[Path, Path], name: str) -> None:
    """The original and patched CDB90 data are byte-identical to the committed files."""
    src, _ = built
    committed = SRC_DIR / "CDB90" / name
    assert (src / "CDB90" / name).read_bytes() == committed.read_bytes()


# ---------------------------------------------------------------------------------------------
# Missing values and coercion
# ---------------------------------------------------------------------------------------------


def test_set_missing_codes_keeps_real_negative_values() -> None:
    """Only -9 and -9999 are missing; other negative codes favor the defender."""
    series = pd.Series([-9, -9999, -1, -2, 0, 3, None], dtype="Int64")
    result = cd.set_missing_codes(series)
    assert result.isna().tolist() == [True, True, False, False, False, False, True]
    assert result.dropna().tolist() == [-1, -2, 0, 3]


def test_set_missing_doubles() -> None:
    """Missing codes also match double columns such as kmda."""
    result = cd.set_missing_codes(pd.Series([-9.0, -6.4, -9999.0]))
    assert result.isna().tolist() == [True, False, True]


def test_set_missing_strings() -> None:
    """String codes match string columns exactly."""
    series = pd.Series(["00", "OO", "HD", None], dtype=object)
    result = cd.set_missing(series, ["00", "OO"])
    assert [cd.scalar(v) for v in result] == [None, None, "HD", None]


def test_set_missing_compares_mixed_types_as_strings() -> None:
    """Like R's %in%, integer 0 does not match "00", but -1 matches the string "-1"."""
    ints = pd.Series([0, 1], dtype="Int64")
    assert cd.set_missing(ints, ["00"]).isna().tolist() == [False, False]
    strings = pd.Series(["-1", "11300"], dtype=object)
    assert cd.set_missing(strings, [-1]).isna().tolist() == [True, False]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("7", 7), (" 4", 4), ("0.9", 0), ("-1.5", -1), ("1e2", 100), ("1234,5", None), (None, None)],
)
def test_r_as_integer(text: str | None, expected: int | None) -> None:
    """Strings convert to integers like R's as.integer(), truncating fractions."""
    assert cd.r_as_integer(text) == expected


@pytest.mark.parametrize(
    ("x", "expected"),
    [
        (0.0, "0"),
        (300.0, "300"),
        (-6.4, "-6.4"),
        (1 / 3, "0.333333333333333"),
        (0.1 + 0.2, "0.3"),
        (1.4375, "1.4375"),
        (100000.0, "1e+05"),
        (123456.0, "123456"),
        (0.0001, "1e-04"),
        (0.00012, "0.00012"),
    ],
)
def test_format_double(x: float, expected: str) -> None:
    """Doubles are written with up to 15 significant digits, as R chooses fixed or sci."""
    assert cd.format_double(x) == expected


def test_type_convert() -> None:
    """Column types are guessed like read.csv(); blanks stay blank only in strings."""
    ints = cd.type_convert(["1", "", "3"])
    assert str(ints.dtype) == "Int64"
    assert ints.isna().tolist() == [False, True, False]
    assert str(cd.type_convert(["", ""]).dtype) == "boolean"
    assert str(cd.type_convert(["1.5", "2"]).dtype) == "float64"
    strings = cd.type_convert(["a", "", "NA"])
    assert [cd.scalar(v) for v in strings] == ["a", "", None]


def test_write_csv(tmp_path: Path) -> None:
    """Output follows write.csv(na = ""): quoted strings, 0/1 logicals, blank missing."""
    frame = pd.DataFrame(
        {
            "i": pd.Series([1, None], dtype="Int64"),
            "x": [0.5, float("nan")],
            "s": pd.Series(['say "hi"', None], dtype=object),
            "b": pd.Series([True, None], dtype="boolean"),
            "t": pd.Series([utc(1600, 7, 2, 14, 30), None], dtype=object),
        }
    )
    path = tmp_path / "out.csv"
    cd.write_csv(frame, path)
    assert path.read_text() == (
        '"i","x","s","b","t"\n1,0.5,"say ""hi""",1,"1600-07-02T14:30:00"\n,,,,\n'
    )


# ---------------------------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("parts", "expected"),
    [
        ((None,), (None, None)),
        ((1600,), (utc(1600, 1, 1), utc(1601, 1, 1))),
        ((1600, 12), (utc(1600, 12, 1), utc(1601, 1, 1))),
        ((1600, 7, 2), (utc(1600, 7, 2), utc(1600, 7, 3))),
        ((1600, 7, 2, 14), (utc(1600, 7, 2, 14), utc(1600, 7, 2, 15))),
        ((1600, 7, 2, 14, 30), (utc(1600, 7, 2, 14, 30), utc(1600, 7, 2, 14, 30))),
        # Hour 24 rolls over to the next day, as in lubridate.
        ((1600, 7, 2, 24, 0), (utc(1600, 7, 3), utc(1600, 7, 3))),
        # A missing month ignores the day and time.
        ((1600, None, 2, 14, 30), (utc(1600, 1, 1), utc(1601, 1, 1))),
        # Invalid dates (day 99 is not recoded in active periods) are missing.
        ((1600, 7, 99), (None, None)),
        ((1600, 2, 30, 12), (None, None)),
        ((1600, 7, 2, 12, 60), (None, None)),
    ],
)
def test_datetime_range(
    parts: tuple[int | None, ...], expected: tuple[datetime | None, datetime | None]
) -> None:
    """The first missing component sets the precision of the range."""
    assert cd.datetime_range(*parts) == expected


def active_period_row(
    start_year: int | None = 1600, start_hour: int | None = 1430, end_hour: int | None = 1930
) -> dict[str, int | None]:
    """Make a row with active period 1 on 1600-07-02, by default from 14:30 to 19:30."""
    row: dict[str, int | None] = {"atpbyr1": start_year, "atpbmn1": 7, "atpbda1": 2}
    row |= {"atpeyr1": 1600, "atpemn1": 7, "atpeda1": 2}
    return row | {"atpbhr1": start_hour, "atpehr1": end_hour}


def test_active_period_times() -> None:
    """Exact start and end times give an exact duration in minutes."""
    period = cd.active_period(active_period_row(), 1)
    assert period is not None
    assert period["start_time_min"] == utc(1600, 7, 2, 14, 30)
    assert period["end_time_max"] == utc(1600, 7, 2, 19, 30)
    assert (period["duration_min"], period["duration_max"], period["duration_only"]) == (
        300,
        300,
        0,
    )


def test_active_period_duration_only() -> None:
    """A start hour of 5000 means the end hour holds the duration as 5000 + hhmm."""
    period = cd.active_period(active_period_row(start_hour=5000, end_hour=5230), 1)
    assert period is not None
    assert (period["duration_min"], period["duration_max"], period["duration_only"]) == (
        150,
        150,
        1,
    )
    assert period["start_time_min"] == utc(1600, 7, 2)
    assert period["start_time_max"] == utc(1600, 7, 3)


def test_active_period_unknown_hours() -> None:
    """Without hours the duration ranges from 0 to the whole span of the days."""
    period = cd.active_period(active_period_row(start_hour=None, end_hour=None), 1)
    assert period is not None
    assert (period["duration_min"], period["duration_max"]) == (0, 1440)


def test_active_period_without_start_year() -> None:
    """A period with no start year does not exist."""
    assert cd.active_period(active_period_row(start_year=None), 1) is None


# ---------------------------------------------------------------------------------------------
# Patch, tables and strings
# ---------------------------------------------------------------------------------------------


def test_apply_patch() -> None:
    """Patch values are set by isqno; strings for character columns, new columns added."""
    data = pd.DataFrame(
        {
            "ISQNO": pd.Series([1, 2, 3], dtype="Int64"),
            "STRA": pd.Series(["100", "200", "300"], dtype=object),
            "TANKD": pd.Series([0, 0, 0], dtype="Int64"),
        }
    )
    patch = [
        {"isqno": [2], "values": {"stra": 250, "tankd": 75}},
        {"isqno": 3, "values": {"insta": 9}},
        {"isnqo": [1], "values": {"tankd": 99}},  # misspelled key: skipped, as in R
    ]
    result = cd.apply_patch(data, patch)
    assert result["STRA"].tolist() == ["100", "250", "300"]
    assert result["TANKD"].tolist() == [0, 75, 0]
    assert str(result["INSTA"].dtype) == "Int64"
    assert result["INSTA"].isna().tolist() == [True, True, False]
    assert data["STRA"].tolist() == ["100", "200", "300"]


def test_belligerent_col_names() -> None:
    """The side letter goes before a trailing digit or pl/mi."""
    attacker = cd.belligerent_col_names(attacker=True)
    defender = cd.belligerent_col_names(attacker=False)
    assert attacker["nam"] == "nama"
    assert attacker["pri1"] == "pria1"
    assert defender["strpl"] == "strdpl"
    assert defender["casmi"] == "casdmi"


def test_split_codes() -> None:
    """O reads as zero, all-zero codes are dropped, zeros are missing, short codes blank."""
    cdb90 = pd.DataFrame(
        {
            "isqno": pd.Series([1, 2], dtype="Int64"),
            "terra1": pd.Series(["RbO", "R"], dtype=object),
            "terra2": pd.Series(["OOO", "000"], dtype=object),
        }
    )
    result = cd.terrain_data(cdb90)
    assert result["isqno"].tolist() == [1, 2]
    assert result["terrano"].tolist() == [1, 1]
    rows = [[cd.scalar(v) for v in row] for row in result[["terra1", "terra2", "terra3"]].values]
    assert rows == [["R", "B", None], ["R", "", ""]]


def test_enum_tables() -> None:
    """Each variable gets a value and description table in the order of the JSON file."""
    tables = cd.enum_tables({"wina": {"0": "draw", "1": "attacker win", "-1": "attacker loss"}})
    assert list(tables) == ["wina"]
    assert tables["wina"]["value"].tolist() == ["0", "1", "-1"]
    assert tables["wina"]["description"].tolist() == ["draw", "attacker win", "attacker loss"]


@pytest.mark.parametrize(
    ("actors", "expected"),
    [("Spain", ["Spain"]), ("France & Spain", ["France", "Spain"]), ("A&B &  C", ["A", "B", "C"])],
)
def test_split_actors(actors: str, expected: list[str]) -> None:
    """Actors are separated by & with optional whitespace."""
    assert cd.split_actors(actors) == expected


def test_collate_key_matches_icu_order() -> None:
    """Strings sort as R's ICU collation does: case second, punctuation before letters."""
    words = ["USA", "a1", "ab", "B", "United-States", "a b", "b", "A", "United States", "a"]
    assert sorted(words, key=cd.collate_key) == [
        "a",
        "A",
        "a b",
        "a1",
        "ab",
        "b",
        "B",
        "United States",
        "United-States",
        "USA",
    ]
