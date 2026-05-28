from __future__ import annotations

from collections import Counter
from pathlib import Path

from rich.console import Console
import typer

from ehitk.download import DownloadJob, destination_for_url, download_jobs, write_batch_script
from ehitk.manifest import ManifestEntry, append_manifest_entry
from ehitk.output import render_or_export_rows, validate_export_options
from ehitk.query import (
    DEFAULT_QUERY_LIMIT,
    QueryValidationError,
    catalog_path_from_context,
    headers_for,
    query_rows,
)
from ehitk.stats import render_target_stats
from ehitk.terms import ensure_terms_accepted
from ehitk.values import DEFAULT_VALUES_LIMIT, value_rows

app = typer.Typer(help="Query, summarize, and fetch hologenomes.", no_args_is_help=True)


@app.command(help="List hologenome records that match host, sample, geography, and data filters.")
def query(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    hologenome_id: str | None = typer.Option(
        None,
        help="Exact hologenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Host taxon ID; catalog descendants are included."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome_envo_id: str | None = typer.Option(
        None,
        "--biome-envo-id",
        "--biome",
        help="ENVO biome identifier; catalog descendants are included, e.g. ENVO:01000175.",
    ),
    biome_name: str | None = typer.Option(None, "--biome-name", help="Exact biome name."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    data_min: float | None = typer.Option(None, help="Minimum available data in GB."),
    data_max: float | None = typer.Option(None, help="Maximum available data in GB."),
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
    csv: bool = typer.Option(
        False,
        "--csv",
        help="Write query results as CSV to stdout, or to --output-file.",
    ),
    tsv: bool = typer.Option(
        False,
        "--tsv",
        help="Write query results as TSV to stdout, or to --output-file.",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output-file",
        help="Write CSV or TSV output to this file instead of stdout.",
    ),
) -> None:
    console = Console()
    validate_export_options(csv, tsv, output_file)

    filters = {
        "hologenome_id": hologenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome_envo_id": biome_envo_id,
        "biome_name": biome_name,
        "country": country,
        "release": release,
        "data_min": data_min,
        "data_max": data_max,
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
            "hologenomes",
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
        headers_for("hologenomes", columns=columns),
        rows,
        title="Hologenomes",
        csv_output=csv,
        tsv_output=tsv,
        output_file=output_file,
    )


@app.command(help="Count distinct values for a hologenome field after applying filters.")
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
    hologenome_id: str | None = typer.Option(
        None,
        help="Exact hologenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Host taxon ID; catalog descendants are included."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome_envo_id: str | None = typer.Option(
        None,
        "--biome-envo-id",
        "--biome",
        help="ENVO biome identifier; catalog descendants are included, e.g. ENVO:01000175.",
    ),
    biome_name: str | None = typer.Option(None, "--biome-name", help="Exact biome name."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    data_min: float | None = typer.Option(None, help="Minimum available data in GB."),
    data_max: float | None = typer.Option(None, help="Maximum available data in GB."),
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
    csv: bool = typer.Option(
        False,
        "--csv",
        help="Write value counts as CSV to stdout, or to --output-file.",
    ),
    tsv: bool = typer.Option(
        False,
        "--tsv",
        help="Write value counts as TSV to stdout, or to --output-file.",
    ),
    output_file: Path | None = typer.Option(
        None,
        "--output-file",
        help="Write CSV or TSV output to this file instead of stdout.",
    ),
) -> None:
    console = Console()
    validate_export_options(csv, tsv, output_file)

    filters = {
        "hologenome_id": hologenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome_envo_id": biome_envo_id,
        "biome_name": biome_name,
        "country": country,
        "release": release,
        "data_min": data_min,
        "data_max": data_max,
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
            target="hologenomes",
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
        csv_output=csv,
        tsv_output=tsv,
        output_file=output_file,
    )


@app.command(help="Download matching paired-read files or write a batch download script.")
def fetch(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    hologenome_id: str | None = typer.Option(
        None,
        help="Exact hologenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Host taxon ID; catalog descendants are included."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome_envo_id: str | None = typer.Option(
        None,
        "--biome-envo-id",
        "--biome",
        help="ENVO biome identifier; catalog descendants are included, e.g. ENVO:01000175.",
    ),
    biome_name: str | None = typer.Option(None, "--biome-name", help="Exact biome name."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    data_min: float | None = typer.Option(None, help="Minimum available data in GB."),
    data_max: float | None = typer.Option(None, help="Maximum available data in GB."),
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
        help="Maximum number of matching hologenomes to fetch.",
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
    accept_terms: bool = typer.Option(
        False,
        "--accept-terms",
        help="Skip the data usage terms prompt for this fetch operation.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="Overwrite existing files instead of skipping them.",
    ),
) -> None:
    console = Console()
    filters = {
        "hologenome_id": hologenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome_envo_id": biome_envo_id,
        "biome_name": biome_name,
        "country": country,
        "release": release,
        "data_min": data_min,
        "data_max": data_max,
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
            "hologenomes",
            filters=filters,
            where=where,
            limit=limit,
            fetch=True,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

    if not rows:
        console.print("No matching hologenomes found.")
        return

    jobs: list[DownloadJob] = []
    missing_url_count = 0
    for row in rows:
        hologenome_id = row["hologenome_id"]
        url1 = row["url1"]
        url2 = row["url2"]

        if not url1 or not url2:
            missing_url_count += 1
            if batch is None:
                append_manifest_entry(
                    manifest_path,
                    ManifestEntry(
                        entry_type="hologenome",
                        id_field="hologenome_id",
                        id_value=hologenome_id,
                        url=None,
                        path=None,
                        checksum=None,
                        status="missing_url",
                    ),
                )
            console.print(f"[yellow]Skipping[/yellow] {hologenome_id}: missing paired read URLs.")
            continue

        base_directory = output_dir / "hologenomes" / hologenome_id
        jobs.append(
            DownloadJob(
                entry_type="hologenome",
                id_field="hologenome_id",
                id_value=hologenome_id,
                url=url1,
                destination=destination_for_url(
                    base_directory,
                    url1,
                    fallback_name=f"{hologenome_id}_1.fastq.gz",
                ),
            )
        )
        jobs.append(
            DownloadJob(
                entry_type="hologenome",
                id_field="hologenome_id",
                id_value=hologenome_id,
                url=url2,
                destination=destination_for_url(
                    base_directory,
                    url2,
                    fallback_name=f"{hologenome_id}_2.fastq.gz",
                ),
            )
        )

    console.print(
        f"Matched {len(rows)} hologenomes; queued {len(jobs)} files for download."
    )
    if missing_url_count:
        console.print(f"{missing_url_count} hologenomes were skipped because URLs were missing.")

    ensure_terms_accepted(console, accept_terms=accept_terms)

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


@app.command(help="Summarize the number, host composition, and data volume of matching hologenomes.")
def stats(
    ctx: typer.Context,
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
    hologenome_id: str | None = typer.Option(
        None,
        help="Exact hologenome ID. Comma-separated values allowed.",
    ),
    host_taxid: str | None = typer.Option(None, help="Host taxon ID; catalog descendants are included."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome_envo_id: str | None = typer.Option(
        None,
        "--biome-envo-id",
        "--biome",
        help="ENVO biome identifier; catalog descendants are included, e.g. ENVO:01000175.",
    ),
    biome_name: str | None = typer.Option(None, "--biome-name", help="Exact biome name."),
    country: str | None = typer.Option(None, help="Exact country label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    data_min: float | None = typer.Option(None, help="Minimum available data in GB."),
    data_max: float | None = typer.Option(None, help="Maximum available data in GB."),
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
        "hologenome_id": hologenome_id,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome_envo_id": biome_envo_id,
        "biome_name": biome_name,
        "country": country,
        "release": release,
        "data_min": data_min,
        "data_max": data_max,
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
            target="hologenomes",
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
