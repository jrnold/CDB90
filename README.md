# CDB90 Battle Dataset

A tidier and open-data version of CDB90 (CAA Database of Battles, Version 1990).
This used to be called CDB13, which I thought was an amusing name, but seemed to make people think I added to the CDB90 data.

The description of CDB90 from Helmbold (1993):

  A database of over 600 battles that were fought between 1600AD and
  1973AD. Descriptive data include battle name, date, and location;
  the strengths and losses on each side; identification of the victor;
  temporal duration of the battle; and selected environmental and
  tactical environment descriptors (such as type of fortifications,
  type of tactical scheme, weather conditions, width of front, etc.)

The original documentation for the CDB90 dataset is in [src-data/M000121/README.TXT](https://github.com/jrnold/CDB90/tree/master/src-data/M000121).

The directory `src-data/M000121` contains the original data from CDB90 as obtained from the NTIS.
The original datafiles are the `WKS` files.
However, since this is an archaic format, these were converted to `csv` files using LibreOffice (v. 4.4.3.2; BuildId: 88805f81e9fe61362df02b9941de8e38a9b5fd16; Locale: en_).

The directory `data` contains the revised data (see [Formats](#formats)).
No major substantive changes were made to the data, nor were new battles added.
A brief summary of the revisions are:

- Minor changes to several values so that logical relationships hold. These are all the edits made in the revision CDB91 as described in Helmbold (1995) [DTIC reort ADA298124, p. 2-4](http://oai.dtic.mil/oai/oai?verb=getRecord&metadataPrefix=html&identifier=ADA298124). The remainder are a few other logical inconsistencies in the original data: e.g. total tanks must equal light battle tanks plus main battle tanks; tanks are 0, not missing prior to WWI.
- Reformatting the data from one of the messier spreadsheets that I have ever seen to tidy data. This means that there are separate tables for battles, combatants, activity periods, etc.
- Additional variables linking the battles to other datasources such as the Correlates of War
- Different categorizations of wars, both from the original HERO dataset and my own categorization which is mostly consistent with the COW wars after 1815, and Wikipedia before 1815.

The flat CSV tables are described by a [Data Package](https://datapackage.org) (`datapackage.json`).

# Formats

There are three ways to get the data, all in version 10.0.0 and later (from the GitHub release and Zenodo).

  | Format               | Files                                                              | For                                                                                                                                                      |
  | -------------------- | ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | Flat CSV and Parquet | `data/flat/battles.{csv,parquet}`, `data/flat/sides.{csv,parquet}` | Analysis: one row per battle, or per battle and side, with the tables already joined.                                                                    |
  | SQLite               | `cdb90.sqlite3` (release asset)                                    | The relational tables: battles, belligerents, commanders, active periods, weather, terrain, front widths, battle links, coordinates and the code tables. |
  | Relational CSV       | `data/relational/*.csv`                                            | The inputs of the SQLite database, one csv per table.                                                                                                    |

`datapackage.json` is a [Frictionless](https://frictionlessdata.io) Data Package for the flat CSV tables.

- `battles`: one row per battle, with its dates and duration, coordinates, most specific Wikipedia link and per-side totals. The coded variables (`wina`, `cea`, `surpa`, ...) are from the attacker's point of view.
- `sides`: one row per battle and side, with forces, commanders and the outcome from that side's point of view (1 win, 0 draw, -1 loss).

Every battle is linked to one or more Wikidata items and Wikipedia articles (`battle_links` in SQLite, `wikidata_id` and `wikipedia_title` in the flat `battles` table), and 648 of the 660 battles have coordinates from Wikidata (`coordinate_precision` says whether the point is the battle, the place it is named after, or only its campaign or region).

Version 10.0.0 moved the relational csv tables from `data/` to `data/relational/`.

# Usage

The build is a [DVC](https://dvc.org) pipeline (`dvc.yaml`). To rebuild the tables, the flat
analysis tables, the data package and the SQLite database, install the Python dependencies with
`uv sync` and run:

```
$ uv run dvc repro
```

The `links` and `coordinates` stages query the Wikipedia and Wikidata APIs, so they need network
access. Every output is small and published from git, so the pipeline has no DVC remote.

# References

- CAA Study Report CAA-SR-84-6, "Analysis of Factors That Have Influenced Outcomes of Battles and Wars: A Data Base of Battles and Engagements," September 1984: AD-B086-797L, AD-B087-718L, AD-B087-719L, AD-B087-720L, AD-B087-721L, AD-B087-722L
- HERO Report Number 129, "Combat History Analysis Study Effort (CHASE) Data Enhancement Study (CDES)," 31 January 1986, AD-A175-712, AD-A175-713, AD-A175-714, AD-A175-715, AD-A175-716
- Data Base Error Correction (DBEC)," 23 January 1987. It was prepared for CAA under Purchase Order Number MDA903-86-M-8560 and is available from DTIC under accession number AD-A176-750.
- FW Management Associates, Inc. Report "Independent Review/Reassessment of Anomalous Data (IR/RAD)," 22 June 1987, in four volumes. It was prepared for CAA under Contract Number MDA903-86-C-0396. It is available from DTIC under the following accession numbers: AD-???-??? (Volume I), AD-195-726 (Volume II), AD-???-??? (Volume III), and AD-???-??? (Volume IV)
- Data Memory Systems Incorporated report, "New Engagement Data for the Breakpoints Data Base," prepared for the US Army Concepts Analysis Agency under Contract No. MDA903-87-C-0807, 30 September 1988.
- Robert Helmbold. 1993. "Personnel Attrition Rates in Historical Land Combat Operations: A Catalog of Attrition and Casualty Data Bases on Diskettes Usable with Personal Computers." [DTIC ADA279069](http://www.dtic.mil/docs/citations/ADA279069).
- Robert Helmbold. 1995. "Personnel Attrition Rates in Historical Land Combat Operations. Some Empirical Relations among Force Sizes, Battle Durations" [DTIC AD-A268 787](http://handle.dtic.mil/100.2/ADA298124).

# Licenses

- Code is [MIT](LICENSE), unless otherwise noted. `load-sqlite.py` is vendored from
  [okfn/dptools](https://github.com/okfn/dptools); upstream gave no license.
- The derived data in `data/` and `datapackage.json` is [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
- Battle links and coordinates come from [Wikidata](https://www.wikidata.org/), which is CC0.
  `src-data/local/battle_links.csv` is curated by hand and with Wikipedia's search.
- The original CDB90 data in `src-data/M000121` is in the public domain.
