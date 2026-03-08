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
