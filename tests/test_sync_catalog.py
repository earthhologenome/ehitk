from __future__ import annotations

import hashlib
import importlib.util
import sqlite3
from pathlib import Path
import sys

import pytest


def _load(name: str, relative: str):
    module_path = Path(relative)
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sync_catalog = _load("ehitk_sync_catalog", "scripts/sync_catalog.py")


def _records(*versions: tuple[str, str]) -> dict:
    hits = []
    for version, date in versions:
        hits.append(
            {
                "doi": f"10.5281/zenodo.{version.replace('.', '')}",
                "metadata": {"version": version, "publication_date": date},
                "files": [
                    {
                        "key": f"ehitk-database-{version}.sqlite",
                        "size": 100,
                        "links": {"self": f"https://zenodo.test/{version}.sqlite"},
                    },
                    {
                        "key": f"ehitk-database-{version}.sqlite.sha256",
                        "links": {"self": f"https://zenodo.test/{version}.sha256"},
                    },
                ],
            }
        )
    return {"hits": {"hits": hits}}


def test_select_record_picks_latest_by_date() -> None:
    records = _records(("2026.05.01", "2026-05-01"), ("2026.06.28", "2026-06-28"))
    chosen = sync_catalog.select_record(records)
    assert sync_catalog.record_data_version(chosen) == "2026.06.28"


def test_select_record_pins_requested_version() -> None:
    records = _records(("2026.05.01", "2026-05-01"), ("2026.06.28", "2026-06-28"))
    chosen = sync_catalog.select_record(records, "2026.05.01")
    assert sync_catalog.record_data_version(chosen) == "2026.05.01"


def test_select_record_unknown_version_raises() -> None:
    records = _records(("2026.06.28", "2026-06-28"))
    with pytest.raises(sync_catalog.SyncError):
        sync_catalog.select_record(records, "1999.01.01")


def test_find_files_returns_sqlite_and_sha() -> None:
    record = _records(("2026.06.28", "2026-06-28"))["hits"]["hits"][0]
    sqlite_file, sha_file = sync_catalog.find_files(record)
    assert sqlite_file["key"].endswith(".sqlite")
    assert sha_file["key"].endswith(".sha256")


def test_verify_sha256_roundtrip() -> None:
    data = b"catalog-bytes"
    digest = hashlib.sha256(data).hexdigest()
    sync_catalog.verify_sha256(data, f"{digest}  ehitk-database-x.sqlite\n", name="x")
    with pytest.raises(sync_catalog.SyncError):
        sync_catalog.verify_sha256(data, "deadbeef  x", name="x")


def _build_catalog_bytes(tmp_path: Path, schema_version: int) -> bytes:
    catalog = tmp_path / "src.sqlite"
    connection = sqlite3.connect(catalog)
    connection.execute(
        "CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO catalog_meta (key, value) VALUES (?, ?)",
        [("data_version", "2026.06.28"), ("schema_version", str(schema_version))],
    )
    connection.commit()
    connection.close()
    return catalog.read_bytes()


def test_fetch_and_embed_writes_supported_catalog(tmp_path) -> None:
    payload = _build_catalog_bytes(tmp_path, schema_version=1)
    sha = f"{hashlib.sha256(payload).hexdigest()}  ehitk-database-2026.06.28.sqlite\n"
    output = tmp_path / "out" / "ehitk.sqlite"

    def fetch_json(url):
        return _records(("2026.06.28", "2026-06-28"))

    def fetch_bytes(url):
        return payload if url.endswith(".sqlite") else sha.encode("utf-8")

    result = sync_catalog.fetch_and_embed(
        output=output,
        data_version=None,
        concept_recid="20430293",
        zenodo_url="https://zenodo.test",
        dry_run=False,
        fetch_json=fetch_json,
        fetch_bytes=fetch_bytes,
    )
    assert result.data_version == "2026.06.28"
    assert output.read_bytes() == payload


def test_fetch_and_embed_rejects_unsupported_schema(tmp_path) -> None:
    payload = _build_catalog_bytes(tmp_path, schema_version=999)
    sha = f"{hashlib.sha256(payload).hexdigest()}  ehitk-database-2026.06.28.sqlite\n"
    output = tmp_path / "out" / "ehitk.sqlite"

    def fetch_json(url):
        return _records(("2026.06.28", "2026-06-28"))

    def fetch_bytes(url):
        return payload if url.endswith(".sqlite") else sha.encode("utf-8")

    with pytest.raises(sync_catalog.SyncError):
        sync_catalog.fetch_and_embed(
            output=output,
            data_version=None,
            concept_recid="20430293",
            zenodo_url="https://zenodo.test",
            dry_run=False,
            fetch_json=fetch_json,
            fetch_bytes=fetch_bytes,
        )
    assert not output.exists()


def test_fetch_and_embed_dry_run_writes_nothing(tmp_path) -> None:
    output = tmp_path / "out" / "ehitk.sqlite"

    def fetch_json(url):
        return _records(("2026.06.28", "2026-06-28"))

    def fetch_bytes(url):  # pragma: no cover - must not be called in dry run
        raise AssertionError("dry run must not download")

    result = sync_catalog.fetch_and_embed(
        output=output,
        data_version=None,
        concept_recid="20430293",
        zenodo_url="https://zenodo.test",
        dry_run=True,
        fetch_json=fetch_json,
        fetch_bytes=fetch_bytes,
    )
    assert result.dry_run is True
    assert result.data_version == "2026.06.28"
    assert not output.exists()
