"""Tests that the DVC pipeline is well formed."""

from pathlib import Path
from typing import Any

import yaml


def load_stages() -> dict[str, dict[str, Any]]:
    """Return the stages of ``dvc.yaml``."""
    with Path("dvc.yaml").open() as f:
        return yaml.safe_load(f)["stages"]


def test_dependencies_exist_or_are_outputs() -> None:
    """Every dependency is a file in the repo or the output of another stage."""
    stages = load_stages()
    outputs = {
        next(iter(out)) if isinstance(out, dict) else out
        for stage in stages.values()
        for out in stage["outs"]
    }
    for name, stage in stages.items():
        for dep in stage["deps"]:
            assert Path(dep).exists() or dep in outputs, f"{name}: missing dependency {dep}"


def test_outputs_are_unique_and_git_tracked() -> None:
    """No two stages write the same file, and no output is cached (there is no remote)."""
    seen: set[str] = set()
    for name, stage in load_stages().items():
        for out in stage["outs"]:
            assert isinstance(out, dict), f"{name}: write outputs as `path: {{cache: false}}`"
            ((path, options),) = out.items()
            assert options == {"cache": False}, f"{name}: {path} must be cache: false"
            assert path not in seen, f"{path} is written by two stages"
            seen.add(path)


def test_published_tables_are_all_built() -> None:
    """Every csv in `data/relational/` and `data/flat/` is an output of some stage."""
    outputs = {next(iter(out)) for stage in load_stages().values() for out in stage["outs"]}
    published = {str(p) for d in ("relational", "flat") for p in Path("data", d).glob("*.csv")}
    assert published <= outputs
