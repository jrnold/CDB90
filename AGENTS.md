# CDB90

A tidy, open-data version of the CDB90 battles dataset. The build is a DVC pipeline in `dvc.yaml`
(`uv run dvc repro`); see the README. Changes go through pull requests with auto-merge, and a change
to the published data bumps the version (`src-data/version.txt`, `data/relational/version.csv`,
`datapackage.json`, `pyproject.toml`) and gets a `vX.Y.Z` tag.

## Data (DVC)

This project follows the data baseline (read it with `git show main:data-baseline/README.md` in
`~/jrnold-projects`), as an empirical project with the exceptions below. Run `dvc` from the repo
root, through `uv run dvc`.

- After changing data or code: `uv run dvc repro`, then `git commit`. There is no remote, so no
  `dvc push`.
- Never run `dvc gc`.
- Zenodo gets the data only, through `scripts/zenodo.py` (metadata in `zenodo/metadata.json`), not
  the GitHub-Zenodo integration, so do not add a `.zenodo.json`. Never run `deposit --publish`
  without the user asking: a DOI is permanent.
- `links`, `coordinates` and `commander-links` query the Wikipedia and Wikidata APIs. The curated
  inputs are `src-data/local/battle_links.csv`, `src-data/local/coordinates_places.csv` and
  `src-data/local/commander_links.csv`.
- Do not correct a value that is what the source says. Add a row to `src-data/local/data_notes.csv`
  with the value, the problem and the source.
- A commander link identifies the person CDB90 lists. It does not correct who held the command, so
  never link whoever really commanded the unit in place of the listed person.

Exception to L1: the published tables in `data/` are about 1 MB and people use them straight from GitHub and Zenodo, so every output is `cache: false` and stays in git.
Exception to L2: `data/` holds the published tables (`data/relational/` csv, `data/flat/` csv and parquet) in git, for the same reason. `cdb90.sqlite3` is built by the pipeline and not tracked; it is a release asset.
Exception to C1: no cached outputs, so there is no remote and `.dvc/config` has none.
Exception to T1: the original data is in `src-data/` (git, under 4 MB), not `data/raw/`.
