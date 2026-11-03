"""Look up battle coordinates on Wikidata, writing ``data/relational/battle_coordinates.csv``.

Each battle gets the coordinates (property P625) of its most specific item that has them. The
candidates are the items linked in ``data/relational/battle_links.csv`` (the battle itself, a
campaign or a war) and the place items in ``src-data/local/coordinates_places.csv`` (the place
the battle is named after, or a larger region). The ``precision`` column says which kind of item
the point comes from, so a campaign's point can be told apart from a battlefield's. Wikidata is
CC0.

Run ``scripts/links.py`` first.
"""

import csv
import re
from pathlib import Path

import requests

ENDPOINT = "https://query.wikidata.org/sparql"
LINKS = Path("data/relational/battle_links.csv")
PLACES = Path("src-data/local/coordinates_places.csv")
OUTPUT = Path("data/relational/battle_coordinates.csv")
BATCH_SIZE = 100
PRECISION_DIGITS = 5
HEADERS = {
    "User-Agent": "CDB90-build/1.0 (https://github.com/jrnold/CDB90)",
    "Accept": "application/sparql-results+json",
}
SPECIFICITY = {"battle": 0, "place": 1, "campaign": 2, "region": 3, "war": 4}
POINT = re.compile(r"Point\((-?[0-9.]+) (-?[0-9.]+)\)")
QUERY = "SELECT ?item ?coord WHERE {{ VALUES ?item {{ {items} }} ?item wdt:P625 ?coord . }}"


def fetch_coordinates(ids: list[str]) -> dict[str, tuple[float, float]]:
    """Return ``{Wikidata ID: (latitude, longitude)}`` for the items that have coordinates."""
    found: dict[str, tuple[float, float]] = {}
    for start in range(0, len(ids), BATCH_SIZE):
        batch = ids[start : start + BATCH_SIZE]
        query = QUERY.format(items=" ".join(f"wd:{qid}" for qid in batch))
        response = requests.get(ENDPOINT, params={"query": query}, headers=HEADERS, timeout=120)
        response.raise_for_status()
        for row in response.json()["results"]["bindings"]:
            match = POINT.fullmatch(row["coord"]["value"])
            if match is None:
                continue
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            # an item can have several coordinates; keep the first
            found.setdefault(qid, (float(match.group(2)), float(match.group(1))))
    return found


def main() -> None:
    """Write the coordinates file."""
    with LINKS.open(newline="") as f:
        links = [
            {"isqno": row["isqno"], "wikidata_id": row["wikidata_id"], "level": row["match"]}
            for row in csv.DictReader(f)
        ]
    with PLACES.open(newline="") as f:
        links += [
            {"isqno": row["isqno"], "wikidata_id": row["wikidata_id"], "level": row["precision"]}
            for row in csv.DictReader(f)
            if row["wikidata_id"]
        ]
    coordinates = fetch_coordinates(sorted({row["wikidata_id"] for row in links}))
    best: dict[int, tuple[int, str, str]] = {}
    for row in links:
        qid, level = row["wikidata_id"], row["level"]
        if qid not in coordinates:
            continue
        isqno = int(row["isqno"])
        rank = SPECIFICITY[level]
        if isqno not in best or rank < best[isqno][0]:
            best[isqno] = (rank, qid, level)
    with OUTPUT.open("w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(["isqno", "latitude", "longitude", "wikidata_id", "precision"])
        for isqno, (_, qid, level) in sorted(best.items()):
            lat, long = coordinates[qid]
            writer.writerow(
                [isqno, round(lat, PRECISION_DIGITS), round(long, PRECISION_DIGITS), qid, level]
            )


if __name__ == "__main__":
    main()
