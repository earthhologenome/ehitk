#!/usr/bin/env python3
"""Fetch a published database from Zenodo and embed it in the ehitk package.

By default this pulls the **latest** version published under the EHItk database
Zenodo concept (concept recid ``20430293`` / concept DOI
``10.5281/zenodo.20430293``), verifies it against its ``.sha256`` sidecar,
checks its ``schema_version`` is supported by this ``ehitk``, and writes it to
``src/ehitk/data/ehitk.sqlite``. Pass ``--data-version`` to pin an older
release instead.

This is a release/build-time tool (the maintainer runs it, or
``scripts/release.py`` calls it). It is never used at runtime.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ehitk.query import (  # noqa: E402
    UnsupportedSchemaVersionError,
    read_catalog_meta,
    validate_catalog_schema,
)

DEFAULT_ZENODO_URL = "https://zenodo.org"
DEFAULT_CONCEPT_RECID = "20430293"
DEFAULT_OUTPUT = ROOT / "src" / "ehitk" / "data" / "ehitk.sqlite"


class SyncError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncResult:
    data_version: str | None
    doi: str | None
    output: Path | None
    dry_run: bool


def select_record(records: dict, data_version: str | None = None) -> dict:
    """Pick the record to embed: a pinned data_version, or the latest published."""
    hits = records.get("hits", {}).get("hits", [])
    if not hits:
        raise SyncError("No records found under the Zenodo concept.")
    if data_version:
        for hit in hits:
            if str(hit.get("metadata", {}).get("version")) == str(data_version):
                return hit
        raise SyncError(
            f"No Zenodo version {data_version} found under the concept."
        )

    def sort_key(hit: dict) -> tuple[str, str]:
        meta = hit.get("metadata", {})
        return (str(meta.get("publication_date", "")), str(meta.get("version", "")))

    return sorted(hits, key=sort_key)[-1]


def record_data_version(record: dict) -> str | None:
    version = record.get("metadata", {}).get("version")
    return str(version) if version else None


def record_doi(record: dict) -> str | None:
    return record.get("doi") or record.get("links", {}).get("doi")


def _file_name(file_entry: dict) -> str:
    return str(file_entry.get("key") or file_entry.get("filename") or "")


def _file_url(file_entry: dict) -> str | None:
    links = file_entry.get("links", {})
    return links.get("download") or links.get("self")


def find_files(record: dict) -> tuple[dict, dict | None]:
    """Return the (.sqlite, .sha256-or-None) file entries from a record."""
    sqlite_file: dict | None = None
    sha_file: dict | None = None
    for file_entry in record.get("files", []):
        name = _file_name(file_entry)
        if name.endswith(".sqlite"):
            sqlite_file = file_entry
        elif name.endswith(".sha256"):
            sha_file = file_entry
    if sqlite_file is None:
        raise SyncError("Selected Zenodo record has no .sqlite file.")
    return sqlite_file, sha_file


def verify_sha256(data: bytes, sha256_text: str, *, name: str) -> None:
    expected = sha256_text.split()[0].strip().lower() if sha256_text.strip() else ""
    if not expected:
        raise SyncError(f"Empty checksum sidecar for {name}.")
    actual = hashlib.sha256(data).hexdigest()
    if expected != actual:
        raise SyncError(
            f"Checksum mismatch for {name}: expected {expected}, got {actual}."
        )


def fetch_and_embed(
    *,
    output: Path,
    data_version: str | None,
    concept_recid: str,
    zenodo_url: str,
    dry_run: bool,
    fetch_json,
    fetch_bytes,
    progress=None,
) -> SyncResult:
    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    # Zenodo caps unauthenticated page size at 25; sort newest-first so the
    # latest published version is always on the first page.
    records_url = (
        f"{zenodo_url.rstrip('/')}/api/records"
        f"?q=conceptrecid:{concept_recid}&all_versions=true&size=25&sort=mostrecent"
    )
    records = fetch_json(records_url)
    record = select_record(records, data_version)
    resolved_version = record_data_version(record)
    doi = record_doi(record)
    sqlite_file, sha_file = find_files(record)

    emit(
        f"Selected database {resolved_version or '(unknown version)'} "
        f"(DOI: {doi or 'n/a'}); file {_file_name(sqlite_file)}"
    )

    if dry_run:
        emit("Dry run: no download or write performed.")
        return SyncResult(resolved_version, doi, None, dry_run=True)

    sqlite_url = _file_url(sqlite_file)
    if not sqlite_url:
        raise SyncError("Selected .sqlite file has no download URL.")
    payload = fetch_bytes(sqlite_url)

    if sha_file is not None:
        sha_url = _file_url(sha_file)
        sha_text = fetch_bytes(sha_url).decode("utf-8") if sha_url else ""
        verify_sha256(payload, sha_text, name=_file_name(sqlite_file))
        emit("Checksum verified against .sha256 sidecar.")
    else:
        emit(
            "Warning: record has no .sha256 sidecar; skipping checksum verification "
            "(older deposit predating the artifact convention)."
        )

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(payload)
    try:
        try:
            validate_catalog_schema(temp_path)
        except UnsupportedSchemaVersionError as exc:
            raise SyncError(
                f"{exc} Update ehitk's readers and SUPPORTED_SCHEMA_VERSIONS, or "
                "pin a compatible release with --data-version."
            ) from exc
        meta = read_catalog_meta(temp_path)
        embedded_version = meta.get("data_version", resolved_version)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
    finally:
        temp_path.unlink(missing_ok=True)

    emit(f"Embedded database {embedded_version} -> {output}")
    return SyncResult(embedded_version, doi, output, dry_run=False)


def _requests_fetchers():
    import requests

    def fetch_json(url: str):
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()

    def fetch_bytes(url: str) -> bytes:
        response = requests.get(url, timeout=300)
        response.raise_for_status()
        return response.content

    return fetch_json, fetch_bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the embedded catalog. Default: src/ehitk/data/ehitk.sqlite.",
    )
    parser.add_argument(
        "--data-version",
        default=None,
        help="Pin a specific data_version (default: latest published).",
    )
    parser.add_argument(
        "--concept-recid",
        default=DEFAULT_CONCEPT_RECID,
        help=f"Zenodo database concept record id. Default: {DEFAULT_CONCEPT_RECID}.",
    )
    parser.add_argument(
        "--zenodo-url",
        default=DEFAULT_ZENODO_URL,
        help=f"Zenodo base URL. Default: {DEFAULT_ZENODO_URL}.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and print the version that would be embedded; download nothing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fetch_json, fetch_bytes = _requests_fetchers()
    result = fetch_and_embed(
        output=args.output,
        data_version=args.data_version,
        concept_recid=args.concept_recid,
        zenodo_url=args.zenodo_url,
        dry_run=args.dry_run,
        fetch_json=fetch_json,
        fetch_bytes=fetch_bytes,
        progress=lambda message: print(message),
    )
    if result.dry_run:
        print(f"Would embed data_version={result.data_version} (DOI: {result.doi})")
    else:
        print(f"data_version={result.data_version}")
        print(f"doi={result.doi}")
        print(f"output={result.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SyncError as exc:
        print(f"Catalog sync failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
