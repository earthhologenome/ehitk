import json

from ehitk.manifest import ManifestEntry, append_manifest_entry


def test_manifest_entry_uses_entity_specific_metagenome_key() -> None:
    entry = ManifestEntry(
        entry_type="metagenome",
        id_field="metagenome_id",
        id_value="EHI00001",
        url="ftp://example.org/read_1.fastq.gz",
        path="downloads/metagenomes/EHI00001/read_1.fastq.gz",
        checksum="abc123",
        status="downloaded",
    )

    payload = entry.as_dict()

    assert payload["type"] == "metagenome"
    assert payload["metagenome_id"] == "EHI00001"
    assert "genome_id" not in payload


def test_append_manifest_entry_writes_entity_specific_mag_key(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.jsonl"
    append_manifest_entry(
        manifest_path,
        ManifestEntry(
            entry_type="mag",
            id_field="mag_id",
            id_value="EHM00001",
            url=None,
            path=None,
            checksum=None,
            status="missing_url",
        ),
    )

    row = json.loads(manifest_path.read_text(encoding="utf-8").strip())
    assert row["type"] == "mag"
    assert row["mag_id"] == "EHM00001"
    assert "genome_id" not in row
