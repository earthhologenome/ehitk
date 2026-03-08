from pathlib import Path

from typer.testing import CliRunner

from ehitk import __version__
from ehitk.cli import app

runner = CliRunner()


def test_root_command_shows_overview_in_fixed_order() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Earth Hologenome Initiative ToolKit" in result.output
    assert "Query, summarize, and fetch specimens, metagenomes, and MAGs" in result.output
    assert "Catalog Snapshot" in result.output

    specimens_index = result.output.rindex("Specimens")
    metagenomes_index = result.output.rindex("Metagenomes")
    mags_index = result.output.rindex("MAGs")
    assert specimens_index < metagenomes_index < mags_index


def test_root_help_shows_db_and_hides_completion_options() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--db" in result.output
    assert "--version" in result.output
    assert "--catalog" not in result.output
    assert "--install-completion" not in result.output
    assert "--show-completion" not in result.output

    specimens_index = result.output.index("specimens")
    metagenomes_index = result.output.index("metagenomes")
    mags_index = result.output.index("mags")
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
    assert contents[0] == (
        "metagenome_id,specimen_id,release,sample_type,host_species,host_genus,biome"
    )


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


def test_metagenomes_stats_cli() -> None:
    result = runner.invoke(
        app,
        ["metagenomes", "stats", "--host-species", "Podarcis muralis"],
    )
    assert result.exit_code == 0
    assert "Matched metagenomes:" in result.output
    assert "Top sample types" in result.output


def test_mags_stats_cli_allows_combined_filters() -> None:
    result = runner.invoke(
        app,
        ["mags", "stats", "--quality", "high", "--species", "Escherichia coli"],
    )
    assert result.exit_code == 0
    assert "Matched MAGs:" in result.output
    assert "Quality" in result.output
    assert "distribution" in result.output


def test_specimens_stats_cli() -> None:
    result = runner.invoke(
        app,
        ["specimens", "stats", "--host-lineage", "Reptilia"],
    )
    assert result.exit_code == 0
    assert "Matched specimens:" in result.output
    assert "Sex distribution" in result.output
