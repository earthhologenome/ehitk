from __future__ import annotations

import importlib.util
import hashlib
from pathlib import Path
import sqlite3
import sys


def _load_release_module():
    module_path = Path("scripts/release.py")
    spec = importlib.util.spec_from_file_location("ehitk_release_script", module_path)
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load scripts/release.py for testing.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_update_pyproject_version_rewrites_single_version_line() -> None:
    release = _load_release_module()
    content = '[project]\nname = "ehitk"\nversion = "1.0.1"\n'
    updated = release.update_pyproject_version(content, "1.0.2")
    assert 'version = "1.0.2"' in updated
    assert 'version = "1.0.1"' not in updated


def test_update_citation_version_rewrites_release_metadata() -> None:
    release = _load_release_module()
    content = 'cff-version: 1.2.0\nversion: "1.0.1"\ndate-released: 2026-03-18\n'
    updated = release.update_citation_version(content, "1.0.2", "2026-03-19")
    assert 'version: "1.0.2"' in updated
    assert "date-released: 2026-03-19" in updated
    assert 'version: "1.0.1"' not in updated


def test_update_codemeta_version_rewrites_release_metadata() -> None:
    release = _load_release_module()
    content = '{"name": "EHItk", "version": "1.0.1", "datePublished": "2026-03-18"}'
    updated = release.update_codemeta_version(content, "1.0.2", "2026-03-19")
    assert '"version": "1.0.2"' in updated
    assert '"datePublished": "2026-03-19"' in updated
    assert updated.endswith("\n")


def test_release_changelog_moves_unreleased_section_into_new_version() -> None:
    release = _load_release_module()
    content = """# Changelog

## [Unreleased]

### Added

- New feature

### Fixed

- Important bug fix

## [1.0.1] - 2026-03-18

### Added

- Previous release item
"""
    updated = release.release_changelog(content, "1.0.2", "2026-03-19")
    assert "## [Unreleased]" in updated
    assert "- No unreleased changes yet." in updated
    assert "## [1.0.2] - 2026-03-19" in updated
    assert "- New feature" in updated
    assert "- Important bug fix" in updated
    assert "## [1.0.1] - 2026-03-18" in updated


def test_write_database_release_artifacts_falls_back_to_ehitk_version(tmp_path) -> None:
    # A catalog without catalog_meta (here a non-sqlite blob) names the artifact
    # by the ehitk version.
    release = _load_release_module()
    source_database = tmp_path / "ehitk.sqlite"
    source_database.write_bytes(b"sqlite catalog")
    release_dir = tmp_path / "dist"

    release.PACKAGE_DB_PATH = source_database
    release.DATABASE_RELEASE_DIR = release_dir
    artifact, checksum_file = release.write_database_release_artifacts("1.2.3")

    expected_checksum = hashlib.sha256(b"sqlite catalog").hexdigest()
    assert artifact == release_dir / "ehitk-database-1.2.3.sqlite"
    assert artifact.read_bytes() == b"sqlite catalog"
    assert checksum_file == release_dir / "ehitk-database-1.2.3.sqlite.sha256"
    assert checksum_file.read_text(encoding="utf-8") == (
        f"{expected_checksum}  ehitk-database-1.2.3.sqlite\n"
    )


def test_write_database_release_artifacts_names_by_data_version(tmp_path) -> None:
    release = _load_release_module()
    source_database = tmp_path / "ehitk.sqlite"
    connection = sqlite3.connect(source_database)
    connection.execute("CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute(
        "INSERT INTO catalog_meta (key, value) VALUES ('data_version', '2026.06.28')"
    )
    connection.commit()
    connection.close()
    release_dir = tmp_path / "dist"

    release.PACKAGE_DB_PATH = source_database
    release.DATABASE_RELEASE_DIR = release_dir
    artifact, checksum_file = release.write_database_release_artifacts("1.2.3")

    assert artifact == release_dir / "ehitk-database-2026.06.28.sqlite"
    assert checksum_file == release_dir / "ehitk-database-2026.06.28.sqlite.sha256"
    assert "ehitk-database-2026.06.28.sqlite" in checksum_file.read_text(encoding="utf-8")
