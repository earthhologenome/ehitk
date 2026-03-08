from ehitk.query import default_catalog_path
from ehitk.values import value_rows


def test_value_rows_returns_metagenome_host_species_counts() -> None:
    field, rows = value_rows(
        str(default_catalog_path()),
        target="metagenomes",
        field="host_species",
        limit=5,
    )
    assert field == "host_species"
    assert rows
    assert rows[0]["count"] >= 1


def test_value_rows_supports_mag_genus_alias() -> None:
    field, rows = value_rows(
        str(default_catalog_path()),
        target="mags",
        field="genus",
        limit=5,
    )
    assert field == "mag_genus"
    assert rows
    assert all(not str(row["value"]).startswith("g__") for row in rows)


def test_value_rows_expands_json_array_measurements() -> None:
    field, rows = value_rows(
        str(default_catalog_path()),
        target="specimens",
        field="weight",
        limit=5,
    )
    assert field == "weight"
    assert rows
    assert rows[0]["count"] >= 1
