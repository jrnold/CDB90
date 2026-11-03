"""Build the data-only Zenodo deposit and upload it as a draft.

``bundle`` collects the data files (flat CSV and Parquet, SQLite, the relational CSV tables as one
zip, a data package for the flat CSVs, the codebook, the original CDB90 documentation, a README
and the licence) into ``dist/zenodo/``.
``deposit`` uploads them to Zenodo with the metadata in ``zenodo/metadata.json`` and leaves the
deposit as a draft; ``--publish`` publishes it, which mints a DOI and cannot be undone.
``--update ID`` replaces the files of an existing draft, and ``--new-version ID`` starts a new
version of a published record (``ID`` is the id of its latest version).

The token is read from the ``ZENODO_TOKEN`` environment variable. Use ``--sandbox`` to try the
upload on sandbox.zenodo.org first.
"""

import argparse
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import requests

BUNDLE = Path("dist/zenodo")
FLAT = Path("data/flat")
RELATIONAL = Path("data/relational")
SQLITE = Path("cdb90.sqlite3")
METADATA = Path("zenodo/metadata.json")
CODEBOOK = Path("docs/codebook.md")
ORIGINAL_DOCS = Path("src-data/M000121/README.TXT")
DOCS_DIR = Path("src-data/docs")
FLAT_FILES = [
    FLAT / f"{name}.{ext}"
    for name in ("battles", "sides", "narratives")
    for ext in ("csv", "parquet")
]
ZIP_TIME = (1980, 1, 1, 0, 0, 0)  # a fixed time, so the zip is the same on every build
SANDBOX_API = "https://sandbox.zenodo.org/api"
API = "https://zenodo.org/api"


def zip_relational(path: Path) -> None:
    """Zip the relational CSV tables into ``path``, in a fixed order with fixed times."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for table in sorted(RELATIONAL.glob("*.csv")):
            info = zipfile.ZipInfo(f"relational/{table.name}", ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, table.read_bytes())


def bundle_descriptor(path: Path) -> None:
    """Write the data package for the bundle, with the flat CSVs at the top level."""
    package = json.loads(Path("datapackage.json").read_text())
    for resource in package["resources"]:
        resource["path"] = Path(resource["path"]).name
    path.write_text(json.dumps(package, indent=2, ensure_ascii=False) + "\n")


def build_bundle(out: Path = BUNDLE) -> list[Path]:
    """Collect the files of the deposit in ``out`` and return their paths."""
    out.mkdir(parents=True, exist_ok=True)
    for source in [*FLAT_FILES, SQLITE]:
        (out / source.name).write_bytes(source.read_bytes())
    (out / "LICENSE.md").write_bytes(Path("data/LICENSE.md").read_bytes())
    (out / "README.md").write_bytes(Path("zenodo/README.md").read_bytes())
    (out / "CODEBOOK.md").write_bytes(CODEBOOK.read_bytes())
    (out / "original-documentation.txt").write_bytes(ORIGINAL_DOCS.read_bytes())
    for source in sorted(DOCS_DIR.glob("AD*.*")):
        (out / source.name).write_bytes(source.read_bytes())
    zip_relational(out / "relational-csv.zip")
    bundle_descriptor(out / "datapackage.json")
    return sorted(p for p in out.iterdir() if p.is_file())


def deposit(
    files: list[Path],
    token: str,
    *,
    sandbox: bool,
    publish: bool,
    deposit_id: int | None = None,
    new_version_of: int | None = None,
) -> str:
    """Upload ``files`` to a Zenodo deposit and return its web address.

    A new deposit is created; or, with ``deposit_id``, the files and metadata of an existing draft
    are replaced (files with the same name are overwritten); or, with ``new_version_of`` (the id of
    a published deposit), a new version of the record is started, its carried-over files are removed
    and the files and metadata are replaced.
    """
    base = SANDBOX_API if sandbox else API
    headers = {"Authorization": f"Bearer {token}"}
    if new_version_of is not None:
        started = requests.post(
            f"{base}/deposit/depositions/{new_version_of}/actions/newversion",
            headers=headers,
            timeout=60,
        )
        started.raise_for_status()
        created = requests.get(started.json()["links"]["latest_draft"], headers=headers, timeout=60)
    elif deposit_id is None:
        created = requests.post(f"{base}/deposit/depositions", json={}, headers=headers, timeout=60)
    else:
        created = requests.get(
            f"{base}/deposit/depositions/{deposit_id}", headers=headers, timeout=60
        )
    created.raise_for_status()
    draft = created.json()
    if draft.get("state") not in {None, "unsubmitted"}:
        message = (
            f"deposit {draft['id']} is {draft['state']}, not a draft; make a new version on Zenodo"
        )
        raise SystemExit(message)
    if new_version_of is not None:
        # a new version starts with the files of the last one: replace them all
        for carried in draft.get("files", []):
            removed = requests.delete(
                f"{base}/deposit/depositions/{draft['id']}/files/{carried['id']}",
                headers=headers,
                timeout=60,
            )
            removed.raise_for_status()
    for path in files:
        with path.open("rb") as f:
            upload = requests.put(
                f"{draft['links']['bucket']}/{path.name}", data=f, headers=headers, timeout=600
            )
        upload.raise_for_status()
    metadata = json.loads(METADATA.read_text())
    metadata["publication_date"] = datetime.now(UTC).date().isoformat()
    update = requests.put(
        f"{base}/deposit/depositions/{draft['id']}",
        json={"metadata": metadata},
        headers=headers,
        timeout=60,
    )
    update.raise_for_status()
    if publish:
        published = requests.post(
            f"{base}/deposit/depositions/{draft['id']}/actions/publish",
            headers=headers,
            timeout=60,
        )
        published.raise_for_status()
        return str(published.json()["links"]["html"])
    return str(draft["links"]["html"])


def main() -> None:
    """Run the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=["bundle", "deposit"])
    parser.add_argument("--sandbox", action="store_true", help="use sandbox.zenodo.org")
    parser.add_argument("--publish", action="store_true", help="publish the deposit (permanent)")
    parser.add_argument("--update", type=int, metavar="ID", help="update an existing draft")
    parser.add_argument(
        "--new-version", type=int, metavar="ID", help="make a new version of a published record"
    )
    args = parser.parse_args()
    if args.update is not None and args.new_version is not None:
        parser.error("use --update or --new-version, not both")
    files = build_bundle()
    for path in files:
        print(f"{path} ({path.stat().st_size:,} bytes)")
    if args.command == "deposit":
        token = os.environ.get("ZENODO_TOKEN")
        if token is None or token == "":
            raise SystemExit("set ZENODO_TOKEN to a Zenodo access token")
        url = deposit(
            files,
            token,
            sandbox=args.sandbox,
            publish=args.publish,
            deposit_id=args.update,
            new_version_of=args.new_version,
        )
        print(f"{'Published' if args.publish else 'Draft'}: {url}")


if __name__ == "__main__":
    main()
