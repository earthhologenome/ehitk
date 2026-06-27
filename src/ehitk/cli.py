from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer
from typer.core import TyperGroup

from ehitk import __version__
from ehitk.mags.commands import app as mags_app
from ehitk.hologenomes.commands import app as hologenomes_app
from ehitk.specimens.commands import app as specimens_app
from ehitk.query import resolve_catalog_path

ROOT_TITLE = "Earth Hologenome Initiative ToolKit"
ROOT_DESCRIPTION = "Query, summarize, and fetch specimens, hologenomes, and MAGs from the EHI."


class RootHeaderGroup(TyperGroup):
    def format_help(self, ctx, formatter) -> None:
        if self.rich_markup_mode is not None:
            from typer import rich_utils

            console = rich_utils._get_rich_console()
            _print_root_header(console)
            console.print()
            return rich_utils.rich_format_help(
                obj=self,
                ctx=ctx,
                markup_mode=self.rich_markup_mode,
            )

        formatter.write(_render_root_header_text())
        formatter.write("\n\n")
        return super().format_help(ctx, formatter)


app = typer.Typer(
    cls=RootHeaderGroup,
    help=ROOT_DESCRIPTION,
    no_args_is_help=False,
    add_completion=False,
)

app.add_typer(specimens_app, name="specimens")
app.add_typer(hologenomes_app, name="hologenomes")
app.add_typer(mags_app, name="mags")

from typer import rich_utils

_ORIGINAL_RICH_FORMAT_ERROR = rich_utils.rich_format_error


def _rich_format_error_with_root_header(self) -> None:
    ctx = getattr(self, "ctx", None)
    if ctx is not None and isinstance(ctx.find_root().command, RootHeaderGroup):
        _print_root_header(Console(stderr=True))
        Console(stderr=True).print()
    _ORIGINAL_RICH_FORMAT_ERROR(self)


rich_utils.rich_format_error = _rich_format_error_with_root_header


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


@app.command("database")
def database(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
) -> None:
    """Show the SQLite catalog currently used by EHItk."""
    catalog_path = (
        resolve_catalog_path(db) if db is not None else Path(ctx.obj["catalog_path"])
    )
    if not catalog_path.exists():
        raise typer.BadParameter(
            f"Database does not exist: {catalog_path}",
            param_hint="--db",
        )
    default_path = resolve_catalog_path(None)
    source = "bundled" if catalog_path == default_path else "custom"
    details = {
        "Package version": __version__,
        "Catalog source": source,
        "Catalog path": str(catalog_path),
        "Catalog size": _format_bytes(catalog_path.stat().st_size),
        "SHA256": _file_sha256(catalog_path),
    }

    console = Console()
    console.print("Database Catalog", style="bold")
    for field, value in details.items():
        console.print(f"{field}: {value}")


def _print_root_overview(database_path: Path) -> None:
    console = Console()
    _print_root_header(console)
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


def _file_sha256(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _format_bytes(size: int) -> str:
    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        value /= 1024
    return f"{size} B"


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
        hologenomes = connection.execute(
            """
            SELECT
                COUNT(*) AS records,
                SUM(CASE WHEN url1 IS NOT NULL AND url1 <> '' AND url2 IS NOT NULL AND url2 <> '' THEN 1 ELSE 0 END) AS paired_urls,
                SUM(data) AS total_data_gb
            FROM hologenomes
            """
        ).fetchone()
        mags = connection.execute(
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
        ).fetchone()

    return (
        {
            "level": "Specimens",
            "records": f"{specimens[0]:,}",
            "summary": f"{specimens[1]:,} host species",
        },
        {
            "level": "Hologenomes",
            "records": f"{hologenomes[0]:,}",
            "summary": (
                f"{hologenomes[1]:,} paired read sets, {_format_gb(hologenomes[2])} GB"
            ),
        },
        {
            "level": "MAGs",
            "records": f"{mags[0]:,}",
            "summary": (
                f"{mags[1]:,} parent hologenomes, {_format_gb(mags[2])} GB"
            ),
        },
    )


def _format_gb(value: float | int | None) -> str:
    if value is None:
        return "0.00"
    return f"{value:,.2f}"


def _print_root_header(console: Console) -> None:
    console.print(Panel.fit(f"[bold]{ROOT_TITLE}[/bold]", border_style="cyan"))
    console.print(ROOT_DESCRIPTION)


def _render_root_header_text() -> str:
    console = Console(record=True, color_system=None, force_terminal=False, width=80)
    _print_root_header(console)
    return console.export_text().rstrip()


if __name__ == "__main__":
    app()
