"""Shared fixtures."""

import sqlite3
from pathlib import Path

import pytest

from scripts import sqlite as sqlite_script


@pytest.fixture(scope="session")
def sqlite_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the SQLite database in a temporary directory and return its path."""
    path = tmp_path_factory.mktemp("sqlite") / "cdb90.sqlite3"
    original = sqlite_script.OUTPUT
    sqlite_script.OUTPUT = path
    try:
        sqlite_script.main()
    finally:
        sqlite_script.OUTPUT = original
    sqlite3.connect(path).close()
    return path
