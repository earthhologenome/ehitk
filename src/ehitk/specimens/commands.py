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
from ehitk.values import DEFAULT_VALUES_LIMIT, value_rows

app = typer.Typer(help="Query and summarize specimens.", no_args_is_help=True)


@app.command()
def query(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    specimen_id: str | None = typer.Option(None, help="Exact specimen ID."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sex: str | None = typer.Option(None, help="Exact sex label."),
    weight_min: float | None = typer.Option(None, help="Minimum specimen weight."),
    weight_max: float | None = typer.Option(None, help="Maximum specimen weight."),
    length_min: float | None = typer.Option(None, help="Minimum specimen length."),
    length_max: float | None = typer.Option(None, help="Maximum specimen length."),
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
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx, db),
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
def values(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    field: str = typer.Option(
        ...,
        "--field",
        help="Field to summarize with distinct values and counts.",
    ),
    specimen_id: str | None = typer.Option(None, help="Exact specimen ID."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sex: str | None = typer.Option(None, help="Exact sex label."),
    weight_min: float | None = typer.Option(None, help="Minimum specimen weight."),
    weight_max: float | None = typer.Option(None, help="Maximum specimen weight."),
    length_min: float | None = typer.Option(None, help="Minimum specimen length."),
    length_max: float | None = typer.Option(None, help="Maximum specimen length."),
    where: str | None = typer.Option(
        None,
        help="Advanced SQL predicate appended to the WHERE clause after validation.",
    ),
    limit: int = typer.Option(
        DEFAULT_VALUES_LIMIT,
        min=1,
        help="Maximum number of distinct values to print.",
    ),
    csv: Path | None = typer.Option(
        None,
        "--csv",
        help="Write value counts to a CSV file instead of displaying a table.",
    ),
    tsv: Path | None = typer.Option(
        None,
        "--tsv",
        help="Write value counts to a TSV file instead of displaying a table.",
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
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        resolved_field, rows = value_rows(
            str(catalog_path_from_context(ctx, db)),
            target="specimens",
            field=field,
            filters=filters,
            where=where,
            limit=limit,
        )
    except QueryValidationError as exc:
        message = str(exc).lower()
        param_hint = "--field" if "field" in message else "--where"
        if "limit" in message:
            param_hint = "--limit"
        raise typer.BadParameter(str(exc), param_hint=param_hint) from exc

    render_or_export_rows(
        console,
        ("value", "count"),
        rows,
        title=f"Values for {resolved_field}",
        csv_path=csv,
        tsv_path=tsv,
    )


@app.command()
def stats(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    specimen_id: str | None = typer.Option(None, help="Exact specimen ID."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sex: str | None = typer.Option(None, help="Exact sex label."),
    weight_min: float | None = typer.Option(None, help="Minimum specimen weight."),
    weight_max: float | None = typer.Option(None, help="Maximum specimen weight."),
    length_min: float | None = typer.Option(None, help="Minimum specimen length."),
    length_max: float | None = typer.Option(None, help="Maximum specimen length."),
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
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        render_target_stats(
            console,
            catalog_path=str(catalog_path_from_context(ctx, db)),
            target="specimens",
            filters=filters,
            where=where,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc
