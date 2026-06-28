from __future__ import annotations

import importlib.util
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


update_db_list = _load("ehitk_update_db_list", "scripts/update_db_list.py")


def _records() -> dict:
    return {
        "hits": {
            "hits": [
                {
                    "doi": "10.5281/zenodo.111",
                    "metadata": {"version": "2026.05.01", "publication_date": "2026-05-01"},
                    "files": [
                        {"key": "ehitk-database-2026.05.01.sqlite", "size": 6_000_000}
                    ],
                },
                {
                    "doi": "10.5281/zenodo.222",
                    "metadata": {"version": "2026.06.28", "publication_date": "2026-06-28"},
                    "files": [
                        {"key": "ehitk-database-2026.06.28.sqlite", "size": 6_500_000}
                    ],
                },
            ]
        }
    }


def test_collect_versions_sorts_newest_first() -> None:
    rows = update_db_list.collect_versions(_records())
    assert [row["data_version"] for row in rows] == ["2026.06.28", "2026.05.01"]
    assert rows[0]["doi"] == "10.5281/zenodo.222"


def test_render_md_table_has_rows_and_doi_links() -> None:
    rows = update_db_list.collect_versions(_records())
    table = update_db_list.render_md_table(rows)
    assert "| Data version |" in table
    assert "2026.06.28" in table
    assert "https://doi.org/10.5281/zenodo.222" in table


def test_render_rst_table_uses_list_table() -> None:
    rows = update_db_list.collect_versions(_records())
    table = update_db_list.render_rst_table(rows)
    assert ".. list-table::" in table
    assert "2026.05.01" in table


def test_replace_region_only_touches_between_markers() -> None:
    text = "before\n<!-- db-list-start -->\nOLD\n<!-- db-list-end -->\nafter"
    updated = update_db_list.replace_region(
        text, "<!-- db-list-start -->", "<!-- db-list-end -->", "NEW"
    )
    assert "before" in updated and "after" in updated
    assert "OLD" not in updated
    assert "NEW" in updated


def test_replace_region_missing_markers_raises() -> None:
    with pytest.raises(update_db_list.DbListError):
        update_db_list.replace_region("no markers here", "<!-- s -->", "<!-- e -->", "x")


def test_update_files_writes_into_both_targets(tmp_path, monkeypatch) -> None:
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Title\n<!-- db-list-start -->\nold\n<!-- db-list-end -->\n", encoding="utf-8"
    )
    docs = tmp_path / "database.rst"
    docs.write_text(
        "Title\n=====\n.. db-list-start\n\nold\n\n.. db-list-end\n", encoding="utf-8"
    )
    monkeypatch.setattr(update_db_list, "README_PATH", readme)
    monkeypatch.setattr(update_db_list, "DOCS_PATH", docs)

    rows = update_db_list.collect_versions(_records())
    changed = update_db_list.update_files(rows, write=True)

    assert set(changed) == {readme, docs}
    assert "2026.06.28" in readme.read_text(encoding="utf-8")
    assert ".. list-table::" in docs.read_text(encoding="utf-8")
