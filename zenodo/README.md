# CDB90: data deposit

A tidier version of CDB90, the US Army Concepts Analysis Agency Database of Battles (Version 1990).
The code that builds these files, and the history of the project, are at
<https://github.com/jrnold/CDB90>.

  | File                             | Contents                                                                                                                                                 |
  | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `battles.csv`, `battles.parquet` | One row per battle (660): variables, dates and duration, coordinates, most specific Wikipedia link, per-side totals.                                     |
  | `sides.csv`, `sides.parquet`     | One row per battle and side (1,320): forces, commanders, and the outcome from that side's point of view.                                                 |
  | `cdb90.sqlite3`                  | The relational tables: battles, belligerents, commanders, active periods, weather, terrain, front widths, battle links, coordinates and the code tables. |
  | `relational-csv.zip`             | The same relational tables as one CSV per table.                                                                                                         |
  | `datapackage.json`               | A Frictionless Data Package describing `battles.csv` and `sides.csv`.                                                                                    |
  | `CODEBOOK.md`                    | The codebook: every table, column and code value, with descriptions.                                                                                     |
  | `original-documentation.txt`     | The documentation distributed with the original CDB90 data (US Army Concepts Analysis Agency, 1991).                                                     |
  | `LICENSE.md`                     | The licence of the data.                                                                                                                                 |

The derived data are CC0 1.0. The original CDB90 data are in the public domain. Links and coordinates
come from Wikidata (CC0). The coded variables in `battles` (`wina`, `cea`, `surpa`, ...) are from the
attacker's point of view: positive favors the attacker, negative the defender.
