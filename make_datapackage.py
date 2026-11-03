"""Compile yaml files in ``src-data/datapackage/`` to ``datapackage.json``."""

import json
from pathlib import Path

import yaml

SRC_DIR = Path("src-data/datapackage")
DST_DIR = Path()


def create_enum_resource(k, v):
    """Create the data package resource for the enum table ``k``."""
    return {
        "path": f"data/enum_{k}.csv",
        "description": v["description"],
        "schema": {
            "fields": [
                {"id": "value", "description": "variable value", "type": v["type"]},
                {"id": "description", "description": "description of the value", "type": "string"},
            ]
        },
    }


with (SRC_DIR / "datapackage.yaml").open() as f:
    data = yaml.safe_load(f)

with (SRC_DIR.parent / "version.txt").open() as f:
    data["version"] = f.read().strip()

for file in sorted((SRC_DIR / "resources").iterdir()):
    if file.suffix == ".yaml":
        with file.open() as f:
            resdata = yaml.safe_load(f)
            resdata["name"] = Path(resdata["path"]).stem
            data["resources"].append(resdata)

with (SRC_DIR / "enum_tables.yaml").open() as f:
    enumdata = yaml.safe_load(f)
for k, v in enumdata.items():
    data["resources"].append(create_enum_resource(k, v))

with (DST_DIR / "datapackage.json").open("w") as f:
    json.dump(data, f, indent=2)
