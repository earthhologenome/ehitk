from __future__ import annotations

import atexit
from contextlib import ExitStack
from dataclasses import dataclass
import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

DEFAULT_QUERY_LIMIT = 50
PACKAGE_DATA = resources.files("ehitk").joinpath("data")
CATALOG_RESOURCE = PACKAGE_DATA.joinpath("ehitk.sqlite")
CUSTOM_COLUMNS_RESOURCE = PACKAGE_DATA.joinpath("custom_columns.json")
ENVO_DESCENDANTS_RESOURCE = PACKAGE_DATA.joinpath("envo_descendants.json")
HOST_TAXON_DESCENDANTS_RESOURCE = PACKAGE_DATA.joinpath("host_taxon_descendants.json")
_RESOURCE_PATHS = ExitStack()
atexit.register(_RESOURCE_PATHS.close)

MAGS_WITH_SPECIMEN_SOURCE = """
(
    SELECT
        m."mag_id",
        m."release",
        m."completeness",
        m."contamination",
        m."size",
        m."gc",
        m."n50",
        m."contigs",
        m."mag_domain",
        m."mag_phylum",
        m."mag_class",
        m."mag_order",
        m."mag_family",
        m."mag_genus",
        m."url",
        m."mag_species",
        m."hologenome_id",
        mgws."release" AS "hologenome_release",
        mgws."sample_type" AS "sample_type",
        mgws."latitude" AS "latitude",
        mgws."longitude" AS "longitude",
        mgws."country" AS "country",
        mgws."date" AS "date",
        mgws."url1" AS "url1",
        mgws."url2" AS "url2",
        mgws."biome_envo_id" AS "biome_envo_id",
        mgws."biome_name" AS "biome_name",
        mgws."data" AS "data",
        mgws."specimen_id" AS "specimen_id",
        mgws."host_taxid" AS "host_taxid",
        mgws."host_species" AS "host_species",
        mgws."host_genus" AS "host_genus",
        mgws."host_family" AS "host_family",
        mgws."host_order" AS "host_order",
        mgws."host_class" AS "host_class",
        mgws."weight" AS "weight",
        mgws."length" AS "length",
        mgws."sex" AS "sex"
    FROM "mags" AS m
    LEFT JOIN "hologenomes_with_specimen" AS mgws ON m."hologenome_id" = mgws."hologenome_id"
)
"""

_BANNED_SQL_PATTERN = re.compile(
    r"\b(?:DROP|DELETE|INSERT|UPDATE|ALTER|ATTACH|PRAGMA)\b",
    flags=re.IGNORECASE,
)


class QueryValidationError(ValueError):
    """Raised when the user-provided SQL fragment is unsafe."""


@dataclass(frozen=True)
class TargetConfig:
    source: str
    query_columns: Mapping[str, str]
    all_query_headers: tuple[str, ...]
    fetch_select: tuple[str, ...]
    fetch_headers: tuple[str, ...]
    order_by: str
    primary_id: str


def _taxonomy_select(column: str, prefix: str, alias: str) -> str:
    prefix_length = len(prefix) + 1
    return (
        f"CASE WHEN {column} LIKE '{prefix}%' THEN substr({column}, {prefix_length}) "
        f"ELSE {column} END AS {alias}"
    )


MAG_QUALITY_CASE_EXPR = (
    "CASE "
    "WHEN completeness >= 90 AND contamination <= 5 THEN 'high' "
    "WHEN completeness >= 50 AND contamination <= 10 THEN 'medium' "
    "ELSE 'low' END"
)


TARGETS: dict[str, TargetConfig] = {
    "hologenomes": TargetConfig(
        source="hologenomes_with_specimen",
        query_columns={
            "hologenome_id": "hologenome_id",
            "release": "release",
            "sample_type": "sample_type",
            "latitude": "latitude",
            "longitude": "longitude",
            "country": "country",
            "date": "date",
            "url1": "url1",
            "url2": "url2",
            "biome_envo_id": "biome_envo_id",
            "biome_name": "biome_name",
            "data_gb": "data AS data_gb",
            "specimen_id": "specimen_id",
            "host_taxid": "host_taxid",
            "host_species": "host_species",
            "host_genus": "host_genus",
            "host_family": "host_family",
            "host_order": "host_order",
            "host_class": "host_class",
            "weight": "weight",
            "length": "length",
            "sex": "sex",
        },
        all_query_headers=(
            "hologenome_id",
            "release",
            "sample_type",
            "latitude",
            "longitude",
            "country",
            "date",
            "url1",
            "url2",
            "biome_envo_id",
            "biome_name",
            "data_gb",
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "weight",
            "length",
            "sex",
        ),
        fetch_select=(
            "hologenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "biome_envo_id",
            "biome_name",
            "url1",
            "url2",
        ),
        fetch_headers=(
            "hologenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "biome_envo_id",
            "biome_name",
            "url1",
            "url2",
        ),
        order_by="hologenome_id",
        primary_id="hologenome_id",
    ),
    "mags": TargetConfig(
        source=MAGS_WITH_SPECIMEN_SOURCE,
        query_columns={
            "mag_id": "mag_id",
            "release": "release",
            "quality": f"{MAG_QUALITY_CASE_EXPR} AS quality",
            "completeness": "completeness",
            "contamination": "contamination",
            "size": "size",
            "gc": "gc",
            "n50": "n50",
            "contigs": "contigs",
            "mag_domain": "mag_domain",
            "mag_phylum": "mag_phylum",
            "mag_class": "mag_class",
            "mag_order": "mag_order",
            "mag_family": "mag_family",
            "mag_genus": _taxonomy_select("mag_genus", "g__", "mag_genus"),
            "url": "url",
            "mag_species": _taxonomy_select("mag_species", "s__", "mag_species"),
            "hologenome_id": "hologenome_id",
            "hologenome_release": "hologenome_release",
            "sample_type": "sample_type",
            "latitude": "latitude",
            "longitude": "longitude",
            "country": "country",
            "date": "date",
            "url1": "url1",
            "url2": "url2",
            "biome_envo_id": "biome_envo_id",
            "biome_name": "biome_name",
            "data_gb": "data AS data_gb",
            "specimen_id": "specimen_id",
            "host_taxid": "host_taxid",
            "host_species": "host_species",
            "host_genus": "host_genus",
            "host_family": "host_family",
            "host_order": "host_order",
            "host_class": "host_class",
            "weight": "weight",
            "length": "length",
            "sex": "sex",
        },
        all_query_headers=(
            "mag_id",
            "release",
            "quality",
            "completeness",
            "contamination",
            "size",
            "gc",
            "n50",
            "contigs",
            "mag_domain",
            "mag_phylum",
            "mag_class",
            "mag_order",
            "mag_family",
            "mag_genus",
            "url",
            "mag_species",
            "hologenome_id",
            "hologenome_release",
            "sample_type",
            "latitude",
            "longitude",
            "country",
            "date",
            "url1",
            "url2",
            "biome_envo_id",
            "biome_name",
            "data_gb",
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "weight",
            "length",
            "sex",
        ),
        fetch_select=(
            "mag_id",
            "hologenome_id",
            "release",
            "completeness",
            "contamination",
            "mag_genus",
            "mag_species",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "url",
        ),
        fetch_headers=(
            "mag_id",
            "hologenome_id",
            "release",
            "completeness",
            "contamination",
            "mag_genus",
            "mag_species",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "url",
        ),
        order_by="mag_id",
        primary_id="mag_id",
    ),
    "specimens": TargetConfig(
        source="specimens",
        query_columns={
            "specimen_id": "specimen_id",
            "host_taxid": "host_taxid",
            "host_species": "host_species",
            "host_genus": "host_genus",
            "host_family": "host_family",
            "host_order": "host_order",
            "host_class": "host_class",
            "weight": "weight",
            "length": "length",
            "sex": "sex",
        },
        all_query_headers=(
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "weight",
            "length",
            "sex",
        ),
        fetch_select=(
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "weight",
            "length",
            "sex",
        ),
        fetch_headers=(
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "weight",
            "length",
            "sex",
        ),
        order_by="specimen_id",
        primary_id="specimen_id",
    ),
}

VALUE_FIELD_ALIASES: dict[str, dict[str, str]] = {
    "hologenomes": {
        "biome": "biome_name",
        "data": "data_gb",
    },
    "mags": {
        "biome": "biome_name",
        "data": "data_gb",
        "genus": "mag_genus",
        "species": "mag_species",
        "quality": "quality",
    },
    "specimens": {},
}

JSON_ARRAY_VALUE_FIELDS = {"weight", "length"}
QUERY_COLUMN_ALIASES: dict[str, dict[str, str]] = {
    "hologenomes": {
        "biome": "biome_name",
        "data": "data_gb",
    },
    "mags": {
        "biome": "biome_name",
        "data": "data_gb",
    },
}


@lru_cache(maxsize=1)
def default_catalog_path() -> Path:
    """Return a filesystem path for the bundled SQLite catalog resource."""
    if not CATALOG_RESOURCE.is_file():
        raise FileNotFoundError("Bundled EHItk SQLite catalog resource was not found.")
    return _RESOURCE_PATHS.enter_context(resources.as_file(CATALOG_RESOURCE))


def resolve_catalog_path(catalog_path: str | Path | None = None) -> Path:
    path = Path(catalog_path).expanduser() if catalog_path is not None else default_catalog_path()
    return path.resolve()


def catalog_path_from_context(ctx: Any, catalog_path: str | Path | None = None) -> Path:
    if catalog_path is not None:
        return resolve_catalog_path(catalog_path)
    if getattr(ctx, "obj", None) and "catalog_path" in ctx.obj:
        return Path(ctx.obj["catalog_path"])
    return default_catalog_path()


@lru_cache(maxsize=1)
def _custom_query_headers() -> dict[str, dict[str, tuple[str, ...]]]:
    with CUSTOM_COLUMNS_RESOURCE.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return {
        target: {preset: tuple(columns) for preset, columns in presets.items()}
        for target, presets in raw.items()
    }


def _load_descendant_resource(resource: Any) -> dict[str, tuple[str, ...]]:
    if not resource.is_file():
        return {}
    with resource.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    return {str(key): tuple(str(value) for value in values) for key, values in raw.items()}


@lru_cache(maxsize=1)
def _envo_descendants() -> dict[str, tuple[str, ...]]:
    return _load_descendant_resource(ENVO_DESCENDANTS_RESOURCE)


@lru_cache(maxsize=1)
def _host_taxon_descendants() -> dict[str, tuple[str, ...]]:
    return _load_descendant_resource(HOST_TAXON_DESCENDANTS_RESOURCE)


def headers_for(
    target: str,
    *,
    fetch: bool = False,
    columns: str | None = None,
) -> tuple[str, ...]:
    config = TARGETS[target]
    if fetch:
        return config.fetch_headers
    return resolve_query_headers(target, columns)


def resolve_query_headers(target: str, columns: str | None = None) -> tuple[str, ...]:
    config = TARGETS[target]
    custom_headers = _custom_query_headers().get(target)
    if custom_headers is None:
        raise QueryValidationError(f"No custom columns configured for target: {target}.")

    if columns is None:
        return custom_headers["default"]

    keyword = columns.strip().lower()
    if not keyword:
        raise QueryValidationError("The --columns option must not be empty.")

    if keyword == "all":
        return config.all_query_headers

    if "," not in columns:
        if keyword in custom_headers:
            return custom_headers[keyword]

        known_presets = {
            preset_name
            for presets in _custom_query_headers().values()
            for preset_name in presets.keys()
        }
        if keyword in known_presets:
            available_presets = ", ".join(sorted(custom_headers.keys()))
            raise QueryValidationError(
                f"Column preset '{keyword}' is not available for {target}. "
                f"Available presets: {available_presets}."
            )

    requested_headers = tuple(
        QUERY_COLUMN_ALIASES.get(target, {}).get(column.strip(), column.strip())
        for column in columns.split(",")
        if column.strip()
    )

    invalid_columns = [
        column for column in requested_headers if column not in config.query_columns
    ]
    if invalid_columns:
        available = ", ".join(config.all_query_headers)
        invalid = ", ".join(invalid_columns)
        raise QueryValidationError(
            f"Unknown columns for {target}: {invalid}. Available columns: {available}."
        )

    return requested_headers


def select_expressions_for(target: str, headers: tuple[str, ...]) -> tuple[str, ...]:
    config = TARGETS[target]
    return tuple(config.query_columns[header] for header in headers)


def _normalized_taxonomy_expr(column: str, prefix: str) -> str:
    prefix_length = len(prefix) + 1
    return (
        f"CASE WHEN {column} LIKE '{prefix}%' THEN substr({column}, {prefix_length}) "
        f"ELSE {column} END"
    )


def _casefold_one_of(expression: str, value_count: int) -> str:
    placeholders = ", ".join("LOWER(?)" for _ in range(value_count))
    return f"LOWER(COALESCE({expression}, '')) IN ({placeholders})"


def _normalize_prefixed_value(value: str, prefix: str) -> str:
    if value.lower().startswith(prefix.lower()):
        return value[len(prefix):]
    return value


def _split_filter_values(value: Any | None) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _combine_filter_values(value: Any | None, extra_values: list[str]) -> str | None:
    values = _split_filter_values(value) + extra_values
    return ",".join(values) if values else None


def _expanded_descendant_values(
    value: Any | None,
    descendants: Mapping[str, tuple[str, ...]],
    *,
    normalize_key: Any = str,
) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for raw_value in _split_filter_values(value):
        key = normalize_key(raw_value)
        for descendant in descendants.get(key, (key,)):
            if descendant not in seen:
                seen.add(descendant)
                expanded.append(descendant)
    return expanded


def _is_envo_id(value: str) -> bool:
    return value.upper().startswith("ENVO:")


def _mag_quality_clause(quality: str) -> str:
    quality_name = quality.strip().lower()
    if quality_name == "high":
        return "(completeness >= 90 AND contamination <= 5)"
    if quality_name == "medium":
        return "(completeness >= 50 AND contamination <= 10)"
    if quality_name == "low":
        return "NOT (completeness >= 50 AND contamination <= 10)"
    raise QueryValidationError(f"Unsupported MAG quality value: {quality}.")


def _mag_quality_value_expr() -> str:
    return MAG_QUALITY_CASE_EXPR


def available_value_fields(target: str) -> tuple[str, ...]:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    fields = list(TARGETS[target].all_query_headers)
    for alias in VALUE_FIELD_ALIASES.get(target, {}):
        if alias not in fields:
            fields.append(alias)
    return tuple(fields)


def resolve_value_field(target: str, field: str) -> str:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    candidate = field.strip()
    if not candidate:
        raise QueryValidationError("The --field option must not be empty.")

    canonical = VALUE_FIELD_ALIASES.get(target, {}).get(candidate, candidate)
    if canonical == "quality" and target == "mags":
        return canonical
    if canonical in TARGETS[target].all_query_headers:
        return canonical

    available = ", ".join(available_value_fields(target))
    raise QueryValidationError(
        f"Unknown values field for {target}: {field}. Available fields: {available}."
    )


def value_expression_for(target: str, field: str) -> tuple[str, bool]:
    canonical = resolve_value_field(target, field)
    if canonical == "mag_genus":
        return _normalized_taxonomy_expr("mag_genus", "g__"), False
    if canonical == "mag_species":
        return _normalized_taxonomy_expr("mag_species", "s__"), False
    if canonical == "quality":
        return _mag_quality_value_expr(), False
    if canonical == "data_gb":
        return "data", False
    return canonical, canonical in JSON_ARRAY_VALUE_FIELDS


def primary_id_for(target: str) -> str:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")
    return TARGETS[target].primary_id


def validate_where_clause(where: str | None) -> str | None:
    if where is None:
        return None

    candidate = where.strip()
    if not candidate:
        return None

    if ";" in candidate:
        raise QueryValidationError("The --where clause must not contain semicolons.")
    if "--" in candidate or "/*" in candidate or "*/" in candidate:
        raise QueryValidationError("The --where clause must not contain SQL comments.")
    if _BANNED_SQL_PATTERN.search(candidate):
        raise QueryValidationError("The --where clause contains a banned SQL keyword.")

    return candidate


def _build_conditions(target: str, filters: Mapping[str, Any]) -> tuple[list[str], list[Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []

    def add_exact(column: str, value: str | None) -> None:
        values = _split_filter_values(value)
        if values:
            conditions.append(_casefold_one_of(column, len(values)))
            parameters.extend(values)

    def add_descendant_exact(
        column: str,
        value: str | None,
        descendants: Mapping[str, tuple[str, ...]],
        *,
        normalize_key: Any = str,
    ) -> None:
        values = _expanded_descendant_values(
            value,
            descendants,
            normalize_key=normalize_key,
        )
        if values:
            conditions.append(_casefold_one_of(column, len(values)))
            parameters.extend(values)

    def add_normalized_taxonomy(column: str, prefix: str, value: str | None) -> None:
        values = _split_filter_values(value)
        if values:
            conditions.append(
                _casefold_one_of(_normalized_taxonomy_expr(column, prefix), len(values))
            )
            parameters.extend(
                _normalize_prefixed_value(value, prefix) for value in values
            )

    def add_numeric_range(
        column: str,
        minimum: float | int | None,
        maximum: float | int | None,
    ) -> None:
        if minimum is not None:
            conditions.append(f"{column} >= ?")
            parameters.append(minimum)
        if maximum is not None:
            conditions.append(f"{column} <= ?")
            parameters.append(maximum)

    def add_json_numeric_range(
        column: str,
        minimum: float | int | None,
        maximum: float | int | None,
    ) -> None:
        if minimum is None and maximum is None:
            return

        range_conditions: list[str] = []
        range_parameters: list[float | int] = []
        if minimum is not None:
            range_conditions.append("CAST(json_each.value AS REAL) >= ?")
            range_parameters.append(minimum)
        if maximum is not None:
            range_conditions.append("CAST(json_each.value AS REAL) <= ?")
            range_parameters.append(maximum)

        conditions.append(
            f"{column} IS NOT NULL AND EXISTS ("
            f"SELECT 1 FROM json_each({column}) WHERE {' AND '.join(range_conditions)}"
            f")"
        )
        parameters.extend(range_parameters)

    def add_host_taxonomy_filters() -> None:
        add_descendant_exact(
            "TRIM(host_taxid)",
            filters.get("host_taxid"),
            _host_taxon_descendants(),
        )
        add_exact("host_species", filters.get("host_species"))

        host_lineage_values = _split_filter_values(filters.get("host_lineage"))
        if host_lineage_values:
            lineage_columns = (
                "host_species",
                "host_genus",
                "host_family",
                "host_order",
                "host_class",
            )
            placeholder_count = len(host_lineage_values)
            conditions.append(
                "("
                + " OR ".join(
                    _casefold_one_of(column, placeholder_count) for column in lineage_columns
                )
                + ")"
            )
            for _ in lineage_columns:
                parameters.extend(host_lineage_values)

    def add_biome_filters() -> None:
        biome_alias_values = _split_filter_values(filters.get("biome"))
        biome_alias_envo_values = [
            value for value in biome_alias_values if _is_envo_id(value)
        ]
        biome_alias_name_values = [
            value for value in biome_alias_values if not _is_envo_id(value)
        ]
        biome_envo_id = _combine_filter_values(
            filters.get("biome_envo_id"),
            biome_alias_envo_values,
        )
        biome_name = filters.get("biome_name")
        if biome_name is None:
            biome_name = _combine_filter_values(None, biome_alias_name_values)

        add_descendant_exact(
            "TRIM(biome_envo_id)",
            biome_envo_id,
            _envo_descendants(),
            normalize_key=str.upper,
        )
        add_exact("biome_name", biome_name)

    if target == "hologenomes":
        add_exact("hologenome_id", filters.get("hologenome_id"))
        add_host_taxonomy_filters()
        add_exact("sample_type", filters.get("sample_type"))
        add_biome_filters()
        add_exact("release", filters.get("release"))
        add_exact("country", filters.get("country"))
        add_numeric_range("data", filters.get("data_min"), filters.get("data_max"))
        add_numeric_range("latitude", filters.get("latitude_min"), filters.get("latitude_max"))
        add_numeric_range("longitude", filters.get("longitude_min"), filters.get("longitude_max"))
        add_json_numeric_range("weight", filters.get("weight_min"), filters.get("weight_max"))
        add_json_numeric_range("length", filters.get("length_min"), filters.get("length_max"))

    elif target == "mags":
        add_exact("mag_id", filters.get("mag_id"))
        add_exact("release", filters.get("release"))
        add_exact("hologenome_id", filters.get("hologenome_id"))
        add_host_taxonomy_filters()
        add_biome_filters()
        add_exact("country", filters.get("country"))
        add_numeric_range("latitude", filters.get("latitude_min"), filters.get("latitude_max"))
        add_numeric_range("longitude", filters.get("longitude_min"), filters.get("longitude_max"))
        add_json_numeric_range("weight", filters.get("weight_min"), filters.get("weight_max"))
        add_json_numeric_range("length", filters.get("length_min"), filters.get("length_max"))
        add_normalized_taxonomy("mag_genus", "g__", filters.get("genus"))
        add_normalized_taxonomy("mag_species", "s__", filters.get("species"))

        quality_values = _split_filter_values(filters.get("quality"))
        if quality_values:
            conditions.append("(" + " OR ".join(_mag_quality_clause(value) for value in quality_values) + ")")
    elif target == "specimens":
        add_exact("specimen_id", filters.get("specimen_id"))
        add_exact("sex", filters.get("sex"))
        add_host_taxonomy_filters()
        add_json_numeric_range("weight", filters.get("weight_min"), filters.get("weight_max"))
        add_json_numeric_range("length", filters.get("length_min"), filters.get("length_max"))
    else:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    return conditions, parameters


def build_query(
    target: str,
    *,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
    limit: int | None = None,
    fetch: bool = False,
    columns: str | None = None,
) -> tuple[str, list[Any]]:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    config = TARGETS[target]
    selected_columns = (
        config.fetch_select
        if fetch
        else select_expressions_for(target, resolve_query_headers(target, columns))
    )
    base_sql, parameters = build_filtered_source_query(
        target,
        filters=filters,
        where=where,
    )

    sql = f"SELECT {', '.join(selected_columns)} FROM ({base_sql}) AS filtered"
    sql += f" ORDER BY {config.order_by}"

    if limit is not None:
        if limit <= 0:
            raise QueryValidationError("The query limit must be greater than zero.")
        sql += " LIMIT ?"
        parameters.append(limit)

    return sql, parameters


def build_filtered_source_query(
    target: str,
    *,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
) -> tuple[str, list[Any]]:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    config = TARGETS[target]
    conditions, parameters = _build_conditions(target, filters or {})

    safe_where = validate_where_clause(where)
    if safe_where:
        conditions.append(f"({safe_where})")

    sql = f"SELECT * FROM {config.source}"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    return sql, parameters


def query_rows(
    catalog_path: str | Path | None,
    target: str,
    *,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
    limit: int | None = None,
    fetch: bool = False,
    columns: str | None = None,
) -> list[sqlite3.Row]:
    resolved_catalog = resolve_catalog_path(catalog_path)
    sql, parameters = build_query(
        target,
        filters=filters,
        where=where,
        limit=limit,
        fetch=fetch,
        columns=columns,
    )

    with sqlite3.connect(resolved_catalog) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(sql, parameters).fetchall()
