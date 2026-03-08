from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from ehitk.query import (
    QueryValidationError,
    build_filtered_source_query,
    primary_id_for,
    resolve_catalog_path,
    resolve_value_field,
    value_expression_for,
)

DEFAULT_VALUES_LIMIT = 20


def value_rows(
    catalog_path: str,
    *,
    target: str,
    field: str,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
    limit: int = DEFAULT_VALUES_LIMIT,
) -> tuple[str, list[dict[str, str | int]]]:
    if limit <= 0:
        raise QueryValidationError("The values limit must be greater than zero.")

    resolved_catalog = resolve_catalog_path(catalog_path)
    canonical_field = resolve_value_field(target, field)
    value_expression, is_json_array = value_expression_for(target, field)
    base_sql, parameters = build_filtered_source_query(
        target,
        filters=filters,
        where=where,
    )

    if is_json_array:
        sql = f"""
        SELECT value, COUNT(*) AS count
        FROM (
            SELECT DISTINCT
                filtered.{primary_id_for(target)} AS record_id,
                CAST(json_each.value AS TEXT) AS value
            FROM ({base_sql}) AS filtered
            JOIN json_each(filtered.{canonical_field})
        ) AS distinct_values
        WHERE COALESCE(TRIM(value), '') <> ''
        GROUP BY value
        ORDER BY count DESC, CAST(value AS REAL) ASC, value ASC
        LIMIT ?
        """
    else:
        sql = f"""
        SELECT CAST(value AS TEXT) AS value, COUNT(*) AS count
        FROM (
            SELECT {value_expression} AS value
            FROM ({base_sql}) AS filtered
        ) AS distinct_values
        WHERE COALESCE(TRIM(CAST(value AS TEXT)), '') <> ''
        GROUP BY value
        ORDER BY count DESC, value ASC
        LIMIT ?
        """

    with sqlite3.connect(resolved_catalog) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(sql, [*parameters, limit]).fetchall()

    return canonical_field, [
        {"value": row["value"], "count": row["count"]}
        for row in rows
    ]
