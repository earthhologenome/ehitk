#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = ROOT / "pyproject.toml"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
CITATION_PATH = ROOT / "CITATION.cff"
CODEMETA_PATH = ROOT / "codemeta.json"
PACKAGE_DB_PATH = ROOT / "src" / "ehitk" / "data" / "ehitk.sqlite"
LEGACY_SOURCE_DB_PATH = ROOT / "data" / "ehitk.sqlite"
DATABASE_RELEASE_DIR = ROOT / "dist"
UNRELEASED_HEADER = "## [Unreleased]"
UNRELEASED_PLACEHOLDER = "### Added\n\n- No unreleased changes yet.\n"


class ReleaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleasePlan:
    version: str
    release_date: str
    run_tests: bool
    run_build: bool
    run_twine_check: bool
    sync_database: bool
    database_artifact: bool
    dry_run: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare an EHItk release by syncing the bundled database, cutting the "
            "CHANGELOG entry from Unreleased, updating pyproject.toml, and running "
            "release checks."
        )
    )
    parser.add_argument(
        "version",
        help="Release version to write into pyproject.toml and CHANGELOG.md.",
    )
    parser.add_argument(
        "--date",
        dest="release_date",
        default=date.today().isoformat(),
        help="Release date for the changelog entry in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned changes without modifying files or running commands.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running pytest.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip building sdist and wheel.",
    )
    parser.add_argument(
        "--skip-twine-check",
        action="store_true",
        help="Skip twine validation of built artifacts.",
    )
    parser.add_argument(
        "--skip-db-sync",
        action="store_true",
        help="Skip legacy database synchronization checks.",
    )
    parser.add_argument(
        "--skip-db-artifact",
        action="store_true",
        help="Skip writing a versioned SQLite database artifact and checksum into dist/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_version(args.version)
    validate_release_date(args.release_date)

    plan = ReleasePlan(
        version=args.version,
        release_date=args.release_date,
        run_tests=not args.skip_tests,
        run_build=not args.skip_build,
        run_twine_check=not args.skip_twine_check,
        sync_database=not args.skip_db_sync,
        database_artifact=not args.skip_db_artifact,
        dry_run=args.dry_run,
    )

    pyproject_before = PYPROJECT_PATH.read_text(encoding="utf-8")
    changelog_before = CHANGELOG_PATH.read_text(encoding="utf-8")
    citation_before = CITATION_PATH.read_text(encoding="utf-8")
    codemeta_before = CODEMETA_PATH.read_text(encoding="utf-8")

    pyproject_after = update_pyproject_version(pyproject_before, plan.version)
    changelog_after = release_changelog(changelog_before, plan.version, plan.release_date)
    citation_after = update_citation_version(citation_before, plan.version, plan.release_date)
    codemeta_after = update_codemeta_version(codemeta_before, plan.version, plan.release_date)

    changed_files = []
    if pyproject_before != pyproject_after:
        changed_files.append(PYPROJECT_PATH.relative_to(ROOT).as_posix())
    if changelog_before != changelog_after:
        changed_files.append(CHANGELOG_PATH.relative_to(ROOT).as_posix())
    if citation_before != citation_after:
        changed_files.append(CITATION_PATH.relative_to(ROOT).as_posix())
    if codemeta_before != codemeta_after:
        changed_files.append(CODEMETA_PATH.relative_to(ROOT).as_posix())
    if plan.sync_database and database_needs_sync():
        changed_files.append(PACKAGE_DB_PATH.relative_to(ROOT).as_posix())

    print_release_plan(plan, changed_files)
    if plan.dry_run:
        return 0

    if plan.sync_database:
        sync_database()

    if plan.database_artifact:
        write_database_release_artifacts(plan.version)

    if pyproject_before != pyproject_after:
        PYPROJECT_PATH.write_text(pyproject_after, encoding="utf-8")

    if changelog_before != changelog_after:
        CHANGELOG_PATH.write_text(changelog_after, encoding="utf-8")

    if citation_before != citation_after:
        CITATION_PATH.write_text(citation_after, encoding="utf-8")

    if codemeta_before != codemeta_after:
        CODEMETA_PATH.write_text(codemeta_after, encoding="utf-8")

    if plan.run_tests:
        require_module("pytest")
        run_command([sys.executable, "-m", "pytest"])
    if plan.run_build:
        require_module("build")
        run_command([sys.executable, "-m", "build"])
    if plan.run_twine_check:
        require_module("twine")
        distributions = [
            f"dist/ehitk-{plan.version}.tar.gz",
            f"dist/ehitk-{plan.version}-py3-none-any.whl",
        ]
        run_command([sys.executable, "-m", "twine", "check", *distributions])

    print()
    print("Release preparation completed.")
    print(f"Next steps:")
    print(f"1. Review changes: git diff")
    print(f"2. Commit them: git commit -am \"Release v{plan.version}\"")
    print(f"3. Tag the release: git tag v{plan.version}")
    print(f"4. Push branch and tag: git push origin main && git push origin v{plan.version}")
    print("5. If PyPI Trusted Publishing is configured, GitHub Actions will publish automatically.")
    return 0


def validate_version(version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ReleaseError(
            f"Unsupported version format: {version}. Expected semantic version like 1.2.3."
        )


def validate_release_date(release_date: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", release_date):
        raise ReleaseError(
            f"Unsupported release date format: {release_date}. Expected YYYY-MM-DD."
        )


def update_pyproject_version(content: str, version: str) -> str:
    updated, count = re.subn(
        r'(?m)^version = "[^"]+"$',
        f'version = "{version}"',
        content,
        count=1,
    )
    if count != 1:
        raise ReleaseError("Could not find a unique version line in pyproject.toml.")
    return updated


def update_citation_version(content: str, version: str, release_date: str) -> str:
    updated, version_count = re.subn(
        r'(?m)^version: "[^"]+"$',
        f'version: "{version}"',
        content,
        count=1,
    )
    updated, date_count = re.subn(
        r"(?m)^date-released: \d{4}-\d{2}-\d{2}$",
        f"date-released: {release_date}",
        updated,
        count=1,
    )
    if version_count != 1 or date_count != 1:
        raise ReleaseError("Could not update version and date-released in CITATION.cff.")
    return updated


def update_codemeta_version(content: str, version: str, release_date: str) -> str:
    metadata = json.loads(content)
    metadata["version"] = version
    metadata["datePublished"] = release_date
    return json.dumps(metadata, indent=2) + "\n"


def release_changelog(content: str, version: str, release_date: str) -> str:
    if f"## [{version}] -" in content:
        raise ReleaseError(f"CHANGELOG.md already contains an entry for version {version}.")

    unreleased_start = content.find(UNRELEASED_HEADER)
    if unreleased_start == -1:
        raise ReleaseError("CHANGELOG.md does not contain an [Unreleased] section.")

    next_section = content.find("\n## [", unreleased_start + len(UNRELEASED_HEADER))
    if next_section == -1:
        unreleased_block = content[unreleased_start:]
        remainder = ""
    else:
        unreleased_block = content[unreleased_start:next_section]
        remainder = content[next_section:]

    header_line, _, unreleased_body = unreleased_block.partition("\n")
    normalized_body = unreleased_body.strip("\n")
    if not normalized_body.strip():
        raise ReleaseError("The [Unreleased] section is empty. Add release notes before cutting a release.")

    release_body = normalized_body
    if release_body == UNRELEASED_PLACEHOLDER.strip():
        raise ReleaseError(
            "The [Unreleased] section only contains the placeholder entry. "
            "Replace it with real release notes before cutting a release."
        )

    released_section = f"## [{version}] - {release_date}\n\n{release_body}\n\n"
    new_unreleased = f"{header_line}\n\n{UNRELEASED_PLACEHOLDER}"
    return content[:unreleased_start] + new_unreleased + "\n" + released_section + remainder.lstrip("\n")


def database_needs_sync() -> bool:
    if not PACKAGE_DB_PATH.exists():
        raise ReleaseError(f"Packaged database not found: {PACKAGE_DB_PATH}")
    if not LEGACY_SOURCE_DB_PATH.exists():
        return False
    return LEGACY_SOURCE_DB_PATH.read_bytes() != PACKAGE_DB_PATH.read_bytes()


def sync_database() -> None:
    if not PACKAGE_DB_PATH.exists():
        raise ReleaseError(f"Packaged database not found: {PACKAGE_DB_PATH}")
    if not LEGACY_SOURCE_DB_PATH.exists():
        print(
            "No legacy root-level database found; using "
            f"{PACKAGE_DB_PATH.relative_to(ROOT)} as the canonical release database."
        )
        return
    PACKAGE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LEGACY_SOURCE_DB_PATH, PACKAGE_DB_PATH)
    print(
        f"Synchronized {LEGACY_SOURCE_DB_PATH.relative_to(ROOT)} -> "
        f"{PACKAGE_DB_PATH.relative_to(ROOT)}"
    )


def read_catalog_data_version(catalog_path: Path) -> str | None:
    """Return the bundled catalog's ``data_version`` from ``catalog_meta``.

    Returns ``None`` for catalogs that cannot be opened or predate the
    ``catalog_meta`` table so the caller can fall back to the ehitk version.
    """
    try:
        connection = sqlite3.connect(f"file:{catalog_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return None
    try:
        exists = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'catalog_meta'"
        ).fetchone()
        if exists is None:
            return None
        row = connection.execute(
            "SELECT value FROM catalog_meta WHERE key = 'data_version'"
        ).fetchone()
    except sqlite3.Error:
        return None
    finally:
        connection.close()
    return row[0] if row and row[0] else None


def write_database_release_artifacts(version: str) -> tuple[Path, Path]:
    if not PACKAGE_DB_PATH.exists():
        raise ReleaseError(f"Packaged database not found: {PACKAGE_DB_PATH}")
    DATABASE_RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    data_version = read_catalog_data_version(PACKAGE_DB_PATH)
    if data_version:
        artifact_version = data_version
    else:
        artifact_version = version
        print(
            "Warning: bundled catalog has no data_version in catalog_meta; "
            f"naming the database artifact by the ehitk version ({version}). "
            "The canonical artifact and Zenodo deposit are produced by ehitk-build."
        )

    artifact = DATABASE_RELEASE_DIR / f"ehitk-database-{artifact_version}.sqlite"
    checksum_file = DATABASE_RELEASE_DIR / f"{artifact.name}.sha256"
    shutil.copy2(PACKAGE_DB_PATH, artifact)
    checksum = file_sha256(artifact)
    checksum_file.write_text(f"{checksum}  {artifact.name}\n", encoding="utf-8")
    print(
        "Wrote database release artifact: "
        f"{display_path(artifact)} and {display_path(checksum_file)}"
    )
    return artifact, checksum_file


def file_sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def display_path(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def require_module(module_name: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module_name}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    install_hint = {
        "pytest": ".[dev,release]",
        "build": ".[release]",
        "twine": ".[release]",
    }.get(module_name, ".[release]")
    raise ReleaseError(
        f"Missing required module '{module_name}'. Install the required tooling with: "
        f"{sys.executable} -m pip install '{install_hint}'"
    )


def run_command(command: list[str], *, shell: bool = False) -> None:
    rendered = " ".join(command)
    print(f"Running: {rendered}")
    subprocess.run(
        rendered if shell else command,
        cwd=ROOT,
        shell=shell,
        check=True,
    )


def print_release_plan(plan: ReleasePlan, changed_files: list[str]) -> None:
    print(f"Preparing EHItk release {plan.version} ({plan.release_date})")
    print(f"- dry run: {'yes' if plan.dry_run else 'no'}")
    print(f"- sync database: {'yes' if plan.sync_database else 'no'}")
    print(f"- run tests: {'yes' if plan.run_tests else 'no'}")
    print(f"- run build: {'yes' if plan.run_build else 'no'}")
    print(f"- run twine check: {'yes' if plan.run_twine_check else 'no'}")
    print(f"- write database artifact: {'yes' if plan.database_artifact else 'no'}")
    if changed_files:
        print("- files to update:")
        for changed_file in changed_files:
            print(f"  - {changed_file}")
    else:
        print("- no file content changes needed before checks")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseError as exc:
        print(f"Release preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
