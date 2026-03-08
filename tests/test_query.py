from ehitk.query import (
    QueryValidationError,
    build_filtered_source_query,
    build_query,
    default_catalog_path,
    headers_for,
    query_rows,
    validate_where_clause,
)


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


def test_headers_for_columns_default_and_all() -> None:
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
