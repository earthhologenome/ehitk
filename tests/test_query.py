import json
from pathlib import Path
import sqlite3

from ehitk.query import (
    QueryValidationError,
    build_filtered_source_query,
    build_query,
    default_catalog_path,
    headers_for,
    query_rows,
    validate_where_clause,
)


def _default_columns(target: str) -> tuple[str, ...]:
    custom_columns_path = Path("src/ehitk/data/custom_columns.json")
    raw = json.loads(custom_columns_path.read_text(encoding="utf-8"))
    return tuple(raw[target]["default"])


def _sample_row(sql: str) -> sqlite3.Row:
    with sqlite3.connect(default_catalog_path()) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql).fetchone()
    if row is None:
        raise AssertionError("Expected sample row for test setup.")
    return row


def test_validate_where_clause_rejects_semicolon() -> None:
    try:
        validate_where_clause("completeness > 90; DROP TABLE mags")
    except QueryValidationError:
        return
    raise AssertionError("Expected QueryValidationError for unsafe SQL")


def test_build_query_for_metagenomes() -> None:
    sql, params = build_query(
        "metagenomes",
        filters={"host_species": "Podarcis muralis", "host_lineage": "Reptilia"},
        where="latitude > 40",
        limit=10,
    )
    assert "FROM metagenomes_with_specimen" in sql
    assert "host_species" in sql
    assert "latitude > 40" in sql
    assert params[-1] == 10


def test_query_rows_returns_metagenomes() -> None:
    rows = query_rows(
        default_catalog_path(),
        "metagenomes",
        filters={"host_species": "Podarcis muralis"},
        limit=2,
    )
    assert rows
    assert rows[0]["metagenome_id"].startswith("EHI")


def test_query_rows_returns_mags() -> None:
    rows = query_rows(
        default_catalog_path(),
        "mags",
        filters={"genus": "Escherichia"},
        limit=2,
        columns="mag_id,mag_genus",
    )
    assert rows
    assert rows[0]["mag_id"].startswith("EHM")


def test_query_rows_returns_specimens() -> None:
    rows = query_rows(
        default_catalog_path(),
        "specimens",
        filters={"host_species": "Podarcis muralis"},
        limit=2,
    )
    assert rows
    assert rows[0]["specimen_id"].startswith("SD")


def test_query_rows_returns_mags_with_host_taxonomy() -> None:
    rows = query_rows(
        default_catalog_path(),
        "mags",
        filters={"host_species": "Sciurus carolinensis"},
        limit=1,
        fetch=True,
    )
    assert rows
    assert rows[0]["host_species"] == "Sciurus carolinensis"


def test_query_rows_filters_metagenomes_by_country_and_coordinate_range() -> None:
    sample = _sample_row(
        """
        SELECT metagenome_id, country, latitude, longitude
        FROM metagenomes_with_specimen
        WHERE country IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 1
        """
    )

    rows = query_rows(
        default_catalog_path(),
        "metagenomes",
        filters={
            "country": sample["country"],
            "latitude_min": float(sample["latitude"]) - 0.01,
            "latitude_max": float(sample["latitude"]) + 0.01,
            "longitude_min": float(sample["longitude"]) - 0.01,
            "longitude_max": float(sample["longitude"]) + 0.01,
        },
        limit=5,
        columns="metagenome_id,country,latitude,longitude",
    )

    assert rows
    assert any(row["metagenome_id"] == sample["metagenome_id"] for row in rows)


def test_query_rows_filters_specimens_by_weight_and_length_range() -> None:
    sample = _sample_row(
        """
        SELECT specimen_id, weight, length
        FROM specimens
        WHERE weight IS NOT NULL AND length IS NOT NULL
        LIMIT 1
        """
    )
    weight_value = float(json.loads(sample["weight"])[0])
    length_value = float(json.loads(sample["length"])[0])

    rows = query_rows(
        default_catalog_path(),
        "specimens",
        filters={
            "weight_min": weight_value - 0.1,
            "weight_max": weight_value + 0.1,
            "length_min": length_value - 0.1,
            "length_max": length_value + 0.1,
        },
        limit=5,
        columns="specimen_id,weight,length",
    )

    assert rows
    assert any(row["specimen_id"] == sample["specimen_id"] for row in rows)


def test_headers_for_columns_default_and_all() -> None:
    assert headers_for("metagenomes") == _default_columns("metagenomes")
    assert headers_for("metagenomes") == headers_for("metagenomes", columns="default")
    assert "host_class" in headers_for("metagenomes", columns="all")
    assert headers_for("metagenomes", columns="url") == (
        "metagenome_id",
        "url1",
        "url2",
    )
    assert headers_for("mags", columns="url") == ("mag_id", "url")


def test_build_query_with_explicit_columns() -> None:
    sql, _ = build_query(
        "mags",
        filters={"host_species": "Sciurus carolinensis"},
        columns="mag_id,host_species,mag_genus",
        limit=1,
    )
    assert "SELECT mag_id, host_species, CASE WHEN mag_genus LIKE 'g__%'" in sql


def test_build_query_rejects_unknown_columns() -> None:
    try:
        build_query("specimens", columns="specimen_id,unknown_column")
    except QueryValidationError:
        return
    raise AssertionError("Expected QueryValidationError for unknown columns")


def test_build_query_rejects_unsupported_column_preset() -> None:
    try:
        build_query("specimens", columns="url")
    except QueryValidationError:
        return
    raise AssertionError("Expected QueryValidationError for unsupported preset")


def test_build_filtered_source_query_allows_combined_mag_filters() -> None:
    sql, params = build_filtered_source_query(
        "mags",
        filters={"quality": "high", "species": "Escherichia coli"},
        where="host_species = 'Sciurus carolinensis'",
    )
    assert "completeness >= 90 AND contamination <= 5" in sql
    assert "host_species = 'Sciurus carolinensis'" in sql
    assert params == ["Escherichia coli"]


def test_build_filtered_source_query_supports_range_and_country_filters() -> None:
    sql, params = build_filtered_source_query(
        "mags",
        filters={
            "country": "ExampleLand",
            "latitude_min": 10.5,
            "latitude_max": 20.5,
            "longitude_min": -5.0,
            "longitude_max": 5.0,
            "weight_min": 1.0,
            "weight_max": 9.0,
            "length_min": 2.0,
            "length_max": 8.0,
        },
    )
    assert "LOWER(COALESCE(country, '')) = LOWER(?)" in sql
    assert "latitude >= ?" in sql
    assert "latitude <= ?" in sql
    assert "longitude >= ?" in sql
    assert "longitude <= ?" in sql
    assert "json_each(weight)" in sql
    assert "json_each(length)" in sql
    assert params == ["ExampleLand", 10.5, 20.5, -5.0, 5.0, 1.0, 9.0, 2.0, 8.0]
