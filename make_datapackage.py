"""Write ``datapackage.json``, a Data Package describing the flat CSV tables in ``data/flat/``.

Metadata comes from ``src-data/datapackage/datapackage.yaml``. Column names and types come from
the Parquet files, and column descriptions from the relational schema files
(``src-data/datapackage/resources/*.yaml``) or, for new and renamed columns, ``flat.yaml``.
"""

import json
from pathlib import Path
from typing import Any

import duckdb
import yaml

SRC_DIR = Path("src-data/datapackage")
FLAT_DIR = Path("data/flat")
OUTPUT = Path("datapackage.json")
TYPES = {
    "BIGINT": "integer",
    "INTEGER": "integer",
    "DOUBLE": "number",
    "VARCHAR": "string",
    "BOOLEAN": "boolean",
    "TIMESTAMP": "datetime",
}


def load_yaml(path: Path) -> Any:
    """Read a YAML file."""
    with path.open() as f:
        return yaml.safe_load(f)


def clean(text: str) -> str:
    """Collapse the whitespace of a YAML text block."""
    return " ".join(text.split())


def column_descriptions(sources: list[str], extra: dict[str, str]) -> dict[str, str]:
    """Return ``{column: description}`` from the relational schemas in ``sources`` and ``extra``."""
    descriptions: dict[str, str] = {}
    for source in sources:
        resource = load_yaml(SRC_DIR / "resources" / f"{source}.yaml")
        for field in resource["schema"]["fields"]:
            if field.get("description"):
                descriptions.setdefault(field["id"], clean(field["description"]))
    descriptions.update({name: clean(text) for name, text in extra.items()})
    return descriptions


def resource(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Build the Data Package resource for the flat table ``name``."""
    parquet = FLAT_DIR / f"{name}.parquet"
    relation = duckdb.sql(f"DESCRIBE SELECT * FROM '{parquet}'")  # noqa: S608
    if relation is None:
        raise ValueError(parquet)
    columns = [(row[0], row[1]) for row in relation.fetchall()]
    descriptions = column_descriptions(spec["sources"], spec["columns"])
    missing = [column for column, _ in columns if column not in descriptions]
    if missing:
        raise SystemExit(f"{name}: no description for columns {missing}")
    fields = [
        {"name": column, "type": TYPES[sql_type], "description": descriptions[column]}
        for column, sql_type in columns
    ]
    return {
        "name": name,
        "path": f"data/flat/{name}.csv",
        "profile": "tabular-data-resource",
        "format": "csv",
        "mediatype": "text/csv",
        "encoding": "utf-8",
        "description": clean(spec["description"]),
        "schema": {"fields": fields, "missingValues": [""], "primaryKey": spec["primary_key"]},
    }


def main() -> None:
    """Write the data package descriptor."""
    package = load_yaml(SRC_DIR / "datapackage.yaml")
    package.pop("resources", None)
    package["profile"] = "tabular-data-package"
    package["version"] = (SRC_DIR.parent / "version.txt").read_text().strip()
    package["resources"] = [
        resource(name, spec) for name, spec in load_yaml(SRC_DIR / "flat.yaml").items()
    ]
    OUTPUT.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
