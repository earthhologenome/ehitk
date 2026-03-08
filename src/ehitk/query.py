from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping

DEFAULT_QUERY_LIMIT = 50
PACKAGE_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "ehitk.sqlite"
REPO_CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "ehitk.sqlite"

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
        m."metagenome_id",
        mgws."release" AS "metagenome_release",
        mgws."sample_type" AS "sample_type",
        mgws."latitude" AS "latitude",
        mgws."longitude" AS "longitude",
        mgws."country" AS "country",
        mgws."date" AS "date",
        mgws."url1" AS "url1",
        mgws."url2" AS "url2",
        mgws."biome" AS "biome",
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
    LEFT JOIN "metagenomes_with_specimen" AS mgws ON m."metagenome_id" = mgws."metagenome_id"
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
    default_select: tuple[str, ...]
    default_headers: tuple[str, ...]
    fetch_select: tuple[str, ...]
    fetch_headers: tuple[str, ...]
    order_by: str


def _taxonomy_select(column: str, prefix: str, alias: str) -> str:
    prefix_length = len(prefix) + 1
    return (
        f"CASE WHEN {column} LIKE '{prefix}%' THEN substr({column}, {prefix_length}) "
        f"ELSE {column} END AS {alias}"
    )


TARGETS: dict[str, TargetConfig] = {
    "metagenomes": TargetConfig(
        source="metagenomes_with_specimen",
        default_select=(
            "metagenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "biome",
        ),
        default_headers=(
            "metagenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "biome",
        ),
        fetch_select=(
            "metagenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "biome",
            "url1",
            "url2",
        ),
        fetch_headers=(
            "metagenome_id",
            "specimen_id",
            "release",
            "sample_type",
            "host_species",
            "host_genus",
            "host_family",
            "host_order",
            "host_class",
            "biome",
            "url1",
            "url2",
        ),
        order_by="metagenome_id",
    ),
    "mags": TargetConfig(
        source=MAGS_WITH_SPECIMEN_SOURCE,
        default_select=(
            "mag_id",
            "metagenome_id",
            "specimen_id",
            "host_species",
            "completeness",
            "contamination",
            _taxonomy_select("mag_genus", "g__", "mag_genus"),
            _taxonomy_select("mag_species", "s__", "mag_species"),
            "release",
        ),
        default_headers=(
            "mag_id",
            "metagenome_id",
            "specimen_id",
            "host_species",
            "completeness",
            "contamination",
            "mag_genus",
            "mag_species",
            "release",
        ),
        fetch_select=(
            "mag_id",
            "metagenome_id",
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
            "metagenome_id",
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
    ),
    "specimens": TargetConfig(
        source="specimens",
        default_select=(
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
            "sex",
        ),
        default_headers=(
            "specimen_id",
            "host_taxid",
            "host_species",
            "host_genus",
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
    ),
}


def default_catalog_path() -> Path:
    if REPO_CATALOG_PATH.exists():
        return REPO_CATALOG_PATH
    return PACKAGE_CATALOG_PATH


def resolve_catalog_path(catalog_path: str | Path | None = None) -> Path:
    path = Path(catalog_path).expanduser() if catalog_path is not None else default_catalog_path()
    return path.resolve()


def catalog_path_from_context(ctx: Any) -> Path:
    if getattr(ctx, "obj", None) and "catalog_path" in ctx.obj:
        return Path(ctx.obj["catalog_path"])
    return default_catalog_path()


def headers_for(target: str, *, fetch: bool = False) -> tuple[str, ...]:
    config = TARGETS[target]
    return config.fetch_headers if fetch else config.default_headers


def _normalized_taxonomy_expr(column: str, prefix: str) -> str:
    prefix_length = len(prefix) + 1
    return (
        f"CASE WHEN {column} LIKE '{prefix}%' THEN substr({column}, {prefix_length}) "
        f"ELSE {column} END"
    )


def _casefold_exact(column: str) -> str:
    return f"LOWER(COALESCE({column}, '')) = LOWER(?)"


def _normalize_prefixed_value(value: str, prefix: str) -> str:
    if value.lower().startswith(prefix.lower()):
        return value[len(prefix):]
    return value


def _mag_quality_clause(quality: str) -> str:
    quality_name = quality.strip().lower()
    if quality_name == "high":
        return "(completeness >= 90 AND contamination <= 5)"
    if quality_name == "medium":
        return "(completeness >= 50 AND contamination <= 10)"
    if quality_name == "low":
        return "NOT (completeness >= 50 AND contamination <= 10)"
    raise QueryValidationError(f"Unsupported MAG quality value: {quality}.")


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
        if value:
            conditions.append(_casefold_exact(column))
            parameters.append(value.strip())

    def add_normalized_taxonomy(column: str, prefix: str, value: str | None) -> None:
        if value:
            conditions.append(
                f"LOWER(COALESCE({_normalized_taxonomy_expr(column, prefix)}, '')) = LOWER(?)"
            )
            parameters.append(_normalize_prefixed_value(value.strip(), prefix))

    def add_host_taxonomy_filters() -> None:
        add_exact("host_taxid", filters.get("host_taxid"))
        add_exact("host_species", filters.get("host_species"))

        host_lineage = filters.get("host_lineage")
        if host_lineage:
            lineage_columns = (
                "host_species",
                "host_genus",
                "host_family",
                "host_order",
                "host_class",
            )
            conditions.append(
                "(" + " OR ".join(_casefold_exact(column) for column in lineage_columns) + ")"
            )
            parameters.extend([host_lineage.strip()] * len(lineage_columns))

    if target == "metagenomes":
        add_host_taxonomy_filters()
        add_exact("sample_type", filters.get("sample_type"))
        add_exact("biome", filters.get("biome"))
        add_exact("release", filters.get("release"))

    elif target == "mags":
        add_exact("release", filters.get("release"))
        add_exact("metagenome_id", filters.get("metagenome_id"))
        add_host_taxonomy_filters()
        add_normalized_taxonomy("mag_genus", "g__", filters.get("genus"))
        add_normalized_taxonomy("mag_species", "s__", filters.get("species"))

        quality = filters.get("quality")
        if quality:
            conditions.append(_mag_quality_clause(quality))
    elif target == "specimens":
        add_exact("specimen_id", filters.get("specimen_id"))
        add_exact("sex", filters.get("sex"))
        add_host_taxonomy_filters()
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
) -> tuple[str, list[Any]]:
    if target not in TARGETS:
        raise QueryValidationError(f"Unsupported query target: {target}.")

    config = TARGETS[target]
    selected_columns = config.fetch_select if fetch else config.default_select
    conditions, parameters = _build_conditions(target, filters or {})

    safe_where = validate_where_clause(where)
    if safe_where:
        conditions.append(f"({safe_where})")

    sql = f"SELECT {', '.join(selected_columns)} FROM {config.source}"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY {config.order_by}"

    if limit is not None:
        if limit <= 0:
            raise QueryValidationError("The query limit must be greater than zero.")
        sql += " LIMIT ?"
        parameters.append(limit)

    return sql, parameters


def query_rows(
    catalog_path: str | Path | None,
    target: str,
    *,
    filters: Mapping[str, Any] | None = None,
    where: str | None = None,
    limit: int | None = None,
    fetch: bool = False,
) -> list[sqlite3.Row]:
    resolved_catalog = resolve_catalog_path(catalog_path)
    sql, parameters = build_query(
        target,
        filters=filters,
        where=where,
        limit=limit,
        fetch=fetch,
    )

    with sqlite3.connect(resolved_catalog) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(sql, parameters).fetchall()
