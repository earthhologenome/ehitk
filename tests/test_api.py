import sqlite3

import pytest

import ehitk
from ehitk.query import default_catalog_path


ROOT_DB_PATH = default_catalog_path()


def _write_catalog_meta(path, entries: dict[str, str]) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
    )
    connection.executemany(
        "INSERT INTO catalog_meta (key, value) VALUES (?, ?)",
        list(entries.items()),
    )
    connection.commit()
    connection.close()


def test_database_rejects_unsupported_schema_version(tmp_path) -> None:
    catalog = tmp_path / "ehitk.sqlite"
    _write_catalog_meta(catalog, {"schema_version": "999", "data_version": "2026.06.28"})
    with pytest.raises(ehitk.UnsupportedSchemaVersionError) as exc_info:
        ehitk.Database(catalog)
    message = str(exc_info.value)
    assert "999" in message
    assert "supported" in message.lower()


def test_database_accepts_supported_schema_version(tmp_path) -> None:
    catalog = tmp_path / "ehitk.sqlite"
    _write_catalog_meta(catalog, {"schema_version": "1", "data_version": "2026.06.28"})
    with ehitk.Database(catalog) as database:
        assert database.path == catalog.resolve()


def test_database_opens_legacy_catalog_without_catalog_meta(tmp_path) -> None:
    catalog = tmp_path / "ehitk.sqlite"
    connection = sqlite3.connect(catalog)
    connection.execute("CREATE TABLE specimens (specimen_id TEXT)")
    connection.commit()
    connection.close()
    # No catalog_meta -> treated as legacy and accepted.
    with ehitk.Database(catalog) as database:
        assert database.path == catalog.resolve()


def _sample_row(sql: str) -> sqlite3.Row:
    with sqlite3.connect(ROOT_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql).fetchone()
    if row is None:
        raise AssertionError("Expected sample row for test setup.")
    return row


def test_database_query_returns_typed_mag_records() -> None:
    with ehitk.Database() as database:
        mags = database.mags.query(
            genus="Escherichia",
            limit=2,
            columns=("mag_id", "quality", "mag_genus"),
        )

    assert mags
    assert isinstance(mags[0], ehitk.Mag)
    assert mags[0].mag_id is not None
    assert mags[0].quality in {"high", "medium", "low"}
    assert mags[0].mag_genus == "Escherichia"


def test_database_query_accepts_python_native_filter_values() -> None:
    sample = _sample_row(
        """
        SELECT specimen_id, host_taxid
        FROM specimens
        WHERE host_taxid IS NOT NULL
        LIMIT 1
        """
    )
    host_taxid = int(sample["host_taxid"])

    with ehitk.Database() as database:
        specimens = database.specimens.query(
            host_taxid=host_taxid,
            limit=5,
            columns=("specimen_id", "host_taxid"),
        )

    assert specimens
    assert any(specimen.specimen_id == sample["specimen_id"] for specimen in specimens)


def test_database_query_expands_host_taxid_descendants() -> None:
    with ehitk.Database() as database:
        specimens = database.specimens.query(
            host_taxid=8509,
            limit=5,
            columns=("specimen_id", "host_taxid", "host_order"),
        )

    assert specimens
    assert all(specimen.host_order == "Squamata" for specimen in specimens)


def test_database_query_returns_split_biome_fields() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, biome_envo_id, biome_name
        FROM hologenomes_with_specimen
        WHERE biome_envo_id IS NOT NULL AND biome_name IS NOT NULL
        LIMIT 1
        """
    )

    with ehitk.Database() as database:
        hologenomes = database.hologenomes.query(
            biome_envo_id=sample["biome_envo_id"],
            biome_name=sample["biome_name"],
            limit=5,
            columns=("hologenome_id", "biome_envo_id", "biome_name"),
        )

    assert hologenomes
    assert any(
        hologenome.hologenome_id == sample["hologenome_id"]
        for hologenome in hologenomes
    )
    assert hologenomes[0].biome_envo_id.startswith("ENVO:")
    assert hologenomes[0].biome_name


def test_database_values_returns_structured_value_counts() -> None:
    with ehitk.Database() as database:
        values = database.mags.values("quality", limit=3)

    assert values.field == "quality"
    assert values.rows
    assert isinstance(values.rows[0], ehitk.ValueCount)
    assert values.rows[0].count > 0


def test_database_stats_returns_structured_summary() -> None:
    with ehitk.Database() as database:
        stats = database.specimens.stats(host_lineage="Reptilia")

    assert stats.target == "specimens"
    assert stats.summary["matched_specimens"] > 0
    assert any(breakdown.title == "Sex distribution" for breakdown in stats.breakdowns)


def test_database_accepts_alternate_catalog_path() -> None:
    with ehitk.Database(ROOT_DB_PATH) as database:
        specimens = database.specimens.query(limit=1)

    assert specimens


def test_mags_fetch_writes_batch_script_without_downloading(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT mag_id
        FROM mags
        WHERE url IS NOT NULL AND url <> ''
        LIMIT 1
        """
    )
    batch_path = tmp_path / "mags-fetch.sh"
    manifest_path = tmp_path / "manifest.jsonl"

    with ehitk.Database() as database:
        summary = database.mags.fetch(
            mag_id=sample["mag_id"],
            batch=batch_path,
            manifest_path=manifest_path,
        )

    assert summary.target == "mags"
    assert summary.matched_count == 1
    assert summary.queued_count == 1
    assert summary.batch_script == batch_path
    assert batch_path.exists()
    assert sample["mag_id"] in batch_path.read_text(encoding="utf-8")
    assert not manifest_path.exists()


def test_database_rejects_calls_after_close() -> None:
    database = ehitk.Database()
    database.close()

    try:
        database.mags.query(limit=1)
    except RuntimeError as exc:
        assert "closed" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError after Database.close().")
