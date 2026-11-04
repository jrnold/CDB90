"""Resolve the curated commander links, writing ``data/relational/commander_links.csv``.

``src-data/local/commander_links.csv`` has one row for each named commander of each battle, with
the person's Wikidata item, or no item when the person could not be identified or has none. The
curated links were checked against the side, date and role of each battle, so they replace the
``uri`` column of ``commanders``, which is left as it is in the source data and has known errors
(see ``data_notes``). This script gets each item's label and English Wikipedia article. An item
that does not exist, is a redirect or is not a person stops the build, as does a curated row that
does not match ``commanders``. Wikidata is CC0.
"""

import csv
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://www.wikidata.org/w/api.php"
CURATED = Path("src-data/local/commander_links.csv")
COMMANDERS = Path("data/relational/commanders.csv")
OUTPUT = Path("data/relational/commander_links.csv")
BATCH_SIZE = 50
HUMAN = "Q5"
HEADERS = {"User-Agent": "CDB90-build/1.0 (https://github.com/jrnold/CDB90)"}


def fetch_items(ids: list[str]) -> dict[str, tuple[str, str]]:
    """Map each Wikidata ID to ``(English label, English Wikipedia title or "")``."""
    items: dict[str, tuple[str, str]] = {}
    problems: list[str] = []
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ids[start : start + BATCH_SIZE]
        response = requests.get(
            API,
            params={
                "action": "wbgetentities",
                "format": "json",
                "props": "labels|claims|sitelinks",
                "languages": "en|mul",
                "sitefilter": "enwiki",
                "ids": "|".join(batch),
            },
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        entities = response.json()["entities"]
        for qid in batch:
            entity = entities.get(qid, {})
            kinds = [
                claim["mainsnak"].get("datavalue", {}).get("value", {}).get("id")
                for claim in entity.get("claims", {}).get("P31", [])
            ]
            if "missing" in entity or entity.get("id") != qid or HUMAN not in kinds:
                problems.append(qid)
                continue
            labels = entity.get("labels", {})
            label = labels.get("en", labels.get("mul", {})).get("value", "")
            title = entity.get("sitelinks", {}).get("enwiki", {}).get("title", "")
            items[qid] = (label, title)
    if problems:
        message = f"Wikidata items that are missing, redirects or not people: {problems}"
        raise SystemExit(message)
    return items


def check_rows(curated: list[dict[str, str]], commanders: list[dict[str, str]]) -> None:
    """Stop unless the curated rows are exactly the named commanders in ``commanders``."""
    key = ("isqno", "attacker", "commanders")
    named = {tuple(row[k] for k in key) for row in commanders if row["commanders"]}
    rows = [tuple(row[k] for k in key) for row in curated]
    if len(rows) != len(set(rows)) or set(rows) != named:
        extra, missing = set(rows) - named, named - set(rows)
        message = (
            f"curated commander links do not match commanders: extra {sorted(extra)[:5]}, "
            f"missing {sorted(missing)[:5]}, duplicates {len(rows) - len(set(rows))}"
        )
        raise SystemExit(message)


def main() -> None:
    """Write the links file."""
    with CURATED.open(newline="", encoding="utf-8") as f:
        curated = list(csv.DictReader(f))
    with COMMANDERS.open(newline="", encoding="utf-8") as f:
        check_rows(curated, list(csv.DictReader(f)))
    linked = [row for row in curated if row["wikidata_id"]]
    items = fetch_items(sorted({row["wikidata_id"] for row in linked}))
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(
            [
                "isqno",
                "attacker",
                "commanders",
                "wikidata_id",
                "wikidata_label",
                "wikipedia_title",
                "wikipedia_url",
                "confidence",
            ]
        )
        for row in linked:
            label, title = items[row["wikidata_id"]]
            slug = quote(title.replace(" ", "_"), safe="_(),'!*~:@$")
            url = f"https://en.wikipedia.org/wiki/{slug}" if title else ""
            writer.writerow(
                [
                    int(row["isqno"]),
                    int(row["attacker"]),
                    row["commanders"],
                    row["wikidata_id"],
                    label,
                    title,
                    url,
                    row["confidence"],
                ]
            )


if __name__ == "__main__":
    main()
