import hashlib
import json
from pathlib import Path
import re
import sqlite3

from typer.testing import CliRunner

from ehitk import __version__
from ehitk.cli import app
from ehitk.query import default_catalog_path

runner = CliRunner()
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ROOT_DB_PATH = default_catalog_path()


def _strip_ansi(text: str) -> str:
    return ANSI_PATTERN.sub("", text)


def _format_gb(value: float | int | None) -> str:
    if value is None:
        return "0.00"
    return f"{value:,.2f}"


def _default_columns(target: str) -> tuple[str, ...]:
    custom_columns_path = Path("src/ehitk/data/custom_columns.json")
    raw = json.loads(custom_columns_path.read_text(encoding="utf-8"))
    return tuple(raw[target]["default"])


def _sample_row(sql: str) -> sqlite3.Row:
    with sqlite3.connect(ROOT_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql).fetchone()
    if row is None:
        raise AssertionError("Expected sample row for test setup.")
    return row


def _sample_rows(sql: str) -> list[sqlite3.Row]:
    with sqlite3.connect(ROOT_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(sql).fetchall()
    if not rows:
        raise AssertionError("Expected sample rows for test setup.")
    return rows


def _root_summary_row(sql: str) -> sqlite3.Row:
    with sqlite3.connect(ROOT_DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql).fetchone()
    if row is None:
        raise AssertionError("Expected summary row for test setup.")
    return row


def test_root_command_shows_overview_in_fixed_order() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Earth Hologenome Initiative ToolKit" in result.output
    assert "Query, summarize, and fetch specimens, hologenomes, and MAGs" in result.output
    assert "Level" in result.output
    assert "Records" in result.output
    assert "Summary" in result.output

    specimens_index = result.output.rindex("Specimens")
    hologenomes_index = result.output.rindex("Hologenomes")
    mags_index = result.output.rindex("MAGs")
    assert specimens_index < hologenomes_index < mags_index

    specimens = _root_summary_row("SELECT COUNT(*) AS records FROM specimens")
    hologenomes = _root_summary_row(
        """
        SELECT
            COUNT(*) AS records,
            SUM(CASE WHEN url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> '' THEN 1 ELSE 0 END) AS paired_urls,
            SUM(data) AS total_data_gb
        FROM hologenomes
        """
    )
    mags = _root_summary_row(
        """
        SELECT
            (SELECT COUNT(*) FROM mags) AS records,
            COUNT(*) AS parent_hologenomes,
            SUM(data) AS total_parent_data_gb
        FROM (
            SELECT DISTINCT hologenome_id, data
            FROM mags_with_hologenome
            WHERE hologenome_id IS NOT NULL
        )
        """
    )
    assert f"{specimens['records']:,}" in result.output
    assert f"{hologenomes['records']:,}" in result.output
    assert f"{mags['records']:,}" in result.output
    assert (
        f"{hologenomes['paired_urls']:,} paired read sets, "
        f"{_format_gb(hologenomes['total_data_gb'])} GB"
    ) in result.output
    assert (
        f"{mags['parent_hologenomes']:,} parent hologenomes, "
        f"{_format_gb(mags['total_parent_data_gb'])} GB"
    ) in result.output


def test_root_help_shows_db_and_hides_completion_options() -> None:
    result = runner.invoke(app, ["--help"])
    output = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "Earth Hologenome Initiative ToolKit" in output
    assert "Query, summarize, and fetch specimens, hologenomes, and MAGs" in output
    assert "--db" in output
    assert "--version" in output
    assert "--catalog" not in output
    assert "--install-completion" not in output
    assert "--show-completion" not in output

    specimens_index = output.index("specimens")
    hologenomes_index = output.index("hologenomes")
    mags_index = output.index("mags")
    assert specimens_index < hologenomes_index < mags_index


def test_database_command_reports_active_catalog() -> None:
    result = runner.invoke(app, ["database"])
    output = _strip_ansi(result.output)
    checksum = hashlib.sha256(ROOT_DB_PATH.read_bytes()).hexdigest()

    assert result.exit_code == 0
    assert "Database Catalog" in output
    assert "Package version" in output
    assert __version__ in output
    assert "Catalog source" in output
    assert "bundled" in output
    assert "Catalog path" in output
    assert str(ROOT_DB_PATH) in output
    assert "SHA256" in output
    assert checksum in output


def test_entity_help_documents_subcommands() -> None:
    expected = {
        "specimens": (
            "List fields accepted by specimen values",
            "List specimen records that match host taxonomy",
            "Count distinct values for a specimen field",
            "Summarize the number and composition",
        ),
        "hologenomes": (
            "List fields accepted by hologenome values",
            "List hologenome records that match host",
            "Count distinct values for a hologenome field",
            "Download matching paired-read files",
            "data volume of matching",
        ),
        "mags": (
            "List fields accepted by MAG values",
            "List MAG records that match taxonomy",
            "Count distinct values for a MAG field",
            "Download matching MAG FASTA files",
            "quality, taxonomy, and host context",
        ),
    }

    for entity, snippets in expected.items():
        result = runner.invoke(app, [entity, "--help"])
        output = _strip_ansi(result.output)
        assert result.exit_code == 0
        for snippet in snippets:
            assert snippet in output


def test_root_error_usage_shows_same_header() -> None:
    result = runner.invoke(app, ["--bad-option"])
    output = _strip_ansi(result.output)
    assert result.exit_code != 0
    assert "Earth Hologenome Initiative ToolKit" in output
    assert "Query, summarize, and fetch specimens, hologenomes, and MAGs" in output
    assert "Usage:" in output


def test_root_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_package_version_matches_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in pyproject


def test_hologenomes_query_cli() -> None:
    result = runner.invoke(
        app,
        ["hologenomes", "query", "--host-species", "Podarcis muralis", "--limit", "1"],
    )
    assert result.exit_code == 0
    assert "EHI" in result.stdout


def test_mags_query_cli() -> None:
    result = runner.invoke(
        app,
        ["mags", "query", "--genus", "Escherichia", "--limit", "1", "--columns", "mag_id,mag_genus"],
    )
    assert result.exit_code == 0
    assert "EHM" in result.stdout


def test_specimens_query_cli() -> None:
    result = runner.invoke(
        app,
        ["specimens", "query", "--host-species", "Podarcis muralis", "--limit", "1"],
    )
    assert result.exit_code == 0
    assert "SD" in result.stdout


def test_hologenomes_query_cli_supports_country_and_coordinate_ranges() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, country, latitude, longitude
        FROM hologenomes_with_specimen
        WHERE country IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 1
        """
    )
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--country",
            sample["country"],
            "--latitude-min",
            str(float(sample["latitude"]) - 0.01),
            "--latitude-max",
            str(float(sample["latitude"]) + 0.01),
            "--longitude-min",
            str(float(sample["longitude"]) - 0.01),
            "--longitude-max",
            str(float(sample["longitude"]) + 0.01),
            "--limit",
            "1",
            "--columns",
            "hologenome_id,country,latitude,longitude",
        ],
    )
    assert result.exit_code == 0
    assert sample["hologenome_id"] in result.stdout


def test_hologenomes_query_cli_supports_data_range() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, data
        FROM hologenomes_with_specimen
        WHERE data IS NOT NULL
        LIMIT 1
        """
    )
    data_value = float(sample["data"])
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--data-min",
            str(data_value - 0.01),
            "--data-max",
            str(data_value + 0.01),
            "--limit",
            "1",
            "--columns",
            "hologenome_id,data_gb",
        ],
    )
    assert result.exit_code == 0
    assert sample["hologenome_id"] in result.stdout


def test_hologenomes_query_cli_supports_split_biome_filters() -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id, biome_envo_id, biome_name
        FROM hologenomes_with_specimen
        WHERE biome_envo_id IS NOT NULL AND biome_name IS NOT NULL
        LIMIT 1
        """
    )
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--biome-envo-id",
            sample["biome_envo_id"],
            "--biome-name",
            sample["biome_name"],
            "--limit",
            "1",
            "--columns",
            "hologenome_id,biome_envo_id,biome_name",
        ],
    )
    assert result.exit_code == 0
    assert sample["hologenome_id"] in result.stdout
    assert sample["biome_envo_id"] in result.stdout
    assert sample["biome_name"] in result.stdout


def test_hologenomes_query_cli_expands_biome_alias_descendants() -> None:
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--biome",
            "ENVO:01000175",
            "--limit",
            "1",
            "--columns",
            "hologenome_id,biome_envo_id,biome_name",
        ],
    )
    assert result.exit_code == 0
    assert "ENVO:01000221" in result.stdout or "ENVO:01000220" in result.stdout


def test_specimens_query_cli_supports_weight_and_length_ranges() -> None:
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
    result = runner.invoke(
        app,
        [
            "specimens",
            "query",
            "--weight-min",
            str(weight_value - 0.1),
            "--weight-max",
            str(weight_value + 0.1),
            "--length-min",
            str(length_value - 0.1),
            "--length-max",
            str(length_value + 0.1),
            "--limit",
            "1",
            "--columns",
            "specimen_id,weight,length",
        ],
    )
    assert result.exit_code == 0
    assert sample["specimen_id"] in result.stdout


def test_mags_query_cli_supports_country_and_weight_ranges() -> None:
    sample = _sample_row(
        """
        SELECT m.mag_id, mgws.country, mgws.weight
        FROM mags AS m
        JOIN hologenomes_with_specimen AS mgws ON m.hologenome_id = mgws.hologenome_id
        WHERE mgws.country IS NOT NULL AND mgws.weight IS NOT NULL
        LIMIT 1
        """
    )
    weight_value = float(json.loads(sample["weight"])[0])
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--country",
            sample["country"],
            "--weight-min",
            str(weight_value - 0.1),
            "--weight-max",
            str(weight_value + 0.1),
            "--limit",
            "1",
            "--columns",
            "mag_id,country,weight",
        ],
    )
    assert result.exit_code == 0
    assert sample["mag_id"] in result.stdout


def test_mags_query_cli_with_host_filter() -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--columns",
            "mag_id,host_species",
        ],
    )
    assert result.exit_code == 0
    assert "EHM" in result.stdout


def test_specimens_query_cli_expands_host_taxid_descendants() -> None:
    result = runner.invoke(
        app,
        [
            "specimens",
            "query",
            "--host-taxid",
            "8509",
            "--limit",
            "1",
            "--columns",
            "specimen_id,host_taxid,host_order",
        ],
    )
    assert result.exit_code == 0
    assert "Squamata" in result.stdout


def test_mags_query_cli_filters_by_biome_descendants() -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--biome",
            "ENVO:01000175",
            "--limit",
            "1",
            "--columns",
            "mag_id,biome_envo_id,biome_name",
        ],
    )
    assert result.exit_code == 0
    assert "ENVO:01000221" in result.stdout or "ENVO:01000220" in result.stdout


def test_hologenomes_values_cli() -> None:
    result = runner.invoke(
        app,
        ["hologenomes", "values", "--field", "host_species", "--limit", "3"],
    )
    assert result.exit_code == 0
    assert "value" in result.output.lower()
    assert "count" in result.output.lower()


def test_hologenomes_fields_cli_lists_value_fields_and_aliases() -> None:
    result = runner.invoke(app, ["hologenomes", "fields", "--csv"])
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0] == "field,type,resolves_to"
    assert "country,field,country" in lines
    assert "biome_name,field,biome_name" in lines
    assert "biome,alias,biome_name" in lines


def test_mags_values_cli_supports_field_alias() -> None:
    result = runner.invoke(
        app,
        ["mags", "values", "--field", "genus", "--limit", "3"],
    )
    assert result.exit_code == 0
    assert "g__" not in result.output


def test_specimens_values_cli_writes_csv(tmp_path) -> None:
    output_path = tmp_path / "specimen-values.csv"
    result = runner.invoke(
        app,
        [
            "specimens",
            "values",
            "--field",
            "sex",
            "--limit",
            "5",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == "value,count"


def test_values_cli_rejects_unknown_field() -> None:
    result = runner.invoke(
        app,
        ["mags", "values", "--field", "nope"],
    )
    assert result.exit_code != 0
    assert "Unknown values field for mags: nope." in result.output


def test_hologenomes_query_cli_supports_hologenome_id_flag_with_multiple_values(tmp_path) -> None:
    samples = _sample_rows(
        """
        SELECT hologenome_id
        FROM hologenomes_with_specimen
        LIMIT 2
        """
    )
    requested_ids = ",".join(row["hologenome_id"] for row in samples)
    output_path = tmp_path / "hologenome-ids.csv"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--hologenome-id",
            requested_ids,
            "--columns",
            "hologenome_id",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    for sample in samples:
        assert sample["hologenome_id"] in contents


def test_mags_query_cli_supports_mag_id_flag_with_multiple_values(tmp_path) -> None:
    samples = _sample_rows(
        """
        SELECT mag_id
        FROM mags
        LIMIT 2
        """
    )
    requested_ids = ",".join(row["mag_id"] for row in samples)
    output_path = tmp_path / "mag-ids.csv"
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--mag-id",
            requested_ids,
            "--columns",
            "mag_id",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    for sample in samples:
        assert sample["mag_id"] in contents


def test_hologenomes_query_cli_writes_csv(tmp_path) -> None:
    output_path = tmp_path / "hologenomes.csv"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "hologenome_id" in contents
    assert "Podarcis muralis" in contents
    assert "Wrote 1 rows" in result.stderr


def test_specimens_query_cli_writes_tsv(tmp_path) -> None:
    output_path = tmp_path / "specimens.tsv"
    result = runner.invoke(
        app,
        [
            "specimens",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--tsv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "specimen_id\thost_taxid" in contents
    assert "Podarcis muralis" in contents
    assert "Wrote 1 rows" in result.stderr


def test_query_cli_rejects_csv_and_tsv_together(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--limit",
            "1",
            "--csv",
            "--tsv",
        ],
    )
    assert result.exit_code != 0
    assert "Use only one of --csv or --tsv." in result.output


def test_query_cli_rejects_output_file_without_csv_or_tsv(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--limit",
            "1",
            "--output-file",
            str(tmp_path / "out.csv"),
        ],
    )
    assert result.exit_code != 0
    assert "Use --output-file only with --csv or --tsv." in result.output


def test_query_cli_writes_csv_to_stdout_for_piping() -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--columns",
            "mag_id,host_species",
            "--csv",
        ],
    )
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0] == "mag_id,host_species"
    assert "Sciurus carolinensis" in lines[1]
    assert "MAGs" not in result.stdout


def test_values_cli_writes_tsv_to_stdout_for_piping() -> None:
    result = runner.invoke(
        app,
        [
            "specimens",
            "values",
            "--field",
            "sex",
            "--limit",
            "1",
            "--tsv",
        ],
    )
    assert result.exit_code == 0
    lines = result.stdout.splitlines()
    assert lines[0] == "value\tcount"
    assert "\t" in lines[1]
    assert "Values for" not in result.stdout


def test_query_cli_uses_default_columns_keyword(tmp_path) -> None:
    default_output_path = tmp_path / "hologenomes-default.csv"
    implicit_output_path = tmp_path / "hologenomes-implicit.csv"

    default_result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--columns",
            "default",
            "--csv",
            "--output-file",
            str(default_output_path),
        ],
    )
    implicit_result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--csv",
            "--output-file",
            str(implicit_output_path),
        ],
    )
    assert default_result.exit_code == 0
    assert implicit_result.exit_code == 0
    assert default_output_path.read_text(encoding="utf-8") == implicit_output_path.read_text(encoding="utf-8")
    contents = default_output_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == ",".join(_default_columns("hologenomes"))


def test_query_cli_writes_selected_columns_to_csv(tmp_path) -> None:
    output_path = tmp_path / "mags-columns.csv"
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--columns",
            "mag_id,host_species,mag_genus",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == "mag_id,host_species,mag_genus"


def test_mags_query_cli_default_columns_include_quality(tmp_path) -> None:
    output_path = tmp_path / "mags-default.csv"
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == ",".join(_default_columns("mags"))
    assert "quality" in contents.splitlines()[0].split(",")


def test_mags_query_cli_all_columns_include_quality(tmp_path) -> None:
    output_path = tmp_path / "mags-all.csv"
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--columns",
            "all",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert "quality" in contents.splitlines()[0].split(",")


def test_query_cli_writes_url_preset_for_hologenomes(tmp_path) -> None:
    output_path = tmp_path / "hologenomes-url.csv"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--columns",
            "url",
            "--csv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == "hologenome_id,url1,url2"


def test_query_cli_writes_url_preset_for_mags(tmp_path) -> None:
    output_path = tmp_path / "mags-url.tsv"
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--host-species",
            "Sciurus carolinensis",
            "--limit",
            "1",
            "--columns",
            "url",
            "--tsv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == "mag_id\turl"


def test_query_cli_columns_all_includes_extended_fields(tmp_path) -> None:
    output_path = tmp_path / "specimens-all.tsv"
    result = runner.invoke(
        app,
        [
            "specimens",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--columns",
            "all",
            "--tsv",
            "--output-file",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == (
        "specimen_id\thost_taxid\thost_species\thost_genus\thost_family\thost_order\t"
        "host_class\tweight\tlength\tsex"
    )


def test_query_cli_rejects_unknown_columns() -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--limit",
            "1",
            "--columns",
            "mag_id,nope",
        ],
    )
    assert result.exit_code != 0
    assert "Unknown columns for mags: nope." in result.output


def test_query_cli_rejects_url_preset_for_specimens() -> None:
    result = runner.invoke(
        app,
        [
            "specimens",
            "query",
            "--limit",
            "1",
            "--columns",
            "url",
        ],
    )
    assert result.exit_code != 0
    assert "Column preset 'url' is not available for" in result.output
    assert "Available presets: default." in result.output


def test_hologenomes_fetch_cli_writes_batch_script(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id
        FROM hologenomes_with_specimen
        WHERE url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> ''
        LIMIT 1
        """
    )
    db_path = ROOT_DB_PATH.resolve()
    batch_path = tmp_path / "hologenomes-fetch.sh"
    manifest_path = tmp_path / "manifest.jsonl"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "fetch",
            "--hologenome-id",
            sample["hologenome_id"],
            "--batch",
            str(batch_path),
            "--manifest-path",
            str(manifest_path),
            "--accept-terms",
            "--db",
            str(db_path),
        ],
    )
    assert result.exit_code == 0
    assert batch_path.exists()
    contents = batch_path.read_text(encoding="utf-8")
    assert contents.startswith("#!/usr/bin/env bash")
    assert contents.count("curl --fail --location --output") == 2
    assert sample["hologenome_id"] in contents
    assert "Wrote batch download script with 2 files" in result.output
    assert not manifest_path.exists()


def test_mags_fetch_cli_writes_batch_script(tmp_path) -> None:
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
    result = runner.invoke(
        app,
        [
            "mags",
            "fetch",
            "--mag-id",
            sample["mag_id"],
            "--batch",
            str(batch_path),
            "--manifest-path",
            str(manifest_path),
            "--accept-terms",
        ],
    )
    assert result.exit_code == 0
    assert batch_path.exists()
    contents = batch_path.read_text(encoding="utf-8")
    assert contents.startswith("#!/usr/bin/env bash")
    assert contents.count("curl --fail --location --output") == 1
    assert sample["mag_id"] in contents
    assert "Wrote batch download script with 1 files" in result.output
    assert not manifest_path.exists()


def test_hologenomes_fetch_batch_skips_missing_urls_without_manifest(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id
        FROM hologenomes_with_specimen
        WHERE url1 IS NULL AND url2 IS NULL
        LIMIT 1
        """
    )
    batch_path = tmp_path / "missing-urls.sh"
    manifest_path = tmp_path / "manifest.jsonl"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "fetch",
            "--hologenome-id",
            sample["hologenome_id"],
            "--batch",
            str(batch_path),
            "--manifest-path",
            str(manifest_path),
            "--accept-terms",
        ],
    )
    assert result.exit_code == 0
    assert batch_path.exists()
    contents = batch_path.read_text(encoding="utf-8")
    assert "curl --fail --location --output" not in contents
    assert "missing paired read URLs" in result.output
    assert "Wrote batch download script with 0 files" in result.output
    assert not manifest_path.exists()


def test_hologenomes_fetch_prompts_for_terms_and_accepts_with_input(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT hologenome_id
        FROM hologenomes_with_specimen
        WHERE url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> ''
        LIMIT 1
        """
    )
    batch_path = tmp_path / "terms-accepted.sh"
    result = runner.invoke(
        app,
        [
            "hologenomes",
            "fetch",
            "--hologenome-id",
            sample["hologenome_id"],
            "--batch",
            str(batch_path),
        ],
        input="y\n",
    )
    assert result.exit_code == 0
    assert batch_path.exists()


def test_mags_fetch_exits_when_terms_are_not_accepted(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT mag_id
        FROM mags
        WHERE url IS NOT NULL AND url <> ''
        LIMIT 1
        """
    )
    batch_path = tmp_path / "terms-declined.sh"
    result = runner.invoke(
        app,
        [
            "mags",
            "fetch",
            "--mag-id",
            sample["mag_id"],
            "--batch",
            str(batch_path),
        ],
        input="n\n",
    )
    assert result.exit_code == 1
    assert "Data Usage Terms" in result.output
    assert not batch_path.exists()


def test_hologenomes_stats_cli() -> None:
    result = runner.invoke(
        app,
        ["hologenomes", "stats", "--host-species", "Podarcis muralis"],
    )
    assert result.exit_code == 0
    assert "Matched hologenomes:" in result.output
    assert "Available data (GB total):" in result.output
    assert "Top sample types" in result.output
    assert "data_gb" in result.output


def test_mags_stats_cli_allows_combined_filters() -> None:
    result = runner.invoke(
        app,
        ["mags", "stats", "--quality", "high", "--species", "Escherichia coli"],
    )
    assert result.exit_code == 0
    assert "Matched MAGs:" in result.output
    assert "Parent hologenome data (GB total):" in result.output
    assert "Quality" in result.output
    assert "distribution" in result.output


def test_mags_stats_cli_allows_multiple_quality_values() -> None:
    result = runner.invoke(
        app,
        ["mags", "stats", "--quality", "high,medium"],
    )
    assert result.exit_code == 0
    assert "Matched MAGs:" in result.output


def test_specimens_stats_cli() -> None:
    result = runner.invoke(
        app,
        ["specimens", "stats", "--host-lineage", "Reptilia"],
    )
    assert result.exit_code == 0
    assert "Matched specimens:" in result.output
    assert "Sex distribution" in result.output
