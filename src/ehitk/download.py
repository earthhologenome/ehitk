from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
import urllib.request

import requests
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from ehitk.manifest import ManifestEntry, append_manifest_entry

CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class DownloadJob:
    entry_type: str
    id_field: str
    id_value: str
    url: str
    destination: Path


@dataclass(frozen=True)
class DownloadResult:
    job: DownloadJob
    status: str
    checksum: str | None = None
    error: str | None = None


def filename_from_url(url: str, *, fallback: str) -> str:
    filename = Path(urlparse(url).path).name
    return filename or fallback


def destination_for_url(base_directory: Path, url: str, *, fallback_name: str) -> Path:
    return base_directory / filename_from_url(url, fallback=fallback_name)


def download_jobs(
    jobs: list[DownloadJob],
    *,
    manifest_path: str | Path,
    overwrite: bool = False,
    console: Console | None = None,
) -> list[DownloadResult]:
    if not jobs:
        return []

    active_console = console or Console()
    results: list[DownloadResult] = []

    with Progress(
        TextColumn("{task.fields[filename]}", justify="left"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=active_console,
    ) as progress:
        for job in jobs:
            result = _download_job(job, progress=progress, overwrite=overwrite)
            append_manifest_entry(
                manifest_path,
                ManifestEntry(
                    entry_type=job.entry_type,
                    id_field=job.id_field,
                    id_value=job.id_value,
                    url=job.url,
                    path=str(job.destination),
                    checksum=result.checksum,
                    status=result.status,
                ),
            )
            results.append(result)

            if result.error:
                active_console.print(
                    f"[red]Failed[/red] {job.destination.name}: {result.error}"
                )

    return results


def _download_job(
    job: DownloadJob,
    *,
    progress: Progress,
    overwrite: bool,
) -> DownloadResult:
    destination = job.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(f"{destination}.part")

    if destination.exists() and not overwrite:
        return DownloadResult(job=job, status="skipped_existing")

    if temporary_path.exists():
        temporary_path.unlink()

    try:
        scheme = urlparse(job.url).scheme.lower()
        if scheme in {"http", "https"}:
            checksum = _download_http(job, temporary_path, progress)
        elif scheme == "ftp":
            checksum = _download_ftp(job, temporary_path, progress)
        else:
            raise ValueError(f"Unsupported URL scheme: {scheme}")

        temporary_path.replace(destination)
        return DownloadResult(job=job, status="downloaded", checksum=checksum)
    except Exception as exc:  # noqa: BLE001
        if temporary_path.exists():
            temporary_path.unlink()
        return DownloadResult(job=job, status="failed", error=str(exc))


def _download_http(job: DownloadJob, temporary_path: Path, progress: Progress) -> str:
    with requests.get(job.url, stream=True, timeout=(10, 300)) as response:
        response.raise_for_status()
        total_size = _parse_total_size(response.headers.get("content-length"))
        chunks = response.iter_content(chunk_size=CHUNK_SIZE)
        return _stream_to_disk(job, chunks, total_size, temporary_path, progress)


def _download_ftp(job: DownloadJob, temporary_path: Path, progress: Progress) -> str:
    with urllib.request.urlopen(job.url, timeout=300) as response:
        total_size = _parse_total_size(getattr(response, "length", None))
        chunks = iter(lambda: response.read(CHUNK_SIZE), b"")
        return _stream_to_disk(job, chunks, total_size, temporary_path, progress)


def _stream_to_disk(
    job: DownloadJob,
    chunks: Iterable[bytes],
    total_size: int | None,
    temporary_path: Path,
    progress: Progress,
) -> str:
    checksum = hashlib.sha256()
    task_id = progress.add_task("download", filename=job.destination.name, total=total_size)

    try:
        with temporary_path.open("wb") as handle:
            for chunk in chunks:
                if not chunk:
                    continue
                handle.write(chunk)
                checksum.update(chunk)
                progress.update(task_id, advance=len(chunk))
    finally:
        progress.remove_task(task_id)

    return checksum.hexdigest()


def _parse_total_size(raw_value: object) -> int | None:
    if raw_value in (None, "", -1):
        return None
    try:
        size = int(raw_value)
    except (TypeError, ValueError):
        return None
    return size if size >= 0 else None
