from typer.testing import CliRunner

from ehitk.cli import app

runner = CliRunner()


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
        ["mags", "query", "--genus", "Escherichia", "--limit", "1"],
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
        ["mags", "query", "--host-species", "Sciurus carolinensis", "--limit", "1"],
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
    output_path = tmp_path / "metagenomes-default.csv"
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
            "default",
            "--csv",
            str(output_path),
        ],
    )
    assert result.exit_code == 0
    contents = output_path.read_text(encoding="utf-8").splitlines()
    assert contents[0] == "metagenome_id,specimen_id,release,sample_type,host_species,host_genus,biome"


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
