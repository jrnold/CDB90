"""Download battle coordinates from DBpedia into ``data/battle_coordinates.csv``.

Each battle in ``data/battles.csv`` that links to a DBpedia resource gets the resource's
WGS 84 latitude and longitude, when it has them (the first linked resource that does).
Battles whose resources have no coordinates fall back to ``src-data/local/coordinates_lchsk.csv``,
which lchsk (https://github.com/lchsk/CDB13) fetched from DBpedia in 2015 for the American Civil
War battles. The ``source`` column says which was used.

The coordinates come from Wikipedia through DBpedia, so they are CC BY-SA, not CC0.
"""

import csv
from pathlib import Path
from urllib.parse import unquote

import requests

ENDPOINT = "https://dbpedia.org/sparql"
BATTLES = Path("data/battles.csv")
FALLBACK = Path("src-data/local/coordinates_lchsk.csv")
OUTPUT = Path("data/battle_coordinates.csv")
BATCH_SIZE = 50
PRECISION = 5  # DBpedia stores 32-bit floats; more digits than this are noise
QUERY = """
SELECT ?resource ?lat ?long WHERE {{
  VALUES ?resource {{ {resources} }}
  ?resource <http://www.w3.org/2003/01/geo/wgs84_pos#lat> ?lat ;
            <http://www.w3.org/2003/01/geo/wgs84_pos#long> ?long .
}}
"""


def fetch_coordinates(uris: list[str]) -> dict[str, tuple[float, float]]:
    """Return ``{resource URI: (latitude, longitude)}`` for the URIs DBpedia has coordinates for."""
    found: dict[str, tuple[float, float]] = {}
    for start in range(0, len(uris), BATCH_SIZE):
        batch = uris[start : start + BATCH_SIZE]
        query = QUERY.format(resources=" ".join(f"<{uri}>" for uri in batch))
        response = requests.get(
            ENDPOINT,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=60,
        )
        response.raise_for_status()
        for row in response.json()["results"]["bindings"]:
            # a resource can list several positions; keep the first
            found.setdefault(
                row["resource"]["value"],
                (float(row["lat"]["value"]), float(row["long"]["value"])),
            )
    return found


def main() -> None:
    """Write the coordinates file."""
    with BATTLES.open(newline="") as f:
        # a battle that spans several articles lists several space-separated URIs
        battles = [
            (int(row["isqno"]), [unquote(uri) for uri in row["dbpedia"].split()])
            for row in csv.DictReader(f)
        ]
    coordinates = fetch_coordinates(sorted({uri for _, uris in battles for uri in uris}))
    with FALLBACK.open(newline="") as f:
        fallback = {
            int(row["isqno"]): (float(row["latitude"]), float(row["longitude"]))
            for row in csv.DictReader(f)
        }
    with OUTPUT.open("w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\n")
        writer.writerow(["isqno", "latitude", "longitude", "source"])
        for isqno, uris in sorted(battles):
            # use the first article that has coordinates
            found = next((coordinates[uri] for uri in uris if uri in coordinates), None)
            if found is not None:
                lat, long = found
                writer.writerow([isqno, round(lat, PRECISION), round(long, PRECISION), "dbpedia"])
            elif isqno in fallback:
                lat, long = fallback[isqno]
                writer.writerow([isqno, round(lat, PRECISION), round(long, PRECISION), "lchsk"])


if __name__ == "__main__":
    main()
