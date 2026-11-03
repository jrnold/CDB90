"""Tests for the Zenodo deposit and the release metadata."""

import json
import re
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml
from frictionless import validate

from scripts import zenodo


@pytest.fixture(scope="module")
def bundle(sqlite_db: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the deposit bundle in a temporary directory."""
    original = zenodo.SQLITE
    zenodo.SQLITE = sqlite_db
    try:
        out = tmp_path_factory.mktemp("bundle")
        zenodo.build_bundle(out)
    finally:
        zenodo.SQLITE = original
    return out


def test_bundle_holds_the_data_files(bundle: Path) -> None:
    """The deposit has the flat tables, SQLite, the relational zip, descriptor, README, licence."""
    assert {p.name for p in bundle.iterdir()} == {
        "battles.csv",
        "battles.parquet",
        "sides.csv",
        "sides.parquet",
        "cdb90.sqlite3",
        "relational-csv.zip",
        "datapackage.json",
        "README.md",
        "CODEBOOK.md",
        "original-documentation.txt",
        "AD1038724.pdf",
        "AD1038724.md",
        "LICENSE.md",
    }


def test_bundle_has_no_code(bundle: Path) -> None:
    """Nothing in the deposit is code."""
    assert not [p for p in bundle.iterdir() if p.suffix in {".py", ".R", ".sh", ".toml", ".lock"}]


def test_bundle_zip_lists_the_relational_tables(bundle: Path) -> None:
    """The zip has every relational CSV table."""
    expected = {f"relational/{p.name}" for p in Path("data/relational").glob("*.csv")}
    with zipfile.ZipFile(bundle / "relational-csv.zip") as archive:
        assert set(archive.namelist()) == expected


def test_bundle_data_package_is_valid(bundle: Path) -> None:
    """The bundle's data package finds its CSVs at the top level and validates."""
    report = validate(str(bundle / "datapackage.json"))
    assert report.valid, report.flatten(["type", "message"])


class Recorder:
    """Records the requests of a fake Zenodo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.state = "unsubmitted"

    def response(self, payload: dict[str, Any]) -> Any:
        """Return a fake response with ``payload``."""

        class Response:
            def raise_for_status(self) -> None: ...

            def json(self) -> dict[str, Any]:
                return payload

        return Response()

    def post(self, url: str, **_: object) -> Any:
        """Record a POST."""
        self.calls.append(("POST", url))
        links = {"bucket": "https://zenodo.test/bucket", "html": "https://zenodo.test/draft"}
        if url.endswith("/actions/publish"):
            return self.response({"links": {"html": "https://zenodo.test/record"}})
        return self.response({"id": 7, "links": links})

    def get(self, url: str, **_: object) -> Any:
        """Record a GET of an existing draft."""
        self.calls.append(("GET", url))
        state = self.state
        return self.response(
            {
                "id": 7,
                "state": state,
                "links": {
                    "bucket": "https://zenodo.test/bucket",
                    "html": "https://zenodo.test/draft",
                },
            }
        )

    def put(self, url: str, **_: object) -> Any:
        """Record a PUT."""
        self.calls.append(("PUT", url))
        return self.response({})


def run_deposit(
    monkeypatch: pytest.MonkeyPatch,
    bundle: Path,
    *,
    publish: bool,
    deposit_id: int | None = None,
    state: str = "unsubmitted",
) -> tuple[str, Any]:
    """Run ``deposit`` against the fake Zenodo."""
    recorder = Recorder()
    recorder.state = state
    monkeypatch.setattr(zenodo.requests, "get", recorder.get)
    monkeypatch.setattr(zenodo.requests, "post", recorder.post)
    monkeypatch.setattr(zenodo.requests, "put", recorder.put)
    files = sorted(p for p in bundle.iterdir() if p.is_file())
    url = zenodo.deposit(files, "token", sandbox=True, publish=publish, deposit_id=deposit_id)
    return url, recorder


def test_deposit_leaves_a_draft_by_default(monkeypatch: pytest.MonkeyPatch, bundle: Path) -> None:
    """Without ``publish`` the deposit is uploaded and described but not published."""
    url, recorder = run_deposit(monkeypatch, bundle, publish=False)
    assert url == "https://zenodo.test/draft"
    assert not any(url.endswith("/actions/publish") for _, url in recorder.calls)
    uploads = [
        url for method, url in recorder.calls if url.startswith("https://zenodo.test/bucket")
    ]
    assert len(uploads) == 13
    assert ("PUT", "https://sandbox.zenodo.org/api/deposit/depositions/7") in recorder.calls


def test_update_replaces_an_existing_draft(monkeypatch: pytest.MonkeyPatch, bundle: Path) -> None:
    """With an id, the existing draft is updated and no new deposit is created."""
    _, recorder = run_deposit(monkeypatch, bundle, publish=False, deposit_id=7)
    assert ("GET", "https://sandbox.zenodo.org/api/deposit/depositions/7") in recorder.calls
    assert not any(method == "POST" for method, _ in recorder.calls)


def test_update_refuses_a_published_deposit(monkeypatch: pytest.MonkeyPatch, bundle: Path) -> None:
    """A published deposit cannot be overwritten; it needs a new version."""
    with pytest.raises(SystemExit):
        run_deposit(monkeypatch, bundle, publish=False, deposit_id=7, state="done")


def test_deposit_publishes_only_when_asked(monkeypatch: pytest.MonkeyPatch, bundle: Path) -> None:
    """``publish`` adds the publish request."""
    url, recorder = run_deposit(monkeypatch, bundle, publish=True)
    assert url == "https://zenodo.test/record"
    assert recorder.calls[-1][1].endswith("/actions/publish")


def project_version() -> str:
    """Return the data version in ``src-data/version.txt``."""
    return Path("src-data/version.txt").read_text().strip()


def test_versions_agree() -> None:
    """Every place that records the version records the same one."""
    version = project_version()
    match = re.search(r'^version = "(.+)"$', Path("pyproject.toml").read_text(), re.MULTILINE)
    assert match is not None
    assert match.group(1) == version
    assert json.loads(Path("zenodo/metadata.json").read_text())["version"] == version
    assert yaml.safe_load(Path("CITATION.cff").read_text())["version"] == version
    assert json.loads(Path("datapackage.json").read_text())["version"] == version
    assert Path("data/relational/version.csv").read_text().split() == ['"version"', f'"{version}"']


def test_zenodo_metadata_has_required_fields() -> None:
    """Zenodo needs a type, title, creators, description and licence; the data is CC0."""
    metadata = json.loads(Path("zenodo/metadata.json").read_text())
    for field in ("upload_type", "title", "creators", "description", "license"):
        assert metadata[field]
    assert metadata["upload_type"] == "dataset"
    assert metadata["license"] == "cc0-1.0"
