from __future__ import annotations

from rich.console import Console
from rich.table import Table
import typer

from ehitk.query import (
    DEFAULT_QUERY_LIMIT,
    QueryValidationError,
    catalog_path_from_context,
    headers_for,
    query_rows,
)

app = typer.Typer(help="Query specimens.", no_args_is_help=True)


@app.command()
def query(
    ctx: typer.Context,
    specimen_id: str | None = typer.Option(None, help="Exact specimen ID."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sex: str | None = typer.Option(None, help="Exact sex label."),
    where: str | None = typer.Option(
        None,
        help="Advanced SQL predicate appended to the WHERE clause after validation.",
    ),
    limit: int = typer.Option(
        DEFAULT_QUERY_LIMIT,
        min=1,
        help="Maximum number of rows to print.",
    ),
) -> None:
    console = Console()
    filters = {
        "specimen_id": specimen_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sex": sex,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx),
            "specimens",
            filters=filters,
            where=where,
            limit=limit,
            fetch=False,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

    _render_rows(console, headers_for("specimens"), rows, title="Specimens")


def _render_rows(
    console: Console,
    headers: tuple[str, ...],
    rows: list[dict],
    *,
    title: str,
) -> None:
    if not rows:
        console.print(f"No matching {title.lower()} found.")
        return

    table = Table(title=title)
    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*(str(row[header]) if row[header] is not None else "" for header in headers))

    console.print(table)
