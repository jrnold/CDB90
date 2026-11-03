"""Load the relational tables in ``data/relational/`` into a SQLite database, ``cdb90.sqlite3``.

Table and column names and types come from the schema files in ``src-data/datapackage/``
(``resources/*.yaml``, ``enum_tables.yaml`` and the version table in ``datapackage.yaml``). Empty
cells are loaded as NULL.
"""

import csv
import sqlite3
from pathlib import Path
from typing import Any

import yaml

SCHEMA_DIR = Path("src-data/datapackage")
OUTPUT = Path("cdb90.sqlite3")
SQL_TYPES = {
    "integer": "INTEGER",
    "number": "REAL",
    "boolean": "INTEGER",
    "string": "TEXT",
    "datetime": "TEXT",
}


def load_yaml(path: Path) -> Any:
    """Read a YAML file."""
    with path.open() as f:
        return yaml.safe_load(f)


def table_schemas() -> dict[Path, list[tuple[str, str]]]:
    """Return ``{csv path: [(column, SQL type), ...]}`` for every relational table."""
    resources = list(load_yaml(SCHEMA_DIR / "datapackage.yaml")["resources"])
    resources += [load_yaml(path) for path in sorted((SCHEMA_DIR / "resources").glob("*.yaml"))]
    for name, enum in load_yaml(SCHEMA_DIR / "enum_tables.yaml").items():
        resources.append(
            {
                "path": f"data/relational/enum_{name}.csv",
                "schema": {
                    "fields": [
                        {"id": "value", "type": enum["type"]},
                        {"id": "description", "type": "string"},
                    ]
                },
            }
        )
    return {
        Path(resource["path"]): [
            (field["id"], SQL_TYPES[field["type"]]) for field in resource["schema"]["fields"]
        ]
        for resource in resources
    }


def load_table(conn: sqlite3.Connection, path: Path, columns: list[tuple[str, str]]) -> None:
    """Create the table for ``path`` and fill it from the CSV file.

    Columns are matched by name, because the order in the schema files is not always the order in
    the CSV file. The table has its columns in the CSV file's order.
    """
    table = path.stem
    sql_types = dict(columns)
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        if sorted(header) != sorted(sql_types):
            message = f"{path}: columns {header} do not match the schema {list(sql_types)}"
            raise ValueError(message)
        definition = ", ".join(f'"{name}" {sql_types[name]}' for name in header)
        conn.execute(f'CREATE TABLE "{table}" ({definition})')
        placeholders = ", ".join("?" * len(header))
        rows = ([value or None for value in row] for row in reader)
        conn.executemany(f'INSERT INTO "{table}" VALUES ({placeholders})', rows)  # noqa: S608


def main() -> None:
    """Build the database."""
    OUTPUT.unlink(missing_ok=True)
    with sqlite3.connect(OUTPUT) as conn:
        for path, columns in table_schemas().items():
            load_table(conn, path, columns)
    conn.close()


if __name__ == "__main__":
    main()
