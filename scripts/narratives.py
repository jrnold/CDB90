"""Parse the HERO battle narratives into ``data/relational/battle_narratives.csv``.

The OCR text of the HERO volumes (CAA-SR-84-6, ``src-data/docs/hero/``) has a narrative for each of
the first 600 CDB90 battles: a heading with the date, paragraphs, a "Significance:" paragraph and a
"Sources:" paragraph that lists codes like ``M.19`` or ``B.11.1``. Each volume ends with a
bibliography that defines the codes. This script

1. parses each narrative into ``narrative``, ``significance`` and ``sources`` fields, replacing the
   codes in the sources with the full citations (``B.11.1`` is volume 1 of entry ``B.11``);
2. matches each narrative to a battle by title and date, with the manual matches in
   ``src-data/local/narrative_matches.csv`` taking priority.
"""

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

import duckdb

HERO = Path("src-data/docs/hero")
MATCHES = Path("src-data/local/narrative_matches.csv")
OUTPUT = Path("data/relational/battle_narratives.csv")
VOLUMES = range(2, 7)  # volume I is the main report; the narratives are in volumes II to VI
MONTHS = {
    name: number
    for number, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        1,
    )
}
MONTH_PATTERN = "|".join(MONTHS)
HEADING = re.compile(
    rf"^(?P<title>.+?),?\s+(?P<when>\d[^,]*?\b(?:{MONTH_PATTERN})\b[^,]*?\d{{4}})$"
)
START = re.compile(rf"(\d{{1,2}})(?:\s*[/-]\s*\d{{1,2}})?\s+({MONTH_PATTERN})(?:\s+(\d{{4}}))?")
CODE = re.compile(r"\b([A-Z]{1,2})\.\s?(\d+)(?:\.(\d+))?")
CODES_ONLY = re.compile(r"^[:;,.\s]*(?:[A-Z]{1,2}\.\s?\d+(?:\.\d+)?[:;,.\s]*)+$")
ENTRY = re.compile(r"^([A-Z]{1,2})\.(\d+)\s+(.*)$")
DITTO = re.compile(r"^(?:_+|[-–—]{2,}|\.)(?=[.,\s])")


def strip_markup(text: str) -> str:
    """Remove the Markdown and HTML emphasis that LlamaParse adds."""
    text = re.sub(r"</?u>|\*\*|__(?!_)|^#+\s*", "", text.strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 2 and text.startswith("_") and text.endswith("_") and "__" not in text:
        text = text.strip("_").strip()
    return text


def volume_text(volume: int) -> str:
    """Return the OCR text of a volume, pages joined by blank lines."""
    record = json.loads((HERO / f"caa-sr-84-6-vol-{volume}.json").read_text(encoding="utf-8"))
    pages: list[str] = [page["markdown"] for page in record["pages"]]
    return "\n\n".join(pages)


def author_of(raw: str) -> str:
    """Return the author at the start of a bibliography entry, before the underlined title."""
    first_close = raw.find("</u>")
    title_start = raw.rfind("<u>", 0, first_close) if first_close != -1 else raw.find("<u>")
    prefix = raw[:title_start] if title_start != -1 else ""
    author = strip_markup(prefix)
    if author:
        return author
    # the author is underlined too: take the text up to the first period that ends a word
    match = re.match(r"^(.*?\b(?:al|[A-Za-z]{3,})\.)\s+[A-Z]", strip_markup(raw))
    return str(match.group(1)) if match else ""


def bibliography() -> dict[tuple[str, int], str]:
    """Return ``{(letter, number): full citation}`` for the source codes of all volumes.

    An entry that starts with a ditto mark (``______.``) repeats the author of the entry before it.
    """
    entries: dict[tuple[str, int], str] = {}
    authors: dict[tuple[str, int], str] = {}
    for volume in range(1, 7):
        text = volume_text(volume)
        # table rows: <td>W.1</td> <td>description</td>
        pattern = r"<td>([A-Z]{1,2}\.\d+)</td>\s*<td>(.*?)</td>"
        for code, description in re.findall(pattern, text, re.DOTALL):
            letter, number = code.split(".")
            entries.setdefault((letter, int(number)), strip_markup(description))
        for line in text.split("\n"):
            match = ENTRY.match(strip_markup(line))
            if not match or "Sources" in line[:20]:
                continue
            key = (match.group(1), int(match.group(2)))
            if key in entries:
                continue
            raw = re.sub(r"^\W*[A-Z]{1,2}\.\d+\s+", "", line.strip().replace("**", ""))
            entries[key] = strip_markup(match.group(3))
            authors[key] = author_of(raw)
    resolved: dict[tuple[str, int], str] = {}
    for key in sorted(entries):
        body = entries[key]
        ditto = DITTO.match(body)
        if ditto:
            earlier = [k for k in resolved if k[0] == key[0] and k[1] < key[1]]
            previous = max(earlier, key=lambda k: k[1]) if earlier else None
            author: str = authors.get(previous, "") if previous else ""
            if author:
                rest = body[ditto.end() :]
                # "______, and Davies" adds a co-author; "______." just repeats the author
                body = author.rstrip(".") + (
                    rest if rest.startswith(",") else "." + rest.lstrip(".")
                )
            authors[key] = author
        resolved[key] = body
    return resolved


def expand_sources(codes_text: str, entries: dict[tuple[str, int], str]) -> str:
    """Replace the source codes in ``codes_text`` with the full citations, one per line.

    A code like ``B.11.1`` is volume 1 of entry ``B.11``.
    """
    citations = []
    for letter, number, volume in CODE.findall(codes_text):
        citation = entries.get((letter, int(number)))
        if citation is None:
            suffix = f".{volume}" if volume else ""
            citations.append(f"{letter}.{number}{suffix} (not defined in the bibliography)")
            continue
        citations.append(f"{citation} (vol. {volume})" if volume else citation)
    return "\n".join(dict.fromkeys(citations))


@dataclass
class Narrative:
    """One parsed narrative."""

    volume: int
    heading: str
    title: str
    start: date | None
    paragraphs: list[str] = field(default_factory=list)
    narrative: str = ""
    significance: str = ""
    sources: str = ""
    codes: str = ""


def parse_start(when: str) -> date | None:
    """Return the first date in a heading's date text, such as ``13/14 April 1918``."""
    match = START.search(when)
    if not match:
        return None
    year_match = match.group(3) or re.findall(r"\d{4}", when)[-1]
    try:
        return date(int(year_match), MONTHS[match.group(2)], int(match.group(1)))
    except ValueError:
        return None


def parse_heading(raw_line: str) -> tuple[str, str, date | None] | None:
    """Return ``(heading text, title, start date)`` if ``raw_line`` is a battle heading."""
    text = strip_markup(raw_line)
    # a trailing "(O.S.)", "(Continued)", a period, or a comma before the year are not part of it
    text = re.sub(r"\s*\((?:O\.S\.|N\.S\.|Continued)\)\s*$", "", text).rstrip(".")
    text = re.sub(r",\s*(\d{4})$", r" \1", text)
    match = HEADING.match(text)
    emphasized = raw_line.lstrip().startswith(("<u>", "_", "**", "#"))
    if (
        match is None
        or not emphasized
        or len(text) >= 170
        or re.match(r"(?i)^(significance|sources?)\b", text)
    ):
        return None
    title = str(match.group("title"))
    return text, title, parse_start(match.group("when"))


def has_sources(narrative: Narrative) -> bool:
    """Return whether the paragraphs so far include the narrative's sources (so it is complete)."""
    return any(
        re.match(r"(?i)^sources?\s*[:;.]", paragraph) or CODES_ONLY.match(paragraph)
        for paragraph in narrative.paragraphs
    )


def split_narratives(volume: int) -> list[Narrative]:
    """Split a volume into narratives, with their paragraphs.

    A narrative that runs over a page break repeats its heading (sometimes with "(Continued)"), so
    a heading seen before continues the narrative it already started.
    """
    narratives: list[Narrative] = []
    by_heading: dict[str, Narrative] = {}
    current: Narrative | None = None
    for raw_block in re.split(r"\n\s*\n", volume_text(volume)):
        block = re.sub(r"<table>.*?</table>", "", raw_block, flags=re.DOTALL)  # tables are not text
        raw_lines = [line for line in block.split("\n") if line.strip()]
        if not raw_lines:
            continue
        # the heading is the first line, or the second when a war heading comes first
        for position in range(min(2, len(raw_lines))):
            parsed = parse_heading(raw_lines[position])
            if parsed is not None:
                current = by_heading.get(parsed[0])
                if current is None and narratives:
                    # the OCR sometimes misspells a repeated heading
                    previous = narratives[-1]
                    if (
                        previous.start == parsed[2]
                        and not has_sources(previous)
                        and SequenceMatcher(None, previous.heading, parsed[0]).ratio() >= 0.9
                    ):
                        current = previous
                if current is None:
                    current = Narrative(volume, parsed[0], parsed[1], parsed[2])
                    narratives.append(current)
                    by_heading[parsed[0]] = current
                raw_lines = raw_lines[position + 1 :]  # the rest follows the heading directly
                break
        if raw_lines and current is not None:
            current.paragraphs.append(strip_markup(" ".join(raw_lines)))
    return narratives


def fill_fields(narrative: Narrative, entries: dict[tuple[str, int], str]) -> None:
    """Set the narrative, significance and sources fields from the paragraphs."""
    parts: dict[str, list[str]] = {"narrative": [], "significance": [], "sources": []}
    current = "narrative"
    for paragraph in narrative.paragraphs:
        if re.fullmatch(r"\d{1,3}", paragraph) or (
            paragraph.isupper() and not CODES_ONLY.match(paragraph)
        ):
            continue  # a page number or the heading of the next war
        text = paragraph
        if re.match(r"(?i)^significance\s*:", paragraph):
            current = "significance"
            text = re.sub(r"(?i)^significance\s*:\s*", "", paragraph)
        elif re.match(r"(?i)^sources?\s*[:;.]", paragraph):
            current = "sources"
            text = re.sub(r"(?i)^sources?\s*[:;.]\s*", "", paragraph)
        elif current == "sources":
            break  # text after the sources belongs to something else
        elif current == "significance" and CODES_ONLY.match(paragraph):
            current = "sources"  # the OCR lost the word "Sources" (and the significance text)
        if current == "significance" and CODES_ONLY.match(text):
            current = "sources"  # a "Significance:" paragraph that is only source codes
        parts[current].append(text.lstrip(":; "))
    narrative.narrative = "\n\n".join(parts["narrative"])
    narrative.significance = "\n\n".join(parts["significance"])
    narrative.codes = " ".join(parts["sources"])
    narrative.sources = expand_sources(narrative.codes, entries)


def normalize(name: str) -> str:
    """Lowercase a battle title for comparison."""
    name = re.sub(r"\(.*?\)", " ", name.lower())
    name = re.sub(r"\b(battle|battles|of|the|and|operation|campaign)\b", " ", name)
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", name).split())


def similarity(narrative_title: str, battle_name: str) -> float:
    """Return how similar a narrative's title and a battle's name are, from 0 to 1."""
    a, b = normalize(narrative_title), normalize(battle_name)
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    tokens_a, tokens_b = set(a.split()), set(b.split())
    overlap = len(tokens_a & tokens_b) / max(1, min(len(tokens_a), len(tokens_b)))
    return max(ratio, 0.9 * overlap)


def match_battles(narratives: list[Narrative]) -> dict[int, Narrative]:
    """Match narratives to battles; returns ``{isqno: narrative}``."""
    relation = duckdb.sql(
        """
        SELECT isqno, name, datetime_min::DATE AS start
        FROM read_csv('data/relational/battles.csv') AS b
        LEFT JOIN read_csv('data/relational/battle_durations.csv') AS d USING (isqno)
        """
    )
    if relation is None:
        raise ValueError("no battles")
    battles = relation.fetchall()
    manual: dict[int, tuple[int, str]] = {}
    if MATCHES.exists():
        with MATCHES.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                manual[int(row["isqno"])] = (int(row["volume"]), row["heading"])
    pairs = []
    for index, narrative in enumerate(narratives):
        for isqno, name, start in battles:
            if isqno in manual:
                if manual[isqno] == (narrative.volume, narrative.heading):
                    pairs.append((10.0, index, isqno))
                continue
            title = similarity(narrative.title, name)
            days = abs((narrative.start - start).days) if narrative.start and start else 9999
            if days <= 3 and title >= 0.35:
                pairs.append((2.0 + title - days / 100, index, isqno))
            elif days <= 45 and title >= 0.75:
                pairs.append((1.0 + title - days / 1000, index, isqno))
    matched: dict[int, Narrative] = {}
    used: set[int] = set()
    for _, index, isqno in sorted(pairs, reverse=True):
        if isqno in matched or index in used:
            continue
        matched[isqno] = narratives[index]
        used.add(index)
    return matched


def main() -> None:
    """Write the narratives table."""
    entries = bibliography()
    narratives = [n for volume in VOLUMES for n in split_narratives(volume)]
    for narrative in narratives:
        fill_fields(narrative, entries)
    matched = match_battles(narratives)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(
            ["isqno", "hero_volume", "hero_title", "narrative", "significance", "sources"]
        )
        for isqno in sorted(matched):
            n = matched[isqno]
            writer.writerow([isqno, n.volume, n.heading, n.narrative, n.significance, n.sources])


if __name__ == "__main__":
    main()
