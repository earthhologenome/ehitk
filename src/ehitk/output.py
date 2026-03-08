from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from rich.console import Console
from rich.table import Table


def render_or_export_rows(
    console: Console,
    headers: tuple[str, ...],
    rows: list[dict],
    *,
    title: str,
    csv_path: Path | None = None,
    tsv_path: Path | None = None,
) -> None:
    if csv_path is not None and tsv_path is not None:
        raise ValueError("Use only one of --csv or --tsv.")

    if csv_path is not None:
        _write_delimited_rows(csv_path, headers, rows, delimiter=",")
        console.print(f"Wrote {len(rows)} rows to {csv_path}.")
        return

    if tsv_path is not None:
        _write_delimited_rows(tsv_path, headers, rows, delimiter="\t")
        console.print(f"Wrote {len(rows)} rows to {tsv_path}.")
        return

    if not rows:
        console.print(f"No matching {title.lower()} found.")
        return

    table = Table(title=title)
    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*(str(row[header]) if row[header] is not None else "" for header in headers))

    console.print(table)


def _write_delimited_rows(
    path: Path,
    headers: tuple[str, ...],
    rows: Iterable[dict],
    *,
    delimiter: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow(headers)
        for row in rows:
            writer.writerow("" if row[header] is None else str(row[header]) for header in headers)
