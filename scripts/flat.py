"""Build flat analysis tables from the tidy tables in ``data/``, written to ``data/flat/``.

The tidy tables follow the relational layout of CDB90 (battles, belligerents, active periods and
so on). For analysis it is usually easier to start from one row per battle or per battle side:

- ``battles.parquet``: one row per battle, with its dates and duration, first front width,
  coordinates, most specific Wikipedia link and per-side totals.
- ``sides.parquet``: one row per battle and side (attacker or defender), with the side's forces,
  commanders and outcome, and the battle's name, war, year and coordinates.

The tables are Parquet with zstd compression.
"""

from pathlib import Path

import duckdb

DATA = Path("data")
OUTPUT = DATA / "flat"

BATTLES_SQL = """
WITH link AS (
    -- the most specific link: the battle's own article, then campaign, then war
    SELECT isqno, wikidata_id, wikipedia_title, match AS link_match
    FROM (
        SELECT
            *,
            row_number() OVER (
                PARTITION BY isqno
                ORDER BY CASE match WHEN 'battle' THEN 0 WHEN 'campaign' THEN 1 ELSE 2 END,
                         wikipedia_title
            ) AS rank
        FROM read_csv('data/battle_links.csv')
    )
    WHERE rank = 1
),
front AS (
    SELECT isqno, wofa, wofd FROM read_csv('data/front_widths.csv') WHERE front_number = 1
),
sides AS (
    SELECT
        isqno,
        max(actors) FILTER (WHERE attacker = 1) AS attacker_actors,
        max(actors) FILTER (WHERE attacker = 0) AS defender_actors,
        max(TRY_CAST(str AS DOUBLE)) FILTER (WHERE attacker = 1) AS attacker_str,
        max(TRY_CAST(str AS DOUBLE)) FILTER (WHERE attacker = 0) AS defender_str,
        max(TRY_CAST(cas AS DOUBLE)) FILTER (WHERE attacker = 1) AS attacker_cas,
        max(TRY_CAST(cas AS DOUBLE)) FILTER (WHERE attacker = 0) AS defender_cas
    FROM read_csv('data/belligerents.csv')
    GROUP BY isqno
)
SELECT
    b.* EXCLUDE (dbpedia),
    d.datetime_min,
    d.datetime_max,
    d.datetime,
    d.duration1 AS duration_days_max,
    d.duration2 AS duration_days_min,
    f.wofa AS front_width_attacker,
    f.wofd AS front_width_defender,
    c.latitude,
    c.longitude,
    c.precision AS coordinate_precision,
    l.wikidata_id,
    l.wikipedia_title,
    l.link_match,
    s.attacker_actors,
    s.defender_actors,
    s.attacker_str,
    s.defender_str,
    s.attacker_cas,
    s.defender_cas
FROM read_csv('data/battles.csv') AS b
LEFT JOIN read_csv('data/battle_durations.csv') AS d USING (isqno)
LEFT JOIN front AS f USING (isqno)
LEFT JOIN read_csv('data/battle_coordinates.csv') AS c USING (isqno)
LEFT JOIN link AS l USING (isqno)
LEFT JOIN sides AS s USING (isqno)
ORDER BY isqno
"""

SIDES_SQL = """
WITH commanders AS (
    SELECT
        isqno,
        attacker,
        string_agg(DISTINCT commanders, '; ' ORDER BY commanders) AS commanders
    FROM read_csv('data/commanders.csv')
    GROUP BY isqno, attacker
)
SELECT
    bl.isqno,
    bl.attacker = 1 AS is_attacker,
    bl.* EXCLUDE (isqno, attacker),
    cm.commanders AS commander_names,
    -- outcome for this side: 1 win, 0 draw, -1 loss (wina is from the attacker's view)
    CASE WHEN bl.attacker = 1 THEN b.wina ELSE -b.wina END AS outcome,
    b.name AS battle_name,
    b.war,
    year(d.datetime) AS year,
    c.latitude,
    c.longitude,
    c.precision AS coordinate_precision
FROM read_csv('data/belligerents.csv') AS bl
JOIN read_csv('data/battles.csv') AS b USING (isqno)
LEFT JOIN read_csv('data/battle_durations.csv') AS d USING (isqno)
LEFT JOIN read_csv('data/battle_coordinates.csv') AS c USING (isqno)
LEFT JOIN commanders AS cm ON cm.isqno = bl.isqno AND cm.attacker = bl.attacker
ORDER BY bl.isqno, bl.attacker DESC
"""


def write_table(query: str, path: Path) -> None:
    """Run ``query`` and write the result to ``path`` as zstd-compressed Parquet."""
    relation = duckdb.sql(query)
    if relation is None:
        raise ValueError("the query returned no relation")
    relation.write_parquet(str(path), compression="zstd")


def main() -> None:
    """Write the flat tables."""
    OUTPUT.mkdir(exist_ok=True)
    write_table(BATTLES_SQL, OUTPUT / "battles.parquet")
    write_table(SIDES_SQL, OUTPUT / "sides.parquet")


if __name__ == "__main__":
    main()
