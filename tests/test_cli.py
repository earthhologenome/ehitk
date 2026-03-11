import json
from pathlib import Path
import re
import sqlite3

from typer.testing import CliRunner

from ehitk import __version__
from ehitk.cli import app

runner = CliRunner()
ANSI_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
ROOT_DB_PATH = Path("data/ehitk.sqlite")
if not ROOT_DB_PATH.exists():
    ROOT_DB_PATH = Path("src/ehitk/data/ehitk.sqlite")


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
    with sqlite3.connect("src/ehitk/data/ehitk.sqlite") as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql).fetchone()
    if row is None:
        raise AssertionError("Expected sample row for test setup.")
    return row


def _sample_rows(sql: str) -> list[sqlite3.Row]:
    with sqlite3.connect("src/ehitk/data/ehitk.sqlite") as connection:
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
    assert "Query, summarize, and fetch specimens, metagenomes, and MAGs" in result.output
    assert "Level" in result.output
    assert "Records" in result.output
    assert "Summary" in result.output

    specimens_index = result.output.rindex("Specimens")
    metagenomes_index = result.output.rindex("Metagenomes")
    mags_index = result.output.rindex("MAGs")
    assert specimens_index < metagenomes_index < mags_index

    specimens = _root_summary_row("SELECT COUNT(*) AS records FROM specimens")
    metagenomes = _root_summary_row(
        """
        SELECT
            COUNT(*) AS records,
            SUM(CASE WHEN url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> '' THEN 1 ELSE 0 END) AS paired_urls,
            SUM(data) AS total_data_gb
        FROM metagenomes
        """
    )
    mags = _root_summary_row(
        """
        SELECT
            (SELECT COUNT(*) FROM mags) AS records,
            COUNT(*) AS parent_metagenomes,
            SUM(data) AS total_parent_data_gb
        FROM (
            SELECT DISTINCT metagenome_id, data
            FROM mags_with_metagenome
            WHERE metagenome_id IS NOT NULL
        )
        """
    )
    assert f"{specimens['records']:,}" in result.output
    assert f"{metagenomes['records']:,}" in result.output
    assert f"{mags['records']:,}" in result.output
    assert (
        f"{metagenomes['paired_urls']:,} paired read sets, "
        f"{_format_gb(metagenomes['total_data_gb'])} GB"
    ) in result.output
    assert (
        f"{mags['parent_metagenomes']:,} parent metagenomes, "
        f"{_format_gb(mags['total_parent_data_gb'])} GB"
    ) in result.output


def test_root_help_shows_db_and_hides_completion_options() -> None:
    result = runner.invoke(app, ["--help"])
    output = _strip_ansi(result.output)
    assert result.exit_code == 0
    assert "--db" in output
    assert "--version" in output
    assert "--catalog" not in output
    assert "--install-completion" not in output
    assert "--show-completion" not in output

    specimens_index = output.index("specimens")
    metagenomes_index = output.index("metagenomes")
    mags_index = output.index("mags")
    assert specimens_index < metagenomes_index < mags_index


def test_root_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_package_version_matches_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in pyproject


def test_metagenomes_query_cli() -> None:
    result = runner.invoke(
        app,
        ["metagenomes", "query", "--host-species", "Podarcis muralis", "--limit", "1"],
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


def test_metagenomes_query_cli_supports_country_and_coordinate_ranges() -> None:
    sample = _sample_row(
        """
        SELECT metagenome_id, country, latitude, longitude
        FROM metagenomes_with_specimen
        WHERE country IS NOT NULL AND latitude IS NOT NULL AND longitude IS NOT NULL
        LIMIT 1
        """
    )
    result = runner.invoke(
        app,
        [
            "metagenomes",
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
            "metagenome_id,country,latitude,longitude",
        ],
    )
    assert result.exit_code == 0
    assert sample["metagenome_id"] in result.stdout


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
        JOIN metagenomes_with_specimen AS mgws ON m.metagenome_id = mgws.metagenome_id
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


def test_metagenomes_values_cli() -> None:
    result = runner.invoke(
        app,
        ["metagenomes", "values", "--field", "host_species", "--limit", "3"],
    )
    assert result.exit_code == 0
    assert "value" in result.output.lower()
    assert "count" in result.output.lower()


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


def test_metagenomes_query_cli_supports_metagenome_id_flag_with_multiple_values(tmp_path) -> None:
    samples = _sample_rows(
        """
        SELECT metagenome_id
        FROM metagenomes_with_specimen
        LIMIT 2
        """
    )
    requested_ids = ",".join(row["metagenome_id"] for row in samples)
    output_path = tmp_path / "metagenome-ids.csv"
    result = runner.invoke(
        app,
        [
            "metagenomes",
            "query",
            "--metagenome-id",
            requested_ids,
            "--columns",
            "metagenome_id",
            "--csv",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    for sample in samples:
        assert sample["metagenome_id"] in contents


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
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    for sample in samples:
        assert sample["mag_id"] in contents


def test_metagenomes_query_cli_writes_csv(tmp_path) -> None:
    output_path = tmp_path / "metagenomes.csv"
    result = runner.invoke(
        app,
        [
            "metagenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--csv",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "metagenome_id" in contents
    assert "Podarcis muralis" in contents
    assert "Wrote 1 rows" in result.stdout


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
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    assert output_path.exists()
    contents = output_path.read_text(encoding="utf-8")
    assert "specimen_id\thost_taxid" in contents
    assert "Podarcis muralis" in contents
    assert "Wrote 1 rows" in result.stdout


def test_query_cli_rejects_csv_and_tsv_together(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "mags",
            "query",
            "--limit",
            "1",
            "--csv",
            str(tmp_path / "out.csv"),
            "--tsv",
            str(tmp_path / "out.tsv"),
        ],
    )
    assert result.exit_code != 0
    assert "Use only one of --csv or --tsv." in result.output


def test_query_cli_uses_default_columns_keyword(tmp_path) -> None:
    default_output_path = tmp_path / "metagenomes-default.csv"
    implicit_output_path = tmp_path / "metagenomes-implicit.csv"

    default_result = runner.invoke(
        app,
        [
            "metagenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--columns",
            "default",
            "--csv",
            str(default_output_path),
        ],
    )
    implicit_result = runner.invoke(
        app,
        [
            "metagenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--csv",
            str(implicit_output_path),
        ],
    )
    assert default_result.exit_code == 0
    assert implicit_result.exit_code == 0
    assert default_output_path.read_text(encoding="utf-8") == implicit_output_path.read_text(encoding="utf-8")
    contents = default_output_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == ",".join(_default_columns("metagenomes"))


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
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == "mag_id,host_species,mag_genus"


def test_query_cli_writes_url_preset_for_metagenomes(tmp_path) -> None:
    output_path = tmp_path / "metagenomes-url.csv"
    result = runner.invoke(
        app,
        [
            "metagenomes",
            "query",
            "--host-species",
            "Podarcis muralis",
            "--limit",
            "1",
            "--columns",
            "url",
            "--csv",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8")
    assert contents.splitlines()[0] == "metagenome_id,url1,url2"


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


def test_metagenomes_fetch_cli_writes_batch_script(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT metagenome_id
        FROM metagenomes_with_specimen
        WHERE url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> ''
        LIMIT 1
        """
    )
    db_path = Path("data/ehitk.sqlite").resolve()
    batch_path = tmp_path / "metagenomes-fetch.sh"
    manifest_path = tmp_path / "manifest.jsonl"
    result = runner.invoke(
        app,
        [
            "metagenomes",
            "fetch",
            "--metagenome-id",
            sample["metagenome_id"],
            "--batch",
            str(batch_path),
            "--manifest-path",
            str(manifest_path),
            "--db",
            str(db_path),
        ],
    )
    assert result.exit_code == 0
    assert batch_path.exists()
    contents = batch_path.read_text(encoding="utf-8")
    assert contents.startswith("#!/usr/bin/env bash")
    assert contents.count("curl --fail --location --output") == 2
    assert sample["metagenome_id"] in contents
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


def test_metagenomes_fetch_batch_skips_missing_urls_without_manifest(tmp_path) -> None:
    sample = _sample_row(
        """
        SELECT metagenome_id
        FROM metagenomes_with_specimen
        WHERE url1 IS NULL AND url2 IS NULL
        LIMIT 1
        """
    )
    batch_path = tmp_path / "missing-urls.sh"
    manifest_path = tmp_path / "manifest.jsonl"
    result = runner.invoke(
        app,
        [
            "metagenomes",
            "fetch",
            "--metagenome-id",
            sample["metagenome_id"],
            "--batch",
            str(batch_path),
            "--manifest-path",
            str(manifest_path),
        ],
    )
    assert result.exit_code == 0
    assert batch_path.exists()
    contents = batch_path.read_text(encoding="utf-8")
    assert "curl --fail --location --output" not in contents
    assert "missing paired read URLs" in result.output
    assert "Wrote batch download script with 0 files" in result.output
    assert not manifest_path.exists()


def test_metagenomes_stats_cli() -> None:
    result = runner.invoke(
        app,
        ["metagenomes", "stats", "--host-species", "Podarcis muralis"],
    )
    assert result.exit_code == 0
    assert "Matched metagenomes:" in result.output
    assert "Available data (GB total):" in result.output
    assert "Top sample types" in result.output


def test_mags_stats_cli_allows_combined_filters() -> None:
    result = runner.invoke(
        app,
        ["mags", "stats", "--quality", "high", "--species", "Escherichia coli"],
    )
    assert result.exit_code == 0
    assert "Matched MAGs:" in result.output
    assert "Parent metagenome data (GB total):" in result.output
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
