"""Resolve the curated battle links to Wikidata items, writing ``data/relational/battle_links.csv``.

``src-data/local/battle_links.csv`` lists, for each battle, one or more English Wikipedia
articles: the battle itself (``match`` = battle), or the smallest campaign or war article that
covers it (campaign, war). This script resolves each title, following redirects, to its
Wikidata item and writes the Wikidata ID and the canonical Wikipedia title and URL.
Titles that do not resolve to a Wikidata item, or that are disambiguation pages, stop the build.
"""

import csv
from pathlib import Path
from urllib.parse import quote

import requests

API = "https://en.wikipedia.org/w/api.php"
CURATED = Path("src-data/local/battle_links.csv")
OUTPUT = Path("data/relational/battle_links.csv")
BATCH_SIZE = 50
HEADERS = {"User-Agent": "CDB90-build/1.0 (https://github.com/jrnold/CDB90)"}


def resolve_titles(titles: list[str]) -> dict[str, tuple[str, str]]:
    """Map each requested title to ``(Wikidata ID, canonical Wikipedia title)``."""
    resolved: dict[str, tuple[str, str]] = {}
    problems: list[str] = []
    for start in range(0, len(titles), BATCH_SIZE):
        batch = titles[start : start + BATCH_SIZE]
        response = requests.get(
            API,
            params={
                "action": "query",
                "format": "json",
                "formatversion": 2,
                "redirects": 1,
                "prop": "pageprops",
                "ppprop": "wikibase_item|disambiguation",
                "titles": "|".join(batch),
            },
            headers=HEADERS,
            timeout=60,
        )
        response.raise_for_status()
        query = response.json()["query"]
        # a requested title maps to a canonical one through normalization and redirects
        alias = {t: t for t in batch}
        for key in ("normalized", "redirects"):
            for change in query.get(key, []):
                for original, current in alias.items():
                    if current == change["from"]:
                        alias[original] = change["to"]
        pages = {page["title"]: page for page in query["pages"]}
        for original, current in alias.items():
            page = pages.get(current, {})
            props = page.get("pageprops", {})
            if page.get("missing") or "wikibase_item" not in props or "disambiguation" in props:
                problems.append(original)
            else:
                resolved[original] = (props["wikibase_item"], current)
    if problems:
        message = (
            f"titles that are missing, disambiguation pages or have no Wikidata item: {problems}"
        )
        raise SystemExit(message)
    return resolved


def main() -> None:
    """Write the links file."""
    with CURATED.open(newline="") as f:
        curated = list(csv.DictReader(f))
    resolved = resolve_titles(sorted({row["wikipedia_title"] for row in curated}))
    with OUTPUT.open("w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(["isqno", "wikidata_id", "wikipedia_title", "wikipedia_url", "match"])
        for row in curated:
            qid, title = resolved[row["wikipedia_title"]]
            slug = quote(title.replace(" ", "_"), safe="_(),'!*~:@$")
            writer.writerow(
                [
                    int(row["isqno"]),
                    qid,
                    title,
                    f"https://en.wikipedia.org/wiki/{slug}",
                    row["match"],
                ]
            )


if __name__ == "__main__":
    main()
