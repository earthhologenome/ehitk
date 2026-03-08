from __future__ import annotations

from collections import Counter
from pathlib import Path

from rich.console import Console
import typer

from ehitk.download import DownloadJob, destination_for_url, download_jobs
from ehitk.manifest import ManifestEntry, append_manifest_entry
from ehitk.output import render_or_export_rows
from ehitk.query import (
    DEFAULT_QUERY_LIMIT,
    QueryValidationError,
    catalog_path_from_context,
    headers_for,
    query_rows,
)
from ehitk.stats import render_target_stats

app = typer.Typer(help="Query, summarize, and fetch metagenomes.", no_args_is_help=True)


@app.command()
def query(
    ctx: typer.Context,
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
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
    if csv is not None and tsv is not None:
        raise typer.BadParameter("Use only one of --csv or --tsv.")

    filters = {
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "release": release,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx),
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
def fetch(
    ctx: typer.Context,
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
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
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "release": release,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx),
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
            append_manifest_entry(
                manifest_path,
                ManifestEntry(
                    entry_type="metagenome",
                    genome_id=metagenome_id,
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
                genome_id=metagenome_id,
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
                genome_id=metagenome_id,
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
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    sample_type: str | None = typer.Option(None, help="Exact sample type."),
    biome: str | None = typer.Option(None, help="Exact biome label."),
    release: str | None = typer.Option(None, help="Exact release ID."),
    where: str | None = typer.Option(
        None,
        help="Advanced SQL predicate appended to the WHERE clause after validation.",
    ),
) -> None:
    console = Console()
    filters = {
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "sample_type": sample_type,
        "biome": biome,
        "release": release,
    }

    try:
        render_target_stats(
            console,
            catalog_path=str(catalog_path_from_context(ctx)),
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
