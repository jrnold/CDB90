"""Build flat analysis tables from the relational tables in ``data/relational/``.

The relational tables follow the layout of CDB90 (battles, belligerents, active periods and so
on) and are loaded into SQLite. For analysis it is usually easier to start from one row per battle
or per battle side, so this writes two flat tables to ``data/flat/``, each as CSV and as Parquet
(zstd):

- ``battles``: one row per battle, with its dates and duration, first front width, coordinates,
  most specific Wikipedia link and per-side totals.
- ``narratives``: one row per battle that has a HERO narrative, with the narrative, its
  significance and its sources.
- ``sides``: one row per battle and side (attacker or defender), with the side's forces,
  commanders and outcome, and the battle's name, war, year and coordinates.
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
        FROM read_csv('data/relational/battle_links.csv')
    )
    WHERE rank = 1
),
front AS (
    SELECT isqno, wofa, wofd
    FROM read_csv('data/relational/front_widths.csv')
    WHERE front_number = 1
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
    FROM read_csv('data/relational/belligerents.csv')
    GROUP BY isqno
)
SELECT
    b.* EXCLUDE (dbpedia),
    d.datetime_min,
    d.datetime_max,
    d.datetime,
    d.duration1 AS duration_days,
    d.duration2 AS duration_active_days,
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
FROM read_csv('data/relational/battles.csv') AS b
LEFT JOIN read_csv('data/relational/battle_durations.csv') AS d USING (isqno)
LEFT JOIN front AS f USING (isqno)
LEFT JOIN read_csv('data/relational/battle_coordinates.csv') AS c USING (isqno)
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
    FROM read_csv('data/relational/commanders.csv')
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
FROM read_csv('data/relational/belligerents.csv') AS bl
JOIN read_csv('data/relational/battles.csv') AS b USING (isqno)
LEFT JOIN read_csv('data/relational/battle_durations.csv') AS d USING (isqno)
LEFT JOIN read_csv('data/relational/battle_coordinates.csv') AS c USING (isqno)
LEFT JOIN commanders AS cm ON cm.isqno = bl.isqno AND cm.attacker = bl.attacker
ORDER BY bl.isqno, bl.attacker DESC
"""


NARRATIVES_SQL = """
SELECT
    n.isqno,
    b.name,
    n.hero_volume,
    n.hero_title,
    n.narrative,
    n.significance,
    n.sources
FROM read_csv('data/relational/battle_narratives.csv') AS n
JOIN read_csv('data/relational/battles.csv') AS b USING (isqno)
ORDER BY n.isqno
"""


def write_table(query: str, name: str) -> None:
    """Run ``query`` and write the result to ``data/flat/<name>`` as zstd Parquet and as CSV."""
    relation = duckdb.sql(query)
    if relation is None:
        raise ValueError("the query returned no relation")
    parquet = OUTPUT / f"{name}.parquet"
    relation.write_parquet(str(parquet), compression="zstd")
    # write the CSV from the Parquet file, so both hold the same values
    duckdb.read_parquet(str(parquet)).write_csv(
        str(OUTPUT / f"{name}.csv"), timestamp_format="%Y-%m-%dT%H:%M:%S"
    )


def main() -> None:
    """Write the flat tables."""
    OUTPUT.mkdir(exist_ok=True)
    write_table(BATTLES_SQL, "battles")
    write_table(SIDES_SQL, "sides")
    write_table(NARRATIVES_SQL, "narratives")


if __name__ == "__main__":
    main()
