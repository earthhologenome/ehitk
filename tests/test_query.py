from ehitk.query import QueryValidationError, build_query, default_catalog_path, query_rows, validate_where_clause


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
    assert "FROM metagenomes" in sql
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
    )
    assert rows
    assert rows[0]["mag_id"].startswith("EHM")

