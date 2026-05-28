from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class StatBreakdown:
    title: str
    value_header: str
    rows: tuple[dict[str, Any], ...]
    aggregate_header: str | None = None
    aggregate_key: str | None = None


@dataclass(frozen=True, slots=True)
class TargetStats:
    target: str
    title: str
    summary: dict[str, Any]
    summary_labels: tuple[tuple[str, str], ...]
    breakdowns: tuple[StatBreakdown, ...]
    empty_message: str | None = None


def target_stats(
    *,
    catalog_path: str,
    target: str,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
) -> TargetStats:
    resolved_catalog = resolve_catalog_path(catalog_path)
    base_sql, parameters = build_filtered_source_query(
        target,
        filters=filters,
        where=where,
    )

    with sqlite3.connect(resolved_catalog) as connection:
        connection.row_factory = sqlite3.Row

        if target == "hologenomes":
            return _hologenome_stats(connection, base_sql, parameters)
        if target == "mags":
            return _mag_stats(connection, base_sql, parameters)
        if target == "specimens":
            return _specimen_stats(connection, base_sql, parameters)

    raise ValueError(f"Unsupported stats target: {target}")


def render_target_stats(
    console: Console,
    *,
    catalog_path: str,
    target: str,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
) -> None:
    _render_stats(console, target_stats(
        catalog_path=catalog_path,
        target=target,
        filters=filters,
        where=where,
    ))


def _hologenome_stats(
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> TargetStats:
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
        return TargetStats(
            target="hologenomes",
            title="Hologenome Stats",
            summary=dict(summary),
            summary_labels=(),
            breakdowns=(),
            empty_message="No matching hologenomes found.",
        )

    return TargetStats(
        target="hologenomes",
        title="Hologenome Stats",
        summary=dict(summary),
        summary_labels=(
            ("Matched hologenomes", "matched_hologenomes"),
            ("Distinct specimens", "distinct_specimens"),
            ("Distinct releases", "distinct_releases"),
            ("Distinct host species", "distinct_host_species"),
            ("Distinct biomes", "distinct_biomes"),
            ("With data", "with_data"),
            ("Available data (GB total)", "total_data_gb"),
            ("Data per hologenome (GB avg/min/max)", "data_gb_range"),
            ("With paired URLs", "with_paired_urls"),
            ("Missing paired URLs", "missing_paired_urls"),
        ),
        breakdowns=(
            StatBreakdown(
                title="Top sample types",
                value_header="sample_type",
                rows=_rows_as_dicts(_top_counts_with_data(connection, base_sql, parameters, "sample_type")),
                aggregate_header="data_gb",
                aggregate_key="data_gb",
            ),
            StatBreakdown(
                title="Top host species",
                value_header="host_species",
                rows=_rows_as_dicts(_top_counts_with_data(connection, base_sql, parameters, "host_species")),
                aggregate_header="data_gb",
                aggregate_key="data_gb",
            ),
            StatBreakdown(
                title="Top biomes",
                value_header="biome",
                rows=_rows_as_dicts(_top_counts_with_data(connection, base_sql, parameters, "biome")),
                aggregate_header="data_gb",
                aggregate_key="data_gb",
            ),
        ),
    )


def _mag_stats(
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> TargetStats:
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
    merged_summary = {**dict(summary), **dict(parent_data)}
    if summary["matched_mags"] == 0:
        return TargetStats(
            target="mags",
            title="MAG Stats",
            summary=merged_summary,
            summary_labels=(),
            breakdowns=(),
            empty_message="No matching MAGs found.",
        )

    return TargetStats(
        target="mags",
        title="MAG Stats",
        summary=merged_summary,
        summary_labels=(
            ("Matched MAGs", "matched_mags"),
            ("Distinct hologenomes", "distinct_hologenomes"),
            ("Distinct specimens", "distinct_specimens"),
            ("Distinct host species", "distinct_host_species"),
            ("Distinct releases", "distinct_releases"),
            ("With URLs", "with_urls"),
            ("Parent hologenomes with data", "hologenomes_with_data"),
            ("Parent hologenome data (GB total)", "total_data_gb"),
            ("Parent hologenome data (GB avg/min/max)", "parent_data_gb_range"),
            ("Completeness (avg/min/max)", "completeness_range"),
            ("Contamination (avg/min/max)", "contamination_range"),
        ),
        breakdowns=(
            StatBreakdown(
                title="Quality distribution",
                value_header="quality",
                rows=_rows_as_dicts(_top_counts(connection, base_sql, parameters, QUALITY_CASE, limit=3)),
            ),
            StatBreakdown(
                title="Top MAG genera",
                value_header="mag_genus",
                rows=_rows_as_dicts(_top_counts(
                    connection,
                    base_sql,
                    parameters,
                    "CASE WHEN mag_genus LIKE 'g__%' THEN substr(mag_genus, 4) ELSE mag_genus END",
                )),
            ),
            StatBreakdown(
                title="Top host species",
                value_header="host_species",
                rows=_rows_as_dicts(_top_counts(connection, base_sql, parameters, "host_species")),
            ),
        ),
    )


def _specimen_stats(
    connection: sqlite3.Connection,
    base_sql: str,
    parameters: list[Any],
) -> TargetStats:
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
        return TargetStats(
            target="specimens",
            title="Specimen Stats",
            summary=dict(summary),
            summary_labels=(),
            breakdowns=(),
            empty_message="No matching specimens found.",
        )

    return TargetStats(
        target="specimens",
        title="Specimen Stats",
        summary=dict(summary),
        summary_labels=(
            ("Matched specimens", "matched_specimens"),
            ("Distinct host taxids", "distinct_host_taxids"),
            ("Distinct host species", "distinct_host_species"),
            ("Distinct host genera", "distinct_host_genera"),
            ("Distinct host classes", "distinct_host_classes"),
            ("With weight", "with_weight"),
            ("With length", "with_length"),
        ),
        breakdowns=(
            StatBreakdown(
                title="Top host species",
                value_header="host_species",
                rows=_rows_as_dicts(_top_counts(connection, base_sql, parameters, "host_species")),
            ),
            StatBreakdown(
                title="Top host orders",
                value_header="host_order",
                rows=_rows_as_dicts(_top_counts(connection, base_sql, parameters, "host_order")),
            ),
            StatBreakdown(
                title="Sex distribution",
                value_header="sex",
                rows=_rows_as_dicts(_top_counts(connection, base_sql, parameters, "sex", limit=10)),
            ),
        ),
    )


def _render_stats(console: Console, stats: TargetStats) -> None:
    if stats.empty_message is not None:
        console.print(stats.empty_message)
        return

    _print_summary_lines(
        console,
        stats.title,
        tuple(
            (label, _format_summary_value(stats, key))
            for label, key in stats.summary_labels
        ),
    )
    for breakdown in stats.breakdowns:
        _render_breakdown(
            console,
            breakdown.title,
            breakdown.value_header,
            breakdown.rows,
            aggregate_header=breakdown.aggregate_header,
            aggregate_key=breakdown.aggregate_key,
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
    rows: list[sqlite3.Row] | tuple[dict[str, Any], ...],
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


def _rows_as_dicts(rows: list[sqlite3.Row]) -> tuple[dict[str, Any], ...]:
    return tuple(dict(row) for row in rows)


def _format_summary_value(stats: TargetStats, key: str) -> Any:
    summary = stats.summary
    if key == "data_gb_range":
        return _format_range(summary["avg_data_gb"], summary["min_data_gb"], summary["max_data_gb"])
    if key == "parent_data_gb_range":
        return _format_range(summary["avg_data_gb"], summary["min_data_gb"], summary["max_data_gb"])
    if key == "completeness_range":
        return _format_range(summary["avg_completeness"], summary["min_completeness"], summary["max_completeness"])
    if key == "contamination_range":
        return _format_range(summary["avg_contamination"], summary["min_contamination"], summary["max_contamination"])
    if key == "total_data_gb":
        return _format_gb(summary["total_data_gb"])
    return summary[key]


def _format_range(avg_value: Any, min_value: Any, max_value: Any) -> str:
    if avg_value is None:
        return "n/a"
    return f"{avg_value:.2f} / {min_value:.2f} / {max_value:.2f}"


def _format_gb(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}"

