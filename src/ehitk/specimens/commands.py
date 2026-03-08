from __future__ import annotations

from pathlib import Path

from rich.console import Console
import typer

from ehitk.output import render_or_export_rows, validate_export_paths
from ehitk.query import (
    DEFAULT_QUERY_LIMIT,
    QueryValidationError,
    catalog_path_from_context,
    headers_for,
    query_rows,
)
from ehitk.stats import render_target_stats

app = typer.Typer(help="Query and summarize specimens.", no_args_is_help=True)


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
    columns: str | None = typer.Option(
        None,
        "--columns",
        help="Query columns to include: default, all, or a comma-separated list.",
    ),
    csv: Path | None = typer.Option(
        None,
        "--csv",
        help="Write query results to a CSV file instead of displaying a table.",
    ),
    tsv: Path | None = typer.Option(
        None,
        "--tsv",
        help="Write query results to a TSV file instead of displaying a table.",
    ),
) -> None:
    console = Console()
    validate_export_paths(csv, tsv)

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
            columns=columns,
        )
    except QueryValidationError as exc:
        param_hint = "--columns" if "column" in str(exc).lower() else "--where"
        raise typer.BadParameter(str(exc), param_hint=param_hint) from exc

    render_or_export_rows(
        console,
        headers_for("specimens", columns=columns),
        rows,
        title="Specimens",
        csv_path=csv,
        tsv_path=tsv,
    )


@app.command()
def stats(
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
        render_target_stats(
            console,
            catalog_path=str(catalog_path_from_context(ctx)),
            target="specimens",
            filters=filters,
            where=where,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc
