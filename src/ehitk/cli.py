from __future__ import annotations

from pathlib import Path
import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from ehitk import __version__
from ehitk.mags.commands import app as mags_app
from ehitk.metagenomes.commands import app as metagenomes_app
from ehitk.specimens.commands import app as specimens_app
from ehitk.query import resolve_catalog_path

app = typer.Typer(
    help="Earth Hologenome Initiative Toolkit",
    no_args_is_help=False,
    add_completion=False,
)

app.add_typer(specimens_app, name="specimens")
app.add_typer(metagenomes_app, name="metagenomes")
app.add_typer(mags_app, name="mags")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show EHItk version and exit.",
    ),
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
) -> None:
    catalog_path = resolve_catalog_path(db)
    if not catalog_path.exists():
        raise typer.BadParameter(
            f"Database does not exist: {catalog_path}",
            param_hint="--db",
        )

    ctx.obj = {"catalog_path": catalog_path}

    if ctx.invoked_subcommand is None:
        _print_root_overview(catalog_path)
        raise typer.Exit()


def _print_root_overview(database_path: Path) -> None:
    console = Console()
    console.print(
        Panel.fit(
            "[bold]Earth Hologenome Initiative ToolKit[/bold]",
            border_style="cyan",
        )
    )
    console.print(
        "Query, summarize, and fetch specimens, metagenomes, and MAGs from the EHI."
    )
    console.print()

    summary = _catalog_summary(database_path)
    table = Table(title="Database Snapshot")
    table.add_column("Level")
    table.add_column("Records", justify="right")
    table.add_column("Summary")
    for row in summary:
        table.add_row(row["level"], row["records"], row["summary"])
    console.print(table)
    console.print("Use `ehitk --help` to see all commands.")


def _catalog_summary(database_path: Path) -> tuple[dict[str, str], ...]:
    with sqlite3.connect(database_path) as connection:
        specimens = connection.execute(
            """
            SELECT
                COUNT(*) AS records,
                COUNT(DISTINCT host_species) AS host_species
            FROM specimens
            """
        ).fetchone()
        metagenomes = connection.execute(
            """
            SELECT
                COUNT(*) AS records,
                SUM(CASE WHEN url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> '' THEN 1 ELSE 0 END) AS paired_urls
            FROM metagenomes
            """
        ).fetchone()
        mags = connection.execute(
            """
            SELECT
                COUNT(*) AS records,
                COUNT(DISTINCT metagenome_id) AS parent_metagenomes
            FROM mags
            """
        ).fetchone()

    return (
        {
            "level": "Specimens",
            "records": f"{specimens[0]:,}",
            "summary": f"{specimens[1]:,} host species",
        },
        {
            "level": "Metagenomes",
            "records": f"{metagenomes[0]:,}",
            "summary": f"{metagenomes[1]:,} paired read sets",
        },
        {
            "level": "MAGs",
            "records": f"{mags[0]:,}",
            "summary": f"{mags[1]:,} parent metagenomes",
        },
    )


if __name__ == "__main__":
    app()
