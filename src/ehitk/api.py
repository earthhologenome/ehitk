from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ehitk.download import (
    DownloadJob,
    DownloadResult,
    destination_for_url,
    download_jobs,
    write_batch_script,
)
from ehitk.manifest import ManifestEntry, append_manifest_entry
from ehitk.query import DEFAULT_QUERY_LIMIT, query_rows, resolve_catalog_path
from ehitk.stats import StatBreakdown, TargetStats, target_stats
from ehitk.values import DEFAULT_VALUES_LIMIT, value_rows


@dataclass(frozen=True, slots=True)
class Specimen:
    specimen_id: str | None = None
    host_taxid: str | int | None = None
    host_species: str | None = None
    host_genus: str | None = None
    host_family: str | None = None
    host_order: str | None = None
    host_class: str | None = None
    weight: tuple[float | str, ...] | None = None
    length: tuple[float | str, ...] | None = None
    sex: str | None = None


@dataclass(frozen=True, slots=True)
class Hologenome:
    hologenome_id: str | None = None
    release: str | None = None
    sample_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    date: str | None = None
    url1: str | None = None
    url2: str | None = None
    biome: str | None = None
    data_gb: float | None = None
    specimen_id: str | None = None
    host_taxid: str | int | None = None
    host_species: str | None = None
    host_genus: str | None = None
    host_family: str | None = None
    host_order: str | None = None
    host_class: str | None = None
    weight: tuple[float | str, ...] | None = None
    length: tuple[float | str, ...] | None = None
    sex: str | None = None


@dataclass(frozen=True, slots=True)
class Mag:
    mag_id: str | None = None
    release: str | None = None
    quality: str | None = None
    completeness: float | None = None
    contamination: float | None = None
    size: int | float | None = None
    gc: float | None = None
    n50: int | None = None
    contigs: int | None = None
    mag_domain: str | None = None
    mag_phylum: str | None = None
    mag_class: str | None = None
    mag_order: str | None = None
    mag_family: str | None = None
    mag_genus: str | None = None
    url: str | None = None
    mag_species: str | None = None
    hologenome_id: str | None = None
    hologenome_release: str | None = None
    sample_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    date: str | None = None
    url1: str | None = None
    url2: str | None = None
    biome: str | None = None
    data_gb: float | None = None
    specimen_id: str | None = None
    host_taxid: str | int | None = None
    host_species: str | None = None
    host_genus: str | None = None
    host_family: str | None = None
    host_order: str | None = None
    host_class: str | None = None
    weight: tuple[float | str, ...] | None = None
    length: tuple[float | str, ...] | None = None
    sex: str | None = None


@dataclass(frozen=True, slots=True)
class ValueCount:
    value: str
    count: int


@dataclass(frozen=True, slots=True)
class ValuesResult:
    field: str
    rows: tuple[ValueCount, ...]


@dataclass(frozen=True, slots=True)
class FetchSummary:
    target: str
    matched_count: int
    queued_count: int
    missing_url_count: int
    jobs: tuple[DownloadJob, ...]
    results: tuple[DownloadResult, ...] = ()
    batch_script: Path | None = None
    manifest_path: Path | None = None


class Database:
    """Public Python interface to the EHItk SQLite catalog."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = resolve_catalog_path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Database does not exist: {self.path}")
        self.specimens = SpecimenCollection(self)
        self.hologenomes = HologenomeCollection(self)
        self.mags = MagCollection(self)
        self._closed = False

    def __enter__(self) -> Database:
        self._ensure_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("EHItk database is closed.")


class _Collection:
    target: str
    record_type: type

    def __init__(self, database: Database) -> None:
        self._database = database

    def query(
        self,
        *,
        where: str | None = None,
        limit: int | None = DEFAULT_QUERY_LIMIT,
        columns: str | Sequence[str] | None = None,
        **filters: Any,
    ) -> list[Any]:
        self._database._ensure_open()
        column_spec = _column_spec(columns)
        rows = query_rows(
            self._database.path,
            self.target,
            filters=_normalize_filters(filters),
            where=where,
            limit=limit,
            fetch=False,
            columns=column_spec,
        )
        return [_record_from_row(self.record_type, row) for row in rows]

    def values(
        self,
        field: str,
        *,
        where: str | None = None,
        limit: int = DEFAULT_VALUES_LIMIT,
        **filters: Any,
    ) -> ValuesResult:
        self._database._ensure_open()
        resolved_field, rows = value_rows(
            str(self._database.path),
            target=self.target,
            field=field,
            filters=_normalize_filters(filters),
            where=where,
            limit=limit,
        )
        return ValuesResult(
            field=resolved_field,
            rows=tuple(ValueCount(value=row["value"], count=row["count"]) for row in rows),
        )

    def stats(self, *, where: str | None = None, **filters: Any) -> TargetStats:
        self._database._ensure_open()
        return target_stats(
            catalog_path=str(self._database.path),
            target=self.target,
            filters=_normalize_filters(filters),
            where=where,
        )


class SpecimenCollection(_Collection):
    target = "specimens"
    record_type = Specimen

    def query(
        self,
        *,
        specimen_id: str | Sequence[str] | None = None,
        host_taxid: str | int | Sequence[str | int] | None = None,
        host_species: str | Sequence[str] | None = None,
        host_lineage: str | Sequence[str] | None = None,
        sex: str | Sequence[str] | None = None,
        weight_min: float | None = None,
        weight_max: float | None = None,
        length_min: float | None = None,
        length_max: float | None = None,
        where: str | None = None,
        limit: int | None = DEFAULT_QUERY_LIMIT,
        columns: str | Sequence[str] | None = None,
    ) -> list[Specimen]:
        return super().query(
            specimen_id=specimen_id,
            host_taxid=host_taxid,
            host_species=host_species,
            host_lineage=host_lineage,
            sex=sex,
            weight_min=weight_min,
            weight_max=weight_max,
            length_min=length_min,
            length_max=length_max,
            where=where,
            limit=limit,
            columns=columns,
        )


class HologenomeCollection(_Collection):
    target = "hologenomes"
    record_type = Hologenome

    def fetch(
        self,
        *,
        output_dir: str | Path = Path("downloads"),
        batch: str | Path | None = None,
        manifest_path: str | Path = Path("manifest.jsonl"),
        overwrite: bool = False,
        where: str | None = None,
        limit: int | None = None,
        **filters: Any,
    ) -> FetchSummary:
        self._database._ensure_open()
        rows = query_rows(
            self._database.path,
            "hologenomes",
            filters=_normalize_filters(filters),
            where=where,
            limit=limit,
            fetch=True,
        )
        jobs: list[DownloadJob] = []
        missing_url_count = 0
        manifest = Path(manifest_path)

        for row in rows:
            hologenome_id = row["hologenome_id"]
            url1 = row["url1"]
            url2 = row["url2"]
            if not url1 or not url2:
                missing_url_count += 1
                if batch is None:
                    append_manifest_entry(
                        manifest,
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
                continue

            base_directory = Path(output_dir) / "hologenomes" / hologenome_id
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

        return _finish_fetch(
            target="hologenomes",
            matched_count=len(rows),
            missing_url_count=missing_url_count,
            jobs=jobs,
            batch=batch,
            manifest_path=manifest,
            overwrite=overwrite,
        )


class MagCollection(_Collection):
    target = "mags"
    record_type = Mag

    def fetch(
        self,
        *,
        output_dir: str | Path = Path("downloads"),
        batch: str | Path | None = None,
        manifest_path: str | Path = Path("manifest.jsonl"),
        overwrite: bool = False,
        where: str | None = None,
        limit: int | None = None,
        **filters: Any,
    ) -> FetchSummary:
        self._database._ensure_open()
        rows = query_rows(
            self._database.path,
            "mags",
            filters=_normalize_filters(filters),
            where=where,
            limit=limit,
            fetch=True,
        )
        jobs: list[DownloadJob] = []
        missing_url_count = 0
        manifest = Path(manifest_path)

        for row in rows:
            mag_id = row["mag_id"]
            url = row["url"]
            if not url:
                missing_url_count += 1
                if batch is None:
                    append_manifest_entry(
                        manifest,
                        ManifestEntry(
                            entry_type="mag",
                            id_field="mag_id",
                            id_value=mag_id,
                            url=None,
                            path=None,
                            checksum=None,
                            status="missing_url",
                        ),
                    )
                continue

            base_directory = Path(output_dir) / "mags" / mag_id
            jobs.append(
                DownloadJob(
                    entry_type="mag",
                    id_field="mag_id",
                    id_value=mag_id,
                    url=url,
                    destination=destination_for_url(
                        base_directory,
                        url,
                        fallback_name=f"{mag_id}.fa.gz",
                    ),
                )
            )

        return _finish_fetch(
            target="mags",
            matched_count=len(rows),
            missing_url_count=missing_url_count,
            jobs=jobs,
            batch=batch,
            manifest_path=manifest,
            overwrite=overwrite,
        )


def _finish_fetch(
    *,
    target: str,
    matched_count: int,
    missing_url_count: int,
    jobs: list[DownloadJob],
    batch: str | Path | None,
    manifest_path: Path,
    overwrite: bool,
) -> FetchSummary:
    if batch is not None:
        script_path = write_batch_script(batch, jobs, overwrite=overwrite)
        return FetchSummary(
            target=target,
            matched_count=matched_count,
            queued_count=len(jobs),
            missing_url_count=missing_url_count,
            jobs=tuple(jobs),
            batch_script=script_path,
            manifest_path=None,
        )

    results = download_jobs(jobs, manifest_path=manifest_path, overwrite=overwrite)
    return FetchSummary(
        target=target,
        matched_count=matched_count,
        queued_count=len(jobs),
        missing_url_count=missing_url_count,
        jobs=tuple(jobs),
        results=tuple(results),
        manifest_path=manifest_path,
    )


def _column_spec(columns: str | Sequence[str] | None) -> str | None:
    if columns is None or isinstance(columns, str):
        return columns
    return ",".join(columns)


def _normalize_filters(filters: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if value is None:
            normalized[key] = None
        elif isinstance(value, str) or key.endswith(("_min", "_max")):
            normalized[key] = value
        elif isinstance(value, Sequence):
            normalized[key] = ",".join(str(item) for item in value)
        else:
            normalized[key] = str(value)
    return normalized


def _record_from_row(record_type: type, row: Any) -> Any:
    keys = set(row.keys())
    payload: dict[str, Any] = {}
    for name in record_type.__dataclass_fields__:
        value = row[name] if name in keys else None
        if name in {"weight", "length"}:
            value = _parse_json_tuple(value)
        payload[name] = value
    return record_type(**payload)


def _parse_json_tuple(value: Any) -> tuple[float | str, ...] | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return (value,)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return (value,)
    if not isinstance(parsed, list):
        parsed = [parsed]

    values: list[float | str] = []
    for item in parsed:
        try:
            values.append(float(item))
        except (TypeError, ValueError):
            values.append(str(item))
    return tuple(values)
