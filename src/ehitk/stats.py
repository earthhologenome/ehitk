from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from rich.console import Console
from rich.table import Table

from ehitk.query import build_filtered_source_query, resolve_catalog_path

TOP_BREAKDOWN_ROWS = 5
QUALITY_CASE = """
CASE
    WHEN completeness >= 90 AND contamination <= 5 THEN 'high'
    WHEN completeness >= 50 AND contamination <= 10 THEN 'medium'
    ELSE 'low'
END
"""


def render_target_stats(
    console: Console,
    *,
    catalog_path: str,
    target: str,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
) -> None:
    resolved_catalog = resolve_catalog_path(catalog_path)
    base_sql, parameters = build_filtered_source_query(
        target,
        filters=filters,
        where=where,
    )

    with sqlite3.connect(resolved_catalog) as connection:
        connection.row_factory = sqlite3.Row

        if target == "hologenomes":
            _render_hologenome_stats(console, connection, base_sql, parameters)
            return
        if target == "mags":
            _render_mag_stats(console, connection, base_sql, parameters)
            return
        if target == "specimens":
            _render_specimen_stats(console, connection, base_sql, parameters)
            return

    raise ValueError(f"Unsupported stats target: {target}")


def _render_hologenome_stats(
    console: Console,
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> None:
    summary = _fetchone(
        connection,
        f"""
        SELECT
            COUNT(*) AS matched_hologenomes,
            COUNT(DISTINCT specimen_id) AS distinct_specimens,
            COUNT(DISTINCT release) AS distinct_releases,
            COUNT(DISTINCT host_species) AS distinct_host_species,
            COUNT(DISTINCT biome) AS distinct_biomes,
            SUM(CASE WHEN data IS NOT NULL THEN 1 ELSE 0 END) AS with_data,
            SUM(data) AS total_data_gb,
            AVG(data) AS avg_data_gb,
            MIN(data) AS min_data_gb,
            MAX(data) AS max_data_gb,
            SUM(CASE WHEN url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> '' THEN 1 ELSE 0 END) AS with_paired_urls,
            SUM(CASE WHEN url1 IS NULL OR url1 = '' OR url2 IS NULL OR url2 = '' THEN 1 ELSE 0 END) AS missing_paired_urls
        FROM ({base_sql}) AS filtered
        """,
        parameters,
    )
    if summary["matched_hologenomes"] == 0:
        console.print("No matching hologenomes found.")
        return

    _print_summary_lines(
        console,
        "Hologenome Stats",
        (
            ("Matched hologenomes", summary["matched_hologenomes"]),
            ("Distinct specimens", summary["distinct_specimens"]),
            ("Distinct releases", summary["distinct_releases"]),
            ("Distinct host species", summary["distinct_host_species"]),
            ("Distinct biomes", summary["distinct_biomes"]),
            ("With data", summary["with_data"]),
            ("Available data (GB total)", _format_gb(summary["total_data_gb"])),
            (
                "Data per hologenome (GB avg/min/max)",
                _format_range(summary["avg_data_gb"], summary["min_data_gb"], summary["max_data_gb"]),
            ),
            ("With paired URLs", summary["with_paired_urls"]),
            ("Missing paired URLs", summary["missing_paired_urls"]),
        ),
    )

    _render_breakdown(
        console,
        "Top sample types",
        "sample_type",
        _top_counts_with_data(connection, base_sql, parameters, "sample_type"),
        aggregate_header="data_gb",
        aggregate_key="data_gb",
    )
    _render_breakdown(
        console,
        "Top host species",
        "host_species",
        _top_counts_with_data(connection, base_sql, parameters, "host_species"),
        aggregate_header="data_gb",
        aggregate_key="data_gb",
    )
    _render_breakdown(
        console,
        "Top biomes",
        "biome",
        _top_counts_with_data(connection, base_sql, parameters, "biome"),
        aggregate_header="data_gb",
        aggregate_key="data_gb",
    )


def _render_mag_stats(
    console: Console,
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> None:
    summary = _fetchone(
        connection,
        f"""
        SELECT
            COUNT(*) AS matched_mags,
            COUNT(DISTINCT hologenome_id) AS distinct_hologenomes,
            COUNT(DISTINCT specimen_id) AS distinct_specimens,
            COUNT(DISTINCT host_species) AS distinct_host_species,
            COUNT(DISTINCT release) AS distinct_releases,
            SUM(CASE WHEN url IS NOT NULL AND url <> '' THEN 1 ELSE 0 END) AS with_urls,
            AVG(completeness) AS avg_completeness,
            MIN(completeness) AS min_completeness,
            MAX(completeness) AS max_completeness,
            AVG(contamination) AS avg_contamination,
            MIN(contamination) AS min_contamination,
            MAX(contamination) AS max_contamination
        FROM ({base_sql}) AS filtered
        """,
        parameters,
    )
    parent_data = _fetchone(
        connection,
        f"""
        SELECT
            COUNT(*) AS hologenomes_with_data,
            SUM(data) AS total_data_gb,
            AVG(data) AS avg_data_gb,
            MIN(data) AS min_data_gb,
            MAX(data) AS max_data_gb
        FROM (
            SELECT DISTINCT hologenome_id, data
            FROM ({base_sql}) AS filtered
            WHERE hologenome_id IS NOT NULL AND data IS NOT NULL
        ) AS parent_data
        """,
        parameters,
    )
    if summary["matched_mags"] == 0:
        console.print("No matching MAGs found.")
        return

    _print_summary_lines(
        console,
        "MAG Stats",
        (
            ("Matched MAGs", summary["matched_mags"]),
            ("Distinct hologenomes", summary["distinct_hologenomes"]),
            ("Distinct specimens", summary["distinct_specimens"]),
            ("Distinct host species", summary["distinct_host_species"]),
            ("Distinct releases", summary["distinct_releases"]),
            ("With URLs", summary["with_urls"]),
            ("Parent hologenomes with data", parent_data["hologenomes_with_data"]),
            ("Parent hologenome data (GB total)", _format_gb(parent_data["total_data_gb"])),
            (
                "Parent hologenome data (GB avg/min/max)",
                _format_range(
                    parent_data["avg_data_gb"],
                    parent_data["min_data_gb"],
                    parent_data["max_data_gb"],
                ),
            ),
            (
                "Completeness (avg/min/max)",
                _format_range(
                    summary["avg_completeness"],
                    summary["min_completeness"],
                    summary["max_completeness"],
                ),
            ),
            (
                "Contamination (avg/min/max)",
                _format_range(
                    summary["avg_contamination"],
                    summary["min_contamination"],
                    summary["max_contamination"],
                ),
            ),
        ),
    )

    _render_breakdown(
        console,
        "Quality distribution",
        "quality",
        _top_counts(connection, base_sql, parameters, QUALITY_CASE, limit=3),
    )
    _render_breakdown(
        console,
        "Top MAG genera",
        "mag_genus",
        _top_counts(
            connection,
            base_sql,
            parameters,
            "CASE WHEN mag_genus LIKE 'g__%' THEN substr(mag_genus, 4) ELSE mag_genus END",
        ),
    )
    _render_breakdown(
        console,
        "Top host species",
        "host_species",
        _top_counts(connection, base_sql, parameters, "host_species"),
    )


def _render_specimen_stats(
    console: Console,
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> None:
    summary = _fetchone(
        connection,
        f"""
        SELECT
            COUNT(*) AS matched_specimens,
            COUNT(DISTINCT host_taxid) AS distinct_host_taxids,
            COUNT(DISTINCT host_species) AS distinct_host_species,
            COUNT(DISTINCT host_genus) AS distinct_host_genera,
            COUNT(DISTINCT host_class) AS distinct_host_classes,
            SUM(CASE WHEN weight IS NOT NULL AND weight <> '' THEN 1 ELSE 0 END) AS with_weight,
            SUM(CASE WHEN length IS NOT NULL AND length <> '' THEN 1 ELSE 0 END) AS with_length
        FROM ({base_sql}) AS filtered
        """,
        parameters,
    )
    if summary["matched_specimens"] == 0:
        console.print("No matching specimens found.")
        return

    _print_summary_lines(
        console,
        "Specimen Stats",
        (
            ("Matched specimens", summary["matched_specimens"]),
            ("Distinct host taxids", summary["distinct_host_taxids"]),
            ("Distinct host species", summary["distinct_host_species"]),
            ("Distinct host genera", summary["distinct_host_genera"]),
            ("Distinct host classes", summary["distinct_host_classes"]),
            ("With weight", summary["with_weight"]),
            ("With length", summary["with_length"]),
        ),
    )

    _render_breakdown(
        console,
        "Top host species",
        "host_species",
        _top_counts(connection, base_sql, parameters, "host_species"),
    )
    _render_breakdown(
        console,
        "Top host orders",
        "host_order",
        _top_counts(connection, base_sql, parameters, "host_order"),
    )
    _render_breakdown(
        console,
        "Sex distribution",
        "sex",
        _top_counts(connection, base_sql, parameters, "sex", limit=10),
    )


def _print_summary_lines(
    console: Console,
    title: str,
    rows: tuple[tuple[str, Any], ...],
) -> None:
    console.print(f"[bold]{title}[/bold]")
    for label, value in rows:
        console.print(f"{label}: {value}")


def _render_breakdown(
    console: Console,
    title: str,
    value_header: str,
    rows: list[sqlite3.Row],
    *,
    aggregate_header: str | None = None,
    aggregate_key: str | None = None,
) -> None:
    if not rows:
        return

    table = Table(title=title)
    table.add_column(value_header)
    table.add_column("count", justify="right")
    if aggregate_header is not None and aggregate_key is not None:
        table.add_column(aggregate_header, justify="right")
    for row in rows:
        rendered_row = [str(row["value"]), str(row["count"])]
        if aggregate_header is not None and aggregate_key is not None:
            rendered_row.append(_format_gb(row[aggregate_key]))
        table.add_row(*rendered_row)
    console.print(table)


def _top_counts(
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
    expression: str,
    *,
    limit: int = TOP_BREAKDOWN_ROWS,
) -> list[sqlite3.Row]:
    return _fetchall(
        connection,
        f"""
        SELECT
            COALESCE(NULLIF(CAST({expression} AS TEXT), ''), '<missing>') AS value,
            COUNT(*) AS count
        FROM ({base_sql}) AS filtered
        GROUP BY value
        ORDER BY count DESC, value ASC
        LIMIT ?
        """,
        [*parameters, limit],
    )


def _top_counts_with_data(
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
    expression: str,
    *,
    limit: int = TOP_BREAKDOWN_ROWS,
) -> list[sqlite3.Row]:
    return _fetchall(
        connection,
        f"""
        SELECT
            COALESCE(NULLIF(CAST({expression} AS TEXT), ''), '<missing>') AS value,
            COUNT(*) AS count,
            COALESCE(SUM(COALESCE(data, 0)), 0) AS data_gb
        FROM ({base_sql}) AS filtered
        GROUP BY value
        ORDER BY count DESC, value ASC
        LIMIT ?
        """,
        [*parameters, limit],
    )


def _fetchone(
    connection: sqlite3.Connection,
    sql: str,
    parameters: list[Any],
) -> sqlite3.Row:
    return connection.execute(sql, parameters).fetchone()


def _fetchall(
    connection: sqlite3.Connection,
    sql: str,
    parameters: list[Any],
) -> list[sqlite3.Row]:
    return connection.execute(sql, parameters).fetchall()


def _format_range(avg_value: Any, min_value: Any, max_value: Any) -> str:
    if avg_value is None:
        return "n/a"
    return f"{avg_value:.2f} / {min_value:.2f} / {max_value:.2f}"


def _format_gb(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}"
