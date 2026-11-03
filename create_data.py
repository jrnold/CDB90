"""Build the tidy CDB90 tables in ``data/`` from the source files in ``src-data/``.

This is a port of the original ``create_data.R``. It reproduces that script's output byte for
byte, including several of its quirks, so a few functions below emulate R behavior:

- ``read_cdb90`` follows ``readr::read_delim()`` (whitespace kept, ``""`` and ``"NA"`` are
  missing) and ``as()`` coercion, which truncates ``"0.9"`` to integer ``0``.
- ``read_local_csv`` follows ``read.csv()`` column type guessing.
- ``write_csv`` follows ``write.csv(na = "")``: strings quoted, doubles to 15 significant
  digits, logicals as ``0``/``1``.
- ``collate_key`` approximates the ICU collation R uses to compare strings in ``make_dyads``.

Run it from the repository root: ``uv run python create_data.py``.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime, timedelta, timezone
from itertools import islice, product
from pathlib import Path
from typing import Any, Final

import pandas as pd
import yaml

DATA_DIR: Final = Path("data")
SRC_DIR: Final = Path("src-data")

#: Number of header lines before the data rows in each ``M000121/CDB90???.csv`` file.
CDB90_HEADER_LINES: Final = 8
#: Battles with ``isqno`` up to this value come from the original HERO data.
LAST_HERO_ISQNO: Final = 600
#: ``atpbhr`` value marking that ``atpehr`` holds a duration (``5000 + hhmm``), not a time.
DURATION_ONLY_HOUR: Final = 5000
#: Missing value codes used by most CDB90 ordinal variables. Other negative values are real:
#: a negative value favors the defender (e.g. ``wina = -1`` is a defender win).
MISSING_CODES: Final = (-9, -9999)

#: Text encoding of all files. ``surrogateescape`` passes the few non-UTF-8 bytes in
#: ``src-data/local/commanders.csv`` through unchanged, as R does.
ENCODING: Final = "utf-8"
ENCODING_ERRORS: Final = "surrogateescape"

ACTOR_SEP: Final = re.compile(r"\s*&\s*")
NUMBER_RE: Final = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
INT32_MAX: Final = 2**31 - 1

Scalar = int | float | str | bool | datetime | None
Row = Mapping[str, Any]

# ---------------------------------------------------------------------------------------------
# R emulation: missing values, coercion, CSV input and output
# ---------------------------------------------------------------------------------------------


def as_frame(value: object) -> pd.DataFrame:
    """Return ``value``, checking that it is a data frame (pandas-stubs loses the type)."""
    if not isinstance(value, pd.DataFrame):
        raise TypeError(f"expected a DataFrame, got {type(value).__name__}")
    return value


def is_missing(value: object) -> bool:
    """Return whether ``value`` is a missing value (``None``, ``NaN``, ``NA`` or ``NaT``)."""
    if value is None:
        return True
    try:
        return bool(pd.isna(value))  # ty: ignore[no-matching-overload]
    except (TypeError, ValueError):
        return False


def scalar(value: object) -> Any:
    """Convert a pandas missing value to ``None`` and leave other values as they are."""
    return None if is_missing(value) else value


def r_as_double(value: str | None) -> float | None:
    """Convert a string to a float like R's ``as.numeric()``; other strings give ``None``."""
    if value is None:
        return None
    text = value.strip()
    if NUMBER_RE.fullmatch(text):
        return float(text)
    if re.fullmatch(r"[-+]?0[xX][0-9a-fA-F]+", text):
        return float(int(text, 16))
    return None


def r_as_integer(value: str | None) -> int | None:
    """Convert a string to an int like R's ``as.integer()``, truncating any fraction."""
    number = r_as_double(value)
    if number is None or not math.isfinite(number) or abs(number) > INT32_MAX:
        return None
    return int(number)


def r_as_character(value: object) -> str | None:
    """Convert a scalar to a string like R's ``as.character()``."""
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return format_double(value)
    return str(value)


def set_missing(series: pd.Series, values: Iterable[Scalar]) -> pd.Series:
    """Set the elements of ``series`` that equal any of ``values`` to missing.

    This is R's ``x[x %in% values] <- NA``. Like ``%in%``, it compares as strings when the
    series and the values differ in type, so an integer ``0`` does not match ``"00"``.
    """
    values = list(values)
    is_text = not (pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series))
    if is_text or any(isinstance(v, str) for v in values):
        targets = {r_as_character(v) for v in values}
        mask = series.map(r_as_character).isin(targets)
    else:
        mask = series.isin(values)
    mask = pd.Series(mask.to_numpy(dtype=bool, na_value=False), index=series.index)
    return series.mask(mask)


def set_missing_codes(series: pd.Series) -> pd.Series:
    """Set the CDB90 missing value codes (-9 and -9999) to missing."""
    return set_missing(series, MISSING_CODES)


def make_column(values: list[Any], kind: str) -> pd.Series:
    """Build a series of R type ``kind`` (``integer``, ``numeric``, ``logical``, ``character``)."""
    if kind == "integer":
        return pd.Series(values, dtype="Int64")
    if kind == "numeric":
        return pd.Series([math.nan if v is None else v for v in values], dtype="float64")
    if kind == "logical":
        return pd.Series(values, dtype="boolean")
    return pd.Series(values, dtype=object)


def type_convert(values: list[str]) -> pd.Series:
    """Guess the type of a column of strings like R's ``type.convert()`` in ``read.csv()``.

    ``"NA"`` is missing. Blank strings are also missing in logical and numeric columns, but
    stay blank in character columns.
    """
    present = [v for v in values if v not in {"", "NA"}]
    logicals = {"T": True, "F": False, "TRUE": True, "FALSE": False}
    logicals |= {"true": True, "false": False, "True": True, "False": False}
    if all(v in logicals for v in present):
        return make_column([logicals.get(v) for v in values], "logical")
    if all(re.fullmatch(r"[-+]?\d+", v) and abs(int(v)) <= INT32_MAX for v in present):
        return make_column([int(v) if v in present else None for v in values], "integer")
    numbers = [None if v in {"", "NA"} else r_as_double(v) for v in values]
    if all(n is not None for n, v in zip(numbers, values, strict=True) if v in present):
        return make_column(numbers, "numeric")
    return make_column([None if v == "NA" else v for v in values], "character")


def read_lines(path: Path) -> list[str]:
    """Read a text file into lines, keeping undecodable bytes."""
    with path.open(encoding=ENCODING, errors=ENCODING_ERRORS, newline="") as f:
        return f.read().splitlines()


def read_local_csv(path: Path) -> pd.DataFrame:
    """Read a CSV file with guessed column types, like R's ``read.csv()``."""
    header, *rows = list(csv.reader(read_lines(path)))
    rows = [row for row in rows if row]
    return pd.DataFrame(
        {name: type_convert([row[j] for row in rows]) for j, name in enumerate(header)}
    )


def format_double(x: float) -> str:
    """Format a double like R's ``write.csv()``: 15 significant digits, fixed or scientific."""
    if math.isnan(x):
        return "NA"
    if math.isinf(x):
        return "Inf" if x > 0 else "-Inf"
    if x == 0:
        return "0"
    mantissa, exponent = f"{x:.14e}".split("e")
    nsig = len(mantissa.lstrip("-").replace(".", "").rstrip("0"))
    kpower = int(exponent)
    negative = int(x < 0)
    decimals = max(0, nsig - kpower - 1)
    fixed_width = negative + max(kpower, 0) + 1 + (decimals + 1 if decimals else 0)
    sci_width = negative + (nsig + 1 if nsig > 1 else 1) + (5 if abs(kpower) >= 100 else 4)
    if fixed_width <= sci_width:
        return f"{x:.{decimals}f}"
    return f"{x:.{nsig - 1}e}"


def format_datetime(value: datetime) -> str:
    """Format a date-time as ``YYYY-MM-DDTHH:MM:SS``, dropping fractional seconds."""
    return (
        f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
        f"T{value.hour:02d}:{value.minute:02d}:{value.second:02d}"
    )


def quote(text: str) -> str:
    """Quote a string for CSV output, doubling embedded quotes."""
    return '"' + text.replace('"', '""') + '"'


def format_column(series: pd.Series) -> list[str]:
    """Format each element of a column as ``write.csv(na = "")`` would."""
    if pd.api.types.is_bool_dtype(series):
        return ["" if is_missing(v) else str(int(v)) for v in series]
    if pd.api.types.is_integer_dtype(series):
        return ["" if is_missing(v) else str(int(v)) for v in series]
    if pd.api.types.is_float_dtype(series):
        return ["" if is_missing(v) else format_double(float(v)) for v in series]

    def format_text(value: object) -> str:
        if is_missing(value):
            return ""
        if isinstance(value, datetime):
            return quote(format_datetime(value))
        return quote(str(value))

    return [format_text(v) for v in series]


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    """Write a data frame to ``path`` like R's ``write.csv(row.names = FALSE, na = "")``."""
    columns = [format_column(frame[name]) for name in frame.columns]
    lines = [",".join(quote(str(name)) for name in frame.columns)]
    lines += [",".join(fields) for fields in zip(*columns, strict=True)]
    with path.open("w", encoding=ENCODING, errors=ENCODING_ERRORS, newline="") as f:
        f.writelines(line + "\n" for line in lines)


# ICU root collation order of ASCII whitespace, punctuation and symbols, which all sort before
# digits and letters.
_ICU_SYMBOLS: Final = "\t\n\v\f\r _-,;:!?.'\"()[]{}@*/\\&#%`^+<=>|~$"


def collate_key(text: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return a sort key approximating ICU root collation, which R uses to compare strings.

    Characters are compared first ignoring case (symbols < digits < letters), and only then
    by case, with lower case first. Characters outside ASCII sort after letters by code point.
    """
    primary: list[int] = []
    tertiary: list[int] = []
    for char in text:
        lower = char.lower()
        if char in _ICU_SYMBOLS:
            primary.append(_ICU_SYMBOLS.index(char))
        elif char.isascii() and char.isdigit():
            primary.append(100 + ord(char))
        elif char.isascii() and char.isalpha():
            primary.append(200 + ord(lower))
        else:
            primary.append(1000 + ord(char))
        tertiary.append(int(char != lower))
    return tuple(primary), tuple(tertiary)


def split_actors(actors: str | None) -> list[str | None]:
    """Split an ``&``-separated list of actors, like ``str_split(x, "\\\\s*&\\\\s*")``."""
    if actors is None:
        return [None]
    return list(ACTOR_SEP.split(actors))


# ---------------------------------------------------------------------------------------------
# Reading and cleaning the original CDB90 data
# ---------------------------------------------------------------------------------------------


def read_cdb90_file(path: Path) -> Iterator[list[str | None]]:
    """Yield the data rows of one ``CDB90???.csv`` file, with ``""`` and ``"NA"`` as ``None``.

    Whitespace is kept (``read_delim()`` does not trim by default), so ``"ARDENNES "`` keeps
    its trailing space.
    """
    with path.open(encoding=ENCODING, errors=ENCODING_ERRORS, newline="") as f:
        for row in csv.reader(islice(f, CDB90_HEADER_LINES, None)):
            if row:
                yield [None if field in {"", "NA"} else field for field in row]


def read_cdb90(src_dir: Path, col_types: Mapping[str, str]) -> pd.DataFrame:
    """Read and combine the original CDB90 CSV files, converting columns to ``col_types``.

    The first comma is removed from the strength and casualty columns before conversion,
    as ``str_replace()`` does in the R script.
    """
    files = sorted(
        p for p in (src_dir / "M000121").iterdir() if re.fullmatch(r"CDB90\d{3}.*\.csv", p.name)
    )
    names = list(col_types)
    rows = [row for path in files for row in read_cdb90_file(path)]
    columns: dict[str, list[str | None]] = {name: [] for name in names}
    for row in rows:
        padded = row + [None] * (len(names) - len(row))
        for name, value in zip(names, padded, strict=False):
            columns[name].append(value)
    for prefix, side in product(["STR", "INTST", "FINST", "RERP", "CAS"], ["A", "D"]):
        name = prefix + side
        columns[name] = [None if v is None else v.replace(",", "", 1) for v in columns[name]]
    converters: dict[str, Callable[[str | None], Any]] = {
        "integer": r_as_integer,
        "numeric": r_as_double,
        "character": lambda v: v,
    }
    return pd.DataFrame(
        {
            name: make_column([converters[kind](v) for v in columns[name]], kind)
            for name, kind in col_types.items()
        }
    )


def apply_patch(data: pd.DataFrame, patch: list[dict[str, Any]]) -> pd.DataFrame:
    """Apply the edits in ``patch.yaml`` to the CDB90 data (upper case column names).

    Each entry sets ``values`` for the battles in ``isqno``. As in the R script, entries
    without an ``isqno`` key are skipped, and a value for a column that does not exist adds a
    new column that is missing for the other battles. Values for character columns are
    converted to strings.
    """
    data = as_frame(data.copy())
    for entry in patch:
        ids = entry.get("isqno")
        if ids is None:
            continue
        for isqno in ids if isinstance(ids, list) else [ids]:
            for key, value in entry["values"].items():
                col = key.upper()
                if col not in data.columns:
                    kind = (
                        "character"
                        if isinstance(value, str)
                        else "integer"
                        if isinstance(value, int)
                        else "numeric"
                    )
                    data[col] = make_column([None] * len(data), kind)
                elif data[col].dtype == object:
                    value = r_as_character(value)  # noqa: PLW2901
                data.loc[data["ISQNO"] == isqno, col] = value
    return data


def clean_cdb90(data: pd.DataFrame, patch: list[dict[str, Any]]) -> pd.DataFrame:
    """Apply the patch, blank the strength ranges of the non-HERO battles, lower case names.

    The R script sets ``str[ad]mi``, ``str[ad]pl``, ``cas[ad]mi`` and ``cas[ad]pl`` to missing
    for rows 601 to 660 (by position).
    """
    data = apply_patch(data, patch)
    ranges = [f"{a}{b}{c}".upper() for a, b, c in product(["str", "cas"], ["a", "d"], ["mi", "pl"])]
    for col in ranges:
        data.loc[data.index[LAST_HERO_ISQNO:660], col] = pd.NA
    data.columns = [name.lower() for name in data.columns]
    return data


# ---------------------------------------------------------------------------------------------
# Battles and belligerents
# ---------------------------------------------------------------------------------------------

BATTLE_VARS: Final = [
    "isqno", "war", "name", "locn", "campgn", "postype", "post1", "post2", "front", "depth",
    "time", "aeroa", "surpa", "cea", "leada", "trnga", "morala", "logsa", "momnta", "intela",
    "techa", "inita", "wina", "kmda", "crit", "quala", "resa", "mobila", "aira", "fprepa",
    "wxa", "terra", "leadaa", "plana", "surpaa", "mana", "logsaa", "fortsa", "deepa",
]  # fmt: skip
#: Battle variables where 9 means missing.
BATTLE_NINE_MISSING: Final = ["front", "depth", "time", "aeroa"]
#: Battle variables where -9 and -9999 mean missing.
BATTLE_CODED: Final = [
    "quala", "resa", "mobila", "aira", "fprepa", "wxa", "terra", "leadaa", "plana", "surpaa",
    "mana", "aeroa", "surpa", "cea", "leada", "trnga", "morala", "logsa", "momnta", "intela",
    "techa", "inita", "wina", "logsaa", "fortsa", "deepa", "kmda",
]  # fmt: skip


def battle_data(cdb90: pd.DataFrame, wars: pd.DataFrame, duplicates: pd.DataFrame) -> pd.DataFrame:
    """Build the battles table: one row per battle, with war codings and duplicate links."""
    x = cdb90[BATTLE_VARS].copy()
    x["is_hero"] = (x["isqno"] <= LAST_HERO_ISQNO).astype("boolean")
    for col in ["post1", "post2"]:
        x[col] = set_missing(x[col], ["00", "OO"])
    for col in BATTLE_NINE_MISSING:
        x[col] = set_missing(x[col], [9])
    for col in BATTLE_CODED:
        x[col] = set_missing_codes(x[col])
    x = x.merge(wars.drop(columns=["name", "war", "comment"]), on="isqno", how="inner")
    x = x.sort_values("isqno", kind="stable", ignore_index=True)
    x["dbpedia"] = [
        None if d is None else "http://dbpedia.org/resource/" + d if d else None
        for d in x["dbpedia"].map(scalar)
    ]
    x["war_initiator"] = (x["sidea"] == "A").astype("boolean")
    x = x.drop(columns="sidea")
    x = x.merge(duplicates, on="isqno", how="left")
    return as_frame(x.sort_values("isqno", kind="stable", ignore_index=True))


BELLIGERENT_VARS: Final = [
    "nam", "co", "str", "code", "intst", "rerp", "cas", "finst", "cav", "tank", "lt", "mbt",
    "arty", "fly", "ctank", "carty", "cfly", "pri1", "pri2", "pri3", "sec1", "sec2", "sec3",
    "reso1", "reso2", "reso3", "strpl", "strmi", "caspl", "casmi", "ach",
]  # fmt: skip
#: Belligerent variables where -1 means missing.
BELLIGERENT_NEG1_MISSING: Final = [
    "str", "intst", "rerp", "cas", "finst", "cav", "tank", "lt", "mbt", "arty", "fly", "ctank",
    "carty", "cfly",
]  # fmt: skip


def belligerent_col_names(attacker: bool) -> dict[str, str]:
    """Map belligerent variable names to CDB90 column names for the attacker or defender.

    The side letter goes before any trailing digit or ``pl``/``mi``: ``pri1`` is ``pria1``
    for the attacker, ``strpl`` is ``strdpl`` for the defender.
    """
    side = "a" if attacker else "d"
    names = {}
    for var in BELLIGERENT_VARS:
        match = re.fullmatch(r"(.*?)(\d|pl|mi)?", var)
        stem, suffix = match.groups() if match else (var, None)
        names[var] = f"{stem}{side}{suffix or ''}"
    return names


def belligerent_side(cdb90: pd.DataFrame, attacker: bool) -> pd.DataFrame:
    """Build the belligerent rows for one side (attacker or defender) of every battle."""
    col_names = belligerent_col_names(attacker)
    x = cdb90[["isqno", *col_names.values()]].copy()
    x.columns = ["isqno", *col_names]
    x["attacker"] = pd.Series(int(attacker), index=x.index, dtype="Int64")
    for col in ["co", "nam"]:
        x[col] = set_missing(x[col], ["?"])
    x["code"] = set_missing(x["code"], [0])
    for col in BELLIGERENT_NEG1_MISSING:
        x[col] = set_missing(x[col], [-1])
    for col in [f"{v}{i}" for v in ["pri", "sec", "reso"] for i in range(1, 4)]:
        # R turns these into factors, so integer columns (secd3) are written as strings.
        x[col] = set_missing(x[col], ["00"]).map(r_as_character).astype(object)
    return as_frame(x)


def belligerent_data(cdb90: pd.DataFrame, new_belligerents: pd.DataFrame) -> pd.DataFrame:
    """Build the belligerents table: one row per side per battle, with its actors.

    R's ``merge()`` on two keys sorts by the keys pasted into a string, so the rows are in
    the string order of ``isqno`` ("1", "10", "100", ...), then ``attacker``.
    """
    sides = pd.concat(
        [belligerent_side(cdb90, attacker=True), belligerent_side(cdb90, attacker=False)],
        ignore_index=True,
    )
    keys = new_belligerents.assign(attacker=new_belligerents["attacker"].astype(int))
    keys = keys.astype({"attacker": "Int64"})
    merged = sides.merge(keys, on=["isqno", "attacker"], how="inner")
    merged = merged[["isqno", "attacker", *BELLIGERENT_VARS, "actors"]]
    order = merged["isqno"].astype(str) + "\r" + merged["attacker"].astype(str)
    return as_frame(merged.iloc[order.argsort(kind="stable")].reset_index(drop=True))


def battle_actors(belligerents: pd.DataFrame) -> pd.DataFrame:
    """Build the battle actors table: one row per actor on each side of each battle."""
    records = [
        {"isqno": row["isqno"], "attacker": row["attacker"], "n": n, "actor": actor}
        for row in belligerents.to_dict("records")
        for n, actor in enumerate(split_actors(scalar(row["actors"])), start=1)
    ]
    frame = pd.DataFrame.from_records(records, columns=["isqno", "attacker", "n", "actor"])
    kinds = {"isqno": "Int64", "attacker": "Int64", "n": "Int64", "actor": object}
    return as_frame(frame.astype(kinds))


def battle_dyads(belligerents: pd.DataFrame) -> pd.DataFrame:
    """Build the battle dyads table: every attacking actor paired with every defending actor.

    This keeps two quirks of the R script: only the first attacker and defender rows of a
    battle are used, and only the last dyad of each battle gets its ``dyad`` label and
    ``direction`` (the others keep ``""`` and 1).
    """
    records = []
    for isqno, group in belligerents.groupby("isqno", sort=True):
        attackers = split_actors(scalar(group.loc[group["attacker"] == 1, "actors"].iloc[0]))
        defenders = split_actors(scalar(group.loc[group["attacker"] == 0, "actors"].iloc[0]))
        pairs = [(a, d) for d in defenders for a in attackers]
        dyads = [
            {
                "isqno": isqno,
                "attacker": a,
                "defender": d,
                "wt": 1 / len(pairs),
                "dyad": "",
                "direction": 1.0,
                "primary": i == 0,
            }
            for i, (a, d) in enumerate(pairs)
        ]
        last = dyads[-1]
        a, d = str(last["attacker"]), str(last["defender"])
        if collate_key(a) < collate_key(d):
            last["dyad"], last["direction"] = f"{a}|{d}", 1.0
        else:
            last["dyad"], last["direction"] = f"{d}|{a}", -1.0
        records += dyads
    frame = pd.DataFrame.from_records(records)
    kinds = {"isqno": "Int64", "attacker": object, "defender": object, "dyad": object}
    return as_frame(frame.astype(kinds).astype({"primary": "boolean"}))


# ---------------------------------------------------------------------------------------------
# Dates and active periods
# ---------------------------------------------------------------------------------------------


def make_datetime(
    year: int, month: int, day: int, hour: int = 0, minute: int = 0
) -> datetime | None:
    """Make a UTC date-time like lubridate's ``ymd_hm(quiet = TRUE)``.

    Invalid dates give ``None``. Hour 24 is accepted and rolls over to the next day.
    """
    if not 0 <= hour <= 24 or not 0 <= minute <= 59:
        return None
    try:
        start = datetime(year, month, day, tzinfo=timezone.utc)
    except ValueError:
        return None
    return start + timedelta(hours=hour, minutes=minute)


def add_month(value: datetime) -> datetime:
    """Add one calendar month to the first day of a month."""
    if value.month == 12:
        return value.replace(year=value.year + 1, month=1)
    return value.replace(month=value.month + 1)


def datetime_range(
    year: int | None,
    month: int | None = None,
    day: int | None = None,
    hour: int | None = None,
    minute: int | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Return the earliest and latest date-time consistent with a partially known date.

    The first missing component sets the precision: a missing month gives the year (from
    January 1 to January 1 of the next year), a missing day the month, a missing hour the day,
    and a missing minute the hour. Later components are ignored.
    """
    if year is None:
        return None, None
    if month is None:
        return make_datetime(year, 1, 1), make_datetime(year + 1, 1, 1)
    if day is None:
        start = make_datetime(year, month, 1)
        return start, None if start is None else add_month(start)
    if hour is None:
        start = make_datetime(year, month, day)
        return start, None if start is None else start + timedelta(days=1)
    if minute is None:
        start = make_datetime(year, month, day, hour)
        return start, None if start is None else start + timedelta(hours=1)
    start = make_datetime(year, month, day, hour, minute)
    return start, start


def minutes_between(end: datetime | None, start: datetime | None) -> float | None:
    """Return ``end - start`` in minutes, or ``None`` if either is missing."""
    if end is None or start is None:
        return None
    return (end - start).total_seconds() / 60


def active_period(row: Row, i: int) -> dict[str, Any] | None:
    """Build active period ``i`` of a battle, or ``None`` if it has no start year.

    An ``atpbhr`` of 5000 means that ``atpehr - 5000`` is the duration (hhmm) and the times
    are unknown. Otherwise the duration bounds come from the start and end time ranges.
    """
    begin = {var: scalar(row[f"atpb{var}{i}"]) for var in ["yr", "mn", "da", "hr"]}
    end = {var: scalar(row[f"atpe{var}{i}"]) for var in ["yr", "mn", "da", "hr"]}
    if begin["yr"] is None:
        return None
    duration_min = duration_max = None
    duration_only = 0.0
    hour1 = minute1 = hour2 = minute2 = None
    start_hour, end_hour = begin["hr"], end["hr"]
    if start_hour == DURATION_ONLY_HOUR:
        if end_hour is not None:
            duration_min = duration_max = float((end_hour // 100 - 50) * 60 + end_hour % 100)
        duration_only = 1.0
    elif start_hour is not None:
        hour1, minute1 = start_hour // 100, start_hour % 100
        if end_hour is not None:
            hour2, minute2 = end_hour // 100, end_hour % 100
    start_min, start_max = datetime_range(begin["yr"], begin["mn"], begin["da"], hour1, minute1)
    end_min, end_max = datetime_range(end["yr"], end["mn"], end["da"], hour2, minute2)
    if duration_min is None:
        shortest = minutes_between(end_min, start_max)
        duration_min = None if shortest is None else max(0.0, shortest)
        duration_max = minutes_between(end_max, start_min)
    return {
        "atp_number": i,
        "start_time_min": start_min,
        "start_time_max": start_max,
        "end_time_min": end_min,
        "end_time_max": end_max,
        "duration_max": duration_max,
        "duration_min": duration_min,
        "duration_only": duration_only,
    }


ACTIVE_PERIOD_COLUMNS: Final = {
    "isqno": "integer",
    "atp_number": "integer",
    "start_time_min": "datetime",
    "start_time_max": "datetime",
    "end_time_min": "datetime",
    "end_time_max": "datetime",
    "duration_max": "numeric",
    "duration_min": "numeric",
    "duration_only": "numeric",
}


def records_frame(records: list[dict[str, Any]], kinds: Mapping[str, str]) -> pd.DataFrame:
    """Build a data frame from records, with column R types ``kinds`` (or ``datetime``)."""
    return pd.DataFrame(
        {name: make_column([r[name] for r in records], kind) for name, kind in kinds.items()}
    )


def active_period_data(cdb90: pd.DataFrame) -> pd.DataFrame:
    """Build the active periods table: up to ten periods of fighting per battle.

    Years, months and hours of 99 or 9999 are missing. Days are not recoded, so a day of 99
    makes the date invalid and missing.
    """
    data = cdb90.copy()
    for be, var, i in product("be", ["hr", "mn", "yr"], range(1, 11)):
        col = f"atp{be}{var}{i}"
        data[col] = set_missing(data[col], [99, 9999])
    records = []
    for row in data.sort_values("isqno", kind="stable").to_dict("records"):
        for i in range(1, 11):
            period = active_period(row, i)
            if period is not None:
                records.append({"isqno": row["isqno"], **period})
    return records_frame(records, ACTIVE_PERIOD_COLUMNS)


def battle_durations(active_periods: pd.DataFrame) -> pd.DataFrame:
    """Summarize the active periods of each battle into its date range and duration.

    Any missing value in a battle's periods makes the summary missing, as with R's ``min()``
    and ``sum()``. ``duration1`` is the days from the earliest start to the latest start, plus
    one; ``duration2`` is the summed period durations divided by 1200, capped at ``duration1``.
    """

    def total(values: Iterable[Any]) -> list[Any] | None:
        values = [scalar(v) for v in values]
        return None if any(v is None for v in values) else values

    records = []
    for isqno, group in active_periods.groupby("isqno", sort=True):
        start_min = total(group["start_time_min"])
        start_max = total(group["start_time_max"])
        end_max = total(group["end_time_max"])
        dmin, dmax = total(group["duration_min"]), total(group["duration_max"])
        first = None if start_min is None else min(start_min)
        last = None if end_max is None else max(end_max)
        midpoint = None
        if first is not None and last is not None:
            midpoint = first + (last - first) / 2
        duration1 = None
        if start_max is not None and first is not None:
            duration1 = (max(start_max) - first).total_seconds() / 86400 + 1
        duration2 = None
        if dmin is not None and dmax is not None and duration1 is not None:
            summed = sum(0.5 * (a + b) for a, b in zip(dmin, dmax, strict=True))
            duration2 = min(summed / 1200, duration1)
        records.append(
            {
                "isqno": isqno,
                "datetime_min": first,
                "datetime_max": last,
                "datetime": midpoint,
                "duration1": duration1,
                "duration2": duration2,
            }
        )
    kinds = {"isqno": "integer", "datetime_min": "datetime", "datetime_max": "datetime"}
    kinds |= {"datetime": "datetime", "duration1": "numeric", "duration2": "numeric"}
    return records_frame(records, kinds)


def front_width_data(cdb90: pd.DataFrame) -> pd.DataFrame:
    """Build the front widths table: up to three front widths per battle, with their times.

    Rows where both widths are missing (-1) are dropped. A year of 9999, month or day of 99,
    and hour or minute of 99 (from an ``hr`` of 9999) are missing.
    """
    records = []
    for row in cdb90.sort_values("isqno", kind="stable").to_dict("records"):
        for i in range(1, 4):
            wofa, wofd = (scalar(row[f"wof{s}{i}"]) for s in "ad")
            wofa, wofd = (None if w == -1 else w for w in (wofa, wofd))
            hhmm = scalar(row[f"hr{i}"])
            parts = [scalar(row[f"{v}{i}"]) for v in ["yr", "mo", "da"]]
            parts += [None if hhmm is None else hhmm // 100, None if hhmm is None else hhmm % 100]
            missing = [9999, 99, 99, 99, 99]
            year, month, day, hour, minute = (
                None if v == code else v for v, code in zip(parts, missing, strict=True)
            )
            time_min, time_max = datetime_range(year, month, day, hour, minute)
            if wofa is None and wofd is None:
                continue
            records.append(
                {
                    "isqno": row["isqno"],
                    "front_number": i,
                    "wofa": wofa,
                    "wofd": wofd,
                    "time_min": time_min,
                    "time_max": time_max,
                }
            )
    kinds = {"isqno": "integer", "front_number": "integer", "wofa": "numeric"}
    kinds |= {"wofd": "numeric", "time_min": "datetime", "time_max": "datetime"}
    return records_frame(records, kinds)


# ---------------------------------------------------------------------------------------------
# Terrain, weather and enum tables
# ---------------------------------------------------------------------------------------------


def split_codes(
    cdb90: pd.DataFrame, prefix: str, count: int, width: int, number_col: str
) -> pd.DataFrame:
    """Split fixed-width code strings (``terra1``, ``wx2``, ...) into one column per letter.

    The letter ``O`` is read as zero, all-zero codes are dropped, and zero letters are
    missing. Codes shorter than ``width`` give blank strings for the absent letters.
    """
    records = []
    for row in cdb90.sort_values("isqno", kind="stable").to_dict("records"):
        for i in range(1, count + 1):
            code = str(row[f"{prefix}{i}"]).replace("O", "0").upper()
            if code == "0" * width:
                continue
            letters = {f"{prefix}{j}": code[j - 1 : j] for j in range(1, width + 1)}
            records.append(
                {
                    "isqno": row["isqno"],
                    number_col: i,
                    **{k: None if v == "0" else v for k, v in letters.items()},
                }
            )
    kinds = {"isqno": "integer", number_col: "integer"}
    kinds |= {f"{prefix}{j}": "character" for j in range(1, width + 1)}
    return records_frame(records, kinds)


def terrain_data(cdb90: pd.DataFrame) -> pd.DataFrame:
    """Build the terrain table: up to two three-letter terrain descriptions per battle."""
    return split_codes(cdb90, "terra", count=2, width=3, number_col="terrano")


def weather_data(cdb90: pd.DataFrame) -> pd.DataFrame:
    """Build the weather table: up to three five-letter weather descriptions per battle."""
    return split_codes(cdb90, "wx", count=3, width=5, number_col="wxno")


def enum_tables(levels: Mapping[str, Mapping[str, Any]]) -> dict[str, pd.DataFrame]:
    """Build a value and description table for each variable in ``variable_levels.json``."""
    return {
        name: pd.DataFrame(
            {
                "value": make_column(list(values), "character"),
                "description": make_column(
                    [r_as_character(v) for v in values.values()], "character"
                ),
            }
        )
        for name, values in levels.items()
    }


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------


def read_duplicates(path: Path) -> pd.DataFrame:
    """Read the matched duplicate battles as ``isqno`` and its ``parent`` battle."""
    duplicates = read_local_csv(path)
    duplicates = duplicates[duplicates["match"].astype(bool)]
    pairs = pd.DataFrame({"isqno": duplicates["isqno.x"], "parent": duplicates["isqno.y"]})
    return as_frame(pairs.reset_index(drop=True))


def read_sides(path: Path, columns: list[str]) -> pd.DataFrame:
    """Read a per-side local table, keeping ``columns`` and making ``attacker`` logical."""
    frame = read_local_csv(path)[columns].copy()
    frame["attacker"] = frame["attacker"].astype(bool).astype("boolean")
    return as_frame(frame)


def build(src_dir: Path, data_dir: Path) -> None:
    """Read the source files in ``src_dir`` and write every table to ``data_dir``.

    Also writes the original and patched CDB90 data to ``src_dir/CDB90``.
    """
    log = sys.stdout.write
    log(f"Writing files to {data_dir}")
    version = (src_dir / "version.txt").read_text(encoding=ENCODING).split()
    log("... Writing version.csv\n")
    write_csv(pd.DataFrame({"version": type_convert(version)}), data_dir / "version.csv")

    cdb90_dir = src_dir / "CDB90"
    col_types = json.loads((cdb90_dir / "cols.json").read_text(encoding=ENCODING))
    cdb90 = read_cdb90(src_dir, col_types)
    write_csv(cdb90, cdb90_dir / "CDB90-orig.csv")
    patch = yaml.safe_load((cdb90_dir / "patch.yaml").read_text(encoding=ENCODING))
    cdb90 = clean_cdb90(cdb90, patch)
    write_csv(cdb90.rename(columns=str.upper), cdb90_dir / "CDB90-patched.csv")

    local = src_dir / "local"
    wars = read_local_csv(local / "wars.csv")
    new_belligerents = read_sides(local / "belligerents.csv", ["isqno", "attacker", "actors"])
    commanders = read_sides(
        local / "commanders.csv", ["isqno", "attacker", "actors", "commanders", "uri"]
    )
    duplicates = read_duplicates(local / "duplicates.csv")

    belligerents = belligerent_data(cdb90, new_belligerents)
    active_periods = active_period_data(cdb90)
    tables = {
        "battles": battle_data(cdb90, wars, duplicates),
        "belligerents": belligerents,
        "weather": weather_data(cdb90),
        "terrain": terrain_data(cdb90),
        "active_periods": active_periods,
        "front_widths": front_width_data(cdb90),
        "battle_durations": battle_durations(active_periods),
        "battle_actors": battle_actors(belligerents),
        "battle_dyads": battle_dyads(belligerents),
        "commanders": commanders,
    }
    for name, table in tables.items():
        log(f"... Writing {name}.csv\n")
        write_csv(table, data_dir / f"{name}.csv")

    levels = json.loads((src_dir / "variable_levels.json").read_text(encoding=ENCODING))
    for name, table in enum_tables(levels).items():
        outfile = data_dir / f"enum_{name}.csv"
        log(f"... writing {outfile}\n")
        write_csv(table, outfile)


def main() -> None:
    """Build the tables from ``src-data/`` into ``data/``."""
    DATA_DIR.mkdir(exist_ok=True)
    build(SRC_DIR, DATA_DIR)


if __name__ == "__main__":
    main()
