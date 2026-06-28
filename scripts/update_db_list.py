#!/usr/bin/env python3
"""Refresh the list of published database versions in the README and docs.

Reads every version published under the EHItk database Zenodo concept
(concept recid ``20430293``) and rewrites an auto-generated table between marker
comments in ``README.md`` (``<!-- db-list-start -->`` / ``<!-- db-list-end -->``)
and ``docs/database.rst`` (``.. db-list-start`` / ``.. db-list-end``).

Only the content between the markers is replaced, so hand-written prose is never
touched. If Zenodo is unreachable the existing tables are left as-is.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ZENODO_URL = "https://zenodo.org"
DEFAULT_CONCEPT_RECID = "20430293"
README_PATH = ROOT / "README.md"
DOCS_PATH = ROOT / "docs" / "database.rst"

MD_START = "<!-- db-list-start -->"
MD_END = "<!-- db-list-end -->"
RST_START = ".. db-list-start"
RST_END = ".. db-list-end"


class DbListError(RuntimeError):
    pass


def collect_versions(records: dict) -> list[dict]:
    """Extract sorted (newest first) version rows from a Zenodo records payload."""
    rows: list[dict] = []
    for hit in records.get("hits", {}).get("hits", []):
        meta = hit.get("metadata", {})
        data_version = meta.get("version")
        if not data_version:
            continue
        size = None
        for file_entry in hit.get("files", []):
            name = str(file_entry.get("key") or file_entry.get("filename") or "")
            if name.endswith(".sqlite"):
                size = file_entry.get("size")
        rows.append(
            {
                "data_version": str(data_version),
                "date": str(meta.get("publication_date", "")),
                "doi": hit.get("doi") or hit.get("links", {}).get("doi") or "",
                "size": size,
            }
        )
    rows.sort(key=lambda row: (row["date"], row["data_version"]), reverse=True)
    return rows


def _human_size(size: object) -> str:
    if not isinstance(size, (int, float)) or size <= 0:
        return "—"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def _doi_url(doi: str) -> str:
    if not doi:
        return ""
    return doi if doi.startswith("http") else f"https://doi.org/{doi}"


def render_md_table(rows: list[dict]) -> str:
    if not rows:
        return "_No published database versions found._"
    lines = [
        "| Data version | Published | Size | DOI |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        url = _doi_url(row["doi"])
        doi_cell = f"[{row['doi']}]({url})" if url else "—"
        lines.append(
            f"| {row['data_version']} | {row['date'] or '—'} | "
            f"{_human_size(row['size'])} | {doi_cell} |"
        )
    return "\n".join(lines)


def render_rst_table(rows: list[dict]) -> str:
    if not rows:
        return "No published database versions found."
    lines = [
        ".. list-table::",
        "   :header-rows: 1",
        "",
        "   * - Data version",
        "     - Published",
        "     - Size",
        "     - DOI",
    ]
    for row in rows:
        url = _doi_url(row["doi"])
        doi_cell = f"`{row['doi']} <{url}>`_" if url else "—"
        lines.extend(
            [
                f"   * - {row['data_version']}",
                f"     - {row['date'] or '—'}",
                f"     - {_human_size(row['size'])}",
                f"     - {doi_cell}",
            ]
        )
    return "\n".join(lines)


def replace_region(text: str, start: str, end: str, body: str) -> str:
    start_index = text.find(start)
    end_index = text.find(end)
    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise DbListError(
            f"Could not find markers {start!r} / {end!r} in the target file."
        )
    before = text[: start_index + len(start)]
    after = text[end_index:]
    return f"{before}\n\n{body}\n\n{after}"


def _requests_fetch_json(url: str):
    import requests

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def update_files(rows: list[dict], *, write: bool = True) -> list[Path]:
    changed: list[Path] = []
    targets = [
        (README_PATH, MD_START, MD_END, render_md_table(rows)),
        (DOCS_PATH, RST_START, RST_END, render_rst_table(rows)),
    ]
    for path, start, end, body in targets:
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = replace_region(original, start, end, body)
        if updated != original:
            changed.append(path)
            if write:
                path.write_text(updated, encoding="utf-8")
    return changed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
        "--check",
        action="store_true",
        help="Exit non-zero if the tables would change (do not write).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = (
        f"{args.zenodo_url.rstrip('/')}/api/records"
        f"?q=conceptrecid:{args.concept_recid}&all_versions=true&size=100"
    )
    try:
        records = _requests_fetch_json(url)
    except Exception as exc:  # network/parse failure: leave files unchanged
        print(f"Warning: could not fetch Zenodo versions ({exc}); leaving files unchanged.")
        return 0

    rows = collect_versions(records)
    changed = update_files(rows, write=not args.check)
    if args.check:
        if changed:
            print("Database list is out of date: " + ", ".join(p.name for p in changed))
            return 1
        print("Database list is up to date.")
        return 0
    if changed:
        print("Updated database list in: " + ", ".join(p.name for p in changed))
    else:
        print("Database list already up to date.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DbListError as exc:
        print(f"Database list update failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
