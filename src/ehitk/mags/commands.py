from __future__ import annotations

from collections import Counter
from enum import Enum
from pathlib import Path

from rich.console import Console
from rich.table import Table
import typer

from ehitk.download import DownloadJob, destination_for_url, download_jobs
from ehitk.manifest import ManifestEntry, append_manifest_entry
from ehitk.query import (
    DEFAULT_QUERY_LIMIT,
    QueryValidationError,
    catalog_path_from_context,
    headers_for,
    query_rows,
)

app = typer.Typer(help="Query and fetch metagenome-assembled genomes.", no_args_is_help=True)


class MagQuality(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


@app.command()
def query(
    ctx: typer.Context,
    quality: MagQuality | None = typer.Option(None, help="Derived MAG quality class."),
    genus: str | None = typer.Option(None, help="Exact MAG genus."),
    species: str | None = typer.Option(None, help="Exact MAG species."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    release: str | None = typer.Option(None, help="Exact MAG release ID."),
    metagenome_id: str | None = typer.Option(None, help="Exact parent metagenome ID."),
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
        "quality": quality.value if quality else None,
        "genus": genus,
        "species": species,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "release": release,
        "metagenome_id": metagenome_id,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx),
            "mags",
            filters=filters,
            where=where,
            limit=limit,
            fetch=False,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

    _render_rows(console, headers_for("mags"), rows, title="MAGs")


@app.command()
def fetch(
    ctx: typer.Context,
    quality: MagQuality | None = typer.Option(None, help="Derived MAG quality class."),
    genus: str | None = typer.Option(None, help="Exact MAG genus."),
    species: str | None = typer.Option(None, help="Exact MAG species."),
    host_taxid: str | None = typer.Option(None, help="Exact host taxon ID."),
    host_species: str | None = typer.Option(None, help="Exact host species name."),
    host_lineage: str | None = typer.Option(
        None,
        help="Exact lineage term matched against host species/genus/family/order/class.",
    ),
    release: str | None = typer.Option(None, help="Exact MAG release ID."),
    metagenome_id: str | None = typer.Option(None, help="Exact parent metagenome ID."),
    where: str | None = typer.Option(
        None,
        help="Advanced SQL predicate appended to the WHERE clause after validation.",
    ),
    limit: int | None = typer.Option(
        None,
        min=1,
        help="Maximum number of matching MAGs to fetch.",
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
        "quality": quality.value if quality else None,
        "genus": genus,
        "species": species,
        "host_taxid": host_taxid,
        "host_species": host_species,
        "host_lineage": host_lineage,
        "release": release,
        "metagenome_id": metagenome_id,
    }

    try:
        rows = query_rows(
            catalog_path_from_context(ctx),
            "mags",
            filters=filters,
            where=where,
            limit=limit,
            fetch=True,
        )
    except QueryValidationError as exc:
        raise typer.BadParameter(str(exc), param_hint="--where") from exc

    if not rows:
        console.print("No matching MAGs found.")
        return

    jobs: list[DownloadJob] = []
    missing_url_count = 0
    for row in rows:
        mag_id = row["mag_id"]
        url = row["url"]
        if not url:
            missing_url_count += 1
            append_manifest_entry(
                manifest_path,
                ManifestEntry(
                    entry_type="mag",
                    genome_id=mag_id,
                    url=None,
                    path=None,
                    checksum=None,
                    status="missing_url",
                ),
            )
            console.print(f"[yellow]Skipping[/yellow] {mag_id}: missing MAG URL.")
            continue

        base_directory = output_dir / "mags" / mag_id
        jobs.append(
            DownloadJob(
                entry_type="mag",
                genome_id=mag_id,
                url=url,
                destination=destination_for_url(
                    base_directory,
                    url,
                    fallback_name=f"{mag_id}.fa.gz",
                ),
            )
        )

    console.print(f"Matched {len(rows)} MAGs; queued {len(jobs)} files for download.")
    if missing_url_count:
        console.print(f"{missing_url_count} MAGs were skipped because URLs were missing.")

    results = download_jobs(
        jobs,
        manifest_path=manifest_path,
        overwrite=overwrite,
        console=console,
    )
    _print_fetch_summary(console, results)


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


def _print_fetch_summary(console: Console, results: list) -> None:
    if not results:
        console.print("No files were queued for download.")
        return

    counts = Counter(result.status for result in results)
    summary = ", ".join(f"{status}={count}" for status, count in sorted(counts.items()))
    console.print(f"Download summary: {summary}")
