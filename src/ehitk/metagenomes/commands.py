from __future__ import annotations

from collections import Counter
from pathlib import Path

from rich.console import Console
import typer

from ehitk.download import DownloadJob, destination_for_url, download_jobs, write_batch_script
from ehitk.manifest import ManifestEntry, append_manifest_entry
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

app = typer.Typer(help="Query, summarize, and fetch metagenomes.", no_args_is_help=True)


@app.command()
def query(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    metagenome_id: str | None = typer.Option(
        None,
        help="Exact metagenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    latitude_min: float | None = typer.Option(None, help="Minimum latitude."),
    latitude_max: float | None = typer.Option(None, help="Maximum latitude."),
    longitude_min: float | None = typer.Option(None, help="Minimum longitude."),
    longitude_max: float | None = typer.Option(None, help="Maximum longitude."),
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
        "metagenome_id": metagenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "country": country,
        "release": release,
        "latitude_min": latitude_min,
        "latitude_max": latitude_max,
        "longitude_min": longitude_min,
        "longitude_max": longitude_max,
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx, db),
            "metagenomes",
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
        headers_for("metagenomes", columns=columns),
        rows,
        title="Metagenomes",
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
    metagenome_id: str | None = typer.Option(
        None,
        help="Exact metagenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    latitude_min: float | None = typer.Option(None, help="Minimum latitude."),
    latitude_max: float | None = typer.Option(None, help="Maximum latitude."),
    longitude_min: float | None = typer.Option(None, help="Minimum longitude."),
    longitude_max: float | None = typer.Option(None, help="Maximum longitude."),
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
        "metagenome_id": metagenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "country": country,
        "release": release,
        "latitude_min": latitude_min,
        "latitude_max": latitude_max,
        "longitude_min": longitude_min,
        "longitude_max": longitude_max,
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        resolved_field, rows = value_rows(
            str(catalog_path_from_context(ctx, db)),
            target="metagenomes",
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
def fetch(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    metagenome_id: str | None = typer.Option(
        None,
        help="Exact metagenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    latitude_min: float | None = typer.Option(None, help="Minimum latitude."),
    latitude_max: float | None = typer.Option(None, help="Maximum latitude."),
    longitude_min: float | None = typer.Option(None, help="Minimum longitude."),
    longitude_max: float | None = typer.Option(None, help="Maximum longitude."),
    weight_min: float | None = typer.Option(None, help="Minimum specimen weight."),
    weight_max: float | None = typer.Option(None, help="Maximum specimen weight."),
    length_min: float | None = typer.Option(None, help="Minimum specimen length."),
    length_max: float | None = typer.Option(None, help="Maximum specimen length."),
    where: str | None = typer.Option(
        None,
        help="Advanced SQL predicate appended to the WHERE clause after validation.",
    ),
    limit: int | None = typer.Option(
        None,
        min=1,
        help="Maximum number of matching metagenomes to fetch.",
    ),
    output_dir: Path = typer.Option(
        Path("downloads"),
        help="Base output directory for downloaded files.",
    ),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        help="Write a shell script with curl download commands instead of downloading now.",
    ),
    manifest_path: Path = typer.Option(
        Path("manifest.jsonl"),
        help="Path to the append-only download manifest.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files instead of skipping them.",
    ),
) -> None:
    console = Console()
    filters = {
        "metagenome_id": metagenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "country": country,
        "release": release,
        "latitude_min": latitude_min,
        "latitude_max": latitude_max,
        "longitude_min": longitude_min,
        "longitude_max": longitude_max,
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx, db),
            "metagenomes",
            filters=filters,
            where=where,
            limit=limit,
            fetch=True,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

    if not rows:
        console.print("No matching metagenomes found.")
        return

    jobs: list[DownloadJob] = []
    missing_url_count = 0
    for row in rows:
        metagenome_id = row["metagenome_id"]
        url1 = row["url1"]
        url2 = row["url2"]

        if not url1 or not url2:
            missing_url_count += 1
            if batch is None:
                append_manifest_entry(
                    manifest_path,
                    ManifestEntry(
                        entry_type="metagenome",
                        id_field="metagenome_id",
                        id_value=metagenome_id,
                        url=None,
                        path=None,
                        checksum=None,
                        status="missing_url",
                    ),
                )
            console.print(f"[yellow]Skipping[/yellow] {metagenome_id}: missing paired read URLs.")
            continue

        base_directory = output_dir / "metagenomes" / metagenome_id
        jobs.append(
            DownloadJob(
                entry_type="metagenome",
                id_field="metagenome_id",
                id_value=metagenome_id,
                url=url1,
                destination=destination_for_url(
                    base_directory,
                    url1,
                    fallback_name=f"{metagenome_id}_1.fastq.gz",
                ),
            )
        )
        jobs.append(
            DownloadJob(
                entry_type="metagenome",
                id_field="metagenome_id",
                id_value=metagenome_id,
                url=url2,
                destination=destination_for_url(
                    base_directory,
                    url2,
                    fallback_name=f"{metagenome_id}_2.fastq.gz",
                ),
            )
        )

    console.print(
        f"Matched {len(rows)} metagenomes; queued {len(jobs)} files for download."
    )
    if missing_url_count:
        console.print(f"{missing_url_count} metagenomes were skipped because URLs were missing.")

    if batch is not None:
        script_path = write_batch_script(batch, jobs, overwrite=overwrite)
        console.print(f"Wrote batch download script with {len(jobs)} files to {script_path}.")
        return

    results = download_jobs(
        jobs,
        manifest_path=manifest_path,
        overwrite=overwrite,
        console=console,
    )
    _print_fetch_summary(console, results)


@app.command()
def stats(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    metagenome_id: str | None = typer.Option(
        None,
        help="Exact metagenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    latitude_min: float | None = typer.Option(None, help="Minimum latitude."),
    latitude_max: float | None = typer.Option(None, help="Maximum latitude."),
    longitude_min: float | None = typer.Option(None, help="Minimum longitude."),
    longitude_max: float | None = typer.Option(None, help="Maximum longitude."),
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
        "metagenome_id": metagenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "country": country,
        "release": release,
        "latitude_min": latitude_min,
        "latitude_max": latitude_max,
        "longitude_min": longitude_min,
        "longitude_max": longitude_max,
        "weight_min": weight_min,
        "weight_max": weight_max,
        "length_min": length_min,
        "length_max": length_max,
    }

    try:
        render_target_stats(
            console,
            catalog_path=str(catalog_path_from_context(ctx, db)),
            target="metagenomes",
            filters=filters,
            where=where,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

def _print_fetch_summary(console: Console, results: list) -> None:
    if not results:
        console.print("No files were queued for download.")
        return

    counts = Counter(result.status for result in results)
    summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    console.print(f"Download summary: {summary}")
