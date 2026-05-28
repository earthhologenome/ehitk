from importlib import resources
import json
from pathlib import Path
import sqlite3
import zipfile

from ehitk.query import (
    CATALOG_RESOURCE,
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


def _sample_rows(sql: str) -> list[sqlite3.Row]:
    with sqlite3.connect(default_catalog_path()) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(sql).fetchall()
    if not rows:
        raise AssertionError("Expected sample rows for test setup.")
    return rows


def test_validate_where_clause_rejects_semicolon() -> None:
    try:
        validate_where_clause("completeness > 90; DROP TABLE mags")
    except QueryValidationError:
        return
    raise AssertionError("Expected QueryValidationError for unsafe SQL")


def test_default_catalog_path_resolves_packaged_database_resource() -> None:
    catalog_path = default_catalog_path()

    assert CATALOG_RESOURCE.is_file()
    assert catalog_path.name == "ehitk.sqlite"
    assert catalog_path.is_file()


def test_default_catalog_path_handles_zip_resources(tmp_path, monkeypatch) -> None:
    package_zip = tmp_path / "resource_package.zip"
    with zipfile.ZipFile(package_zip, "w") as archive:
        archive.writestr("zip_resource_package/__init__.py", "")
        archive.writestr("zip_resource_package/data/ehitk.sqlite", b"catalog")

    monkeypatch.syspath_prepend(str(package_zip))
    zipped_catalog = resources.files("zip_resource_package").joinpath("data", "ehitk.sqlite")
    monkeypatch.setattr("ehitk.query.CATALOG_RESOURCE", zipped_catalog)

    default_catalog_path.cache_clear()
    try:
        catalog_path = default_catalog_path()

        assert catalog_path.name.endswith("ehitk.sqlite")
        assert catalog_path.is_file()
        assert catalog_path.read_bytes() == b"catalog"
    finally:
        default_catalog_path.cache_clear()


def test_build_query_for_hologenomes() -> None:
    sql, params = build_query(
        "hologenomes",
        filters={"host_species": "Podarcis muralis", "host_lineage": "Reptilia"},
        where="latitude > 40",
        limit=10,
    )
    assert "FROM hologenomes_with_specimen" in sql
    assert "host_species" in sql
    assert "latitude > 40" in sql
    assert params[-1] == 10


def test_query_rows_returns_hologenomes() -> None:
    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={"host_species": "Podarcis muralis"},
        limit=2,
    )
    assert rows
    assert rows[0]["hologenome_id"].startswith("EHI")


def test_query_rows_returns_hologenome_data_column() -> None:
    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={"host_species": "Podarcis muralis"},
        limit=2,
        columns="hologenome_id,data_gb",
    )
    assert rows
    assert "data_gb" in rows[0].keys()


def test_query_rows_filters_hologenomes_by_split_biome_fields() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, biome_envo_id, biome_name
        FROM hologenomes_with_specimen
        WHERE biome_envo_id IS NOT NULL AND biome_name IS NOT NULL
        LIMIT 1
        """
    )

    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={
            "biome_envo_id": sample["biome_envo_id"],
            "biome_name": sample["biome_name"],
        },
        limit=5,
        columns="hologenome_id,biome_envo_id,biome_name",
    )

    assert rows
    assert any(row["hologenome_id"] == sample["hologenome_id"] for row in rows)
    assert all(row["biome_envo_id"].startswith("ENVO:") for row in rows)


def test_query_rows_expands_biome_envo_descendants() -> None:
    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={"biome_envo_id": "ENVO:01000175"},
        limit=None,
        columns="hologenome_id,biome_envo_id,biome_name",
    )

    biome_ids = {row["biome_envo_id"] for row in rows}
    biome_names = {row["biome_name"] for row in rows}
    assert "ENVO:01000221" in biome_ids
    assert "ENVO:01000220" in biome_ids
    assert "Temperate woodland" in biome_names
    assert "Tropical woodland" in biome_names


def test_query_rows_expands_legacy_biome_alias_when_value_is_envo_id() -> None:
    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={"biome": "ENVO:01000175"},
        limit=5,
        columns="hologenome_id,biome_envo_id",
    )

    assert rows
    assert {row["biome_envo_id"] for row in rows}.issubset(
        {"ENVO:01000220", "ENVO:01000221"}
    )


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


def test_query_rows_returns_mag_quality_column() -> None:
    rows = query_rows(
        default_catalog_path(),
        "mags",
        filters={"genus": "Escherichia"},
        limit=2,
        columns="mag_id,quality",
    )
    assert rows
    assert rows[0]["quality"] in {"high", "medium", "low"}


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


def test_query_rows_expands_host_taxid_descendants() -> None:
    rows = query_rows(
        default_catalog_path(),
        "specimens",
        filters={"host_taxid": "8509"},
        limit=10,
        columns="specimen_id,host_taxid,host_order",
    )

    assert rows
    assert all(row["host_order"] == "Squamata" for row in rows)
    assert any(str(row["host_taxid"]).strip() != "8509" for row in rows)


def test_query_rows_filters_mags_by_biome_envo_descendants() -> None:
    rows = query_rows(
        default_catalog_path(),
        "mags",
        filters={"biome_envo_id": "ENVO:01000175"},
        limit=10,
        columns="mag_id,biome_envo_id",
    )

    assert rows
    assert {row["biome_envo_id"] for row in rows}.issubset(
        {"ENVO:01000220", "ENVO:01000221"}
    )


def test_query_rows_filters_hologenomes_by_country_and_coordinate_range() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, country, latitude, longitude
        FROM hologenomes_with_specimen
        WHERE country IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 1
        """
    )

    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={
            "country": sample["country"],
            "latitude_min": float(sample["latitude"]) - 0.01,
            "latitude_max": float(sample["latitude"]) + 0.01,
            "longitude_min": float(sample["longitude"]) - 0.01,
            "longitude_max": float(sample["longitude"]) + 0.01,
        },
        limit=5,
        columns="hologenome_id,country,latitude,longitude",
    )

    assert rows
    assert any(row["hologenome_id"] == sample["hologenome_id"] for row in rows)


def test_query_rows_filters_hologenomes_by_data_range() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, data
        FROM hologenomes_with_specimen
        WHERE data IS NOT NULL
        LIMIT 1
        """
    )
    data_value = float(sample["data"])

    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={
            "data_min": data_value - 0.01,
            "data_max": data_value + 0.01,
        },
        limit=5,
        columns="hologenome_id,data_gb",
    )

    assert rows
    assert any(row["hologenome_id"] == sample["hologenome_id"] for row in rows)


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


def test_query_rows_supports_comma_separated_hologenome_ids() -> None:
    samples = _sample_rows(
        """
        SELECT hologenome_id
        FROM hologenomes_with_specimen
        LIMIT 2
        """
    )
    requested_ids = ",".join(row["hologenome_id"] for row in samples)

    rows = query_rows(
        default_catalog_path(),
        "hologenomes",
        filters={"hologenome_id": requested_ids},
        limit=10,
        columns="hologenome_id",
    )

    returned_ids = {row["hologenome_id"] for row in rows}
    assert {row["hologenome_id"] for row in samples}.issubset(returned_ids)


def test_query_rows_supports_comma_separated_mag_ids() -> None:
    samples = _sample_rows(
        """
        SELECT mag_id
        FROM mags
        LIMIT 2
        """
    )
    requested_ids = ",".join(row["mag_id"] for row in samples)

    rows = query_rows(
        default_catalog_path(),
        "mags",
        filters={"mag_id": requested_ids},
        limit=10,
        columns="mag_id",
    )

    returned_ids = {row["mag_id"] for row in rows}
    assert {row["mag_id"] for row in samples}.issubset(returned_ids)


def test_headers_for_columns_default_and_all() -> None:
    assert headers_for("hologenomes") == _default_columns("hologenomes")
    assert headers_for("hologenomes") == headers_for("hologenomes", columns="default")
    assert "data_gb" in headers_for("hologenomes", columns="all")
    assert "data_gb" in headers_for("mags", columns="all")
    assert "quality" in headers_for("mags")
    assert "quality" in headers_for("mags", columns="all")
    assert "host_class" in headers_for("hologenomes", columns="all")
    assert headers_for("hologenomes", columns="url") == (
        "hologenome_id",
        "url1",
        "url2",
    )
    assert headers_for("mags", columns="url") == ("mag_id", "url")


def test_headers_for_accepts_legacy_data_alias() -> None:
    assert headers_for("hologenomes", columns="data") == ("data_gb",)
    assert headers_for("mags", columns="data") == ("data_gb",)


def test_headers_for_accepts_legacy_biome_alias() -> None:
    assert headers_for("hologenomes", columns="biome") == ("biome_name",)
    assert headers_for("mags", columns="biome") == ("biome_name",)


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
    assert "LOWER(COALESCE(country, '')) IN (LOWER(?))" in sql
    assert "latitude >= ?" in sql
    assert "latitude <= ?" in sql
    assert "longitude >= ?" in sql
    assert "longitude <= ?" in sql
    assert "json_each(weight)" in sql
    assert "json_each(length)" in sql
    assert params == ["ExampleLand", 10.5, 20.5, -5.0, 5.0, 1.0, 9.0, 2.0, 8.0]


def test_build_filtered_source_query_supports_hologenome_data_range() -> None:
    sql, params = build_filtered_source_query(
        "hologenomes",
        filters={
            "data_min": 1.25,
            "data_max": 9.75,
        },
    )
    assert "data >= ?" in sql
    assert "data <= ?" in sql
    assert params == [1.25, 9.75]


def test_build_filtered_source_query_supports_multi_value_quality_and_ids() -> None:
    sql, params = build_filtered_source_query(
        "mags",
        filters={
            "mag_id": "EHM00001,EHM00002",
            "quality": "high,medium",
        },
    )
    assert "LOWER(COALESCE(mag_id, '')) IN (LOWER(?), LOWER(?))" in sql
    assert "(completeness >= 90 AND contamination <= 5)" in sql
    assert "(completeness >= 50 AND contamination <= 10)" in sql
    assert params == ["EHM00001", "EHM00002"]


def test_build_filtered_source_query_expands_descendant_filters() -> None:
    sql, params = build_filtered_source_query(
        "hologenomes",
        filters={"biome_envo_id": "ENVO:01000175", "host_taxid": "8509"},
    )

    assert "TRIM(host_taxid)" in sql
    assert "TRIM(biome_envo_id)" in sql
    assert "ENVO:01000221" in params
    assert "ENVO:01000220" in params
    assert "64176" in params
