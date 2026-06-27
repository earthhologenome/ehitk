"""Public Python API for the Earth Hologenome Initiative Toolkit.

This module defines the objects exposed at the top level of the ``ehitk``
package: the :class:`Database` entry point, the per-level collection objects it
exposes (specimens, hologenomes, MAGs), and the typed record and result
dataclasses returned by their methods.

Example:
    >>> import ehitk
    >>> with ehitk.Database() as db:
    ...     mags = db.mags.query(quality="high", limit=5)
    >>> mags[0].mag_id  # doctest: +SKIP
    'EHI00001_bin.1'

See the Sphinx documentation (``docs/api.rst``) for an extended guide.
"""

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
    """A specimen record: a sampled host animal and its associated metadata.

    Returned by :meth:`SpecimenCollection.query`. Every field is optional
    because queries may request a subset of columns. The ``weight`` and
    ``length`` measurements are normalised to tuples of numeric (or, when not
    parseable, string) values.

    Attributes:
        specimen_id: EHI specimen identifier.
        host_taxid: NCBI taxonomy identifier of the host species.
        host_species: Host species name.
        host_genus: Host genus name.
        host_family: Host family name.
        host_order: Host order name.
        host_class: Host class name.
        weight: Recorded host body weight(s).
        length: Recorded host body length(s).
        sex: Recorded host sex.
    """

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
    """A hologenome record: a shotgun sequencing dataset for a specimen.

    Returned by :meth:`HologenomeCollection.query`. Fields combine
    hologenome-level metadata (sample, location, sequencing data) with the
    metadata of the parent specimen, so the same host fields as
    :class:`Specimen` are available here. Every field is optional because
    queries may request a subset of columns.

    Attributes:
        hologenome_id: EHI hologenome identifier.
        release: EHI data release the hologenome belongs to.
        sample_type: Type of biological sample sequenced.
        latitude: Sampling latitude in decimal degrees.
        longitude: Sampling longitude in decimal degrees.
        country: Country of sampling.
        date: Sampling date.
        url1: Download URL for the first (forward) read file.
        url2: Download URL for the second (reverse) read file.
        biome_envo_id: ENVO identifier of the sampling biome.
        biome_name: Human-readable biome name.
        data_gb: Sequencing data volume in gigabytes.
        specimen_id: Identifier of the parent specimen.
        host_taxid: NCBI taxonomy identifier of the host species.
        host_species: Host species name.
        host_genus: Host genus name.
        host_family: Host family name.
        host_order: Host order name.
        host_class: Host class name.
        weight: Recorded host body weight(s).
        length: Recorded host body length(s).
        sex: Recorded host sex.
    """

    hologenome_id: str | None = None
    release: str | None = None
    sample_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    country: str | None = None
    date: str | None = None
    url1: str | None = None
    url2: str | None = None
    biome_envo_id: str | None = None
    biome_name: str | None = None
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
    """A metagenome-assembled genome (MAG) record.

    Returned by :meth:`MagCollection.query`. Fields combine MAG-level metrics
    and taxonomy with the metadata of the parent hologenome and specimen, so
    the relevant hologenome and host fields are also available here. Every
    field is optional because queries may request a subset of columns.

    Attributes:
        mag_id: EHI MAG identifier.
        release: EHI data release the MAG belongs to.
        quality: Quality tier (``"high"``, ``"medium"``, or ``"low"``) derived
            from completeness and contamination.
        completeness: Estimated genome completeness (percent).
        contamination: Estimated genome contamination (percent).
        size: Genome size in base pairs.
        gc: GC content (percent).
        n50: Contig N50.
        contigs: Number of contigs.
        mag_domain: GTDB domain assignment.
        mag_phylum: GTDB phylum assignment.
        mag_class: GTDB class assignment.
        mag_order: GTDB order assignment.
        mag_family: GTDB family assignment.
        mag_genus: GTDB genus assignment.
        mag_species: GTDB species assignment.
        url: Download URL for the MAG FASTA file.
        hologenome_id: Identifier of the parent hologenome.
        hologenome_release: Release of the parent hologenome.
        sample_type: Type of biological sample sequenced.
        latitude: Sampling latitude in decimal degrees.
        longitude: Sampling longitude in decimal degrees.
        country: Country of sampling.
        date: Sampling date.
        url1: Download URL for the parent hologenome forward reads.
        url2: Download URL for the parent hologenome reverse reads.
        biome_envo_id: ENVO identifier of the sampling biome.
        biome_name: Human-readable biome name.
        data_gb: Sequencing data volume of the parent hologenome in gigabytes.
        specimen_id: Identifier of the parent specimen.
        host_taxid: NCBI taxonomy identifier of the host species.
        host_species: Host species name.
        host_genus: Host genus name.
        host_family: Host family name.
        host_order: Host order name.
        host_class: Host class name.
        weight: Recorded host body weight(s).
        length: Recorded host body length(s).
        sex: Recorded host sex.
    """

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
    biome_envo_id: str | None = None
    biome_name: str | None = None
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
    """A single distinct value and the number of records that carry it.

    Attributes:
        value: The distinct field value.
        count: Number of matching records with that value.
    """

    value: str
    count: int


@dataclass(frozen=True, slots=True)
class ValuesResult:
    """Result of a ``values()`` call: distinct values for a field with counts.

    Returned by the ``values()`` method of every collection.

    Attributes:
        field: The resolved field name the values were counted for.
        rows: Distinct values with their counts, ordered by descending count.
    """

    field: str
    rows: tuple[ValueCount, ...]


@dataclass(frozen=True, slots=True)
class FetchSummary:
    """Outcome of a ``fetch()`` call on the hologenome or MAG collection.

    Returned by :meth:`HologenomeCollection.fetch` and
    :meth:`MagCollection.fetch`. When ``batch`` was requested no download is
    performed and ``batch_script`` points at the generated shell script;
    otherwise ``results`` holds the per-file download outcomes and
    ``manifest_path`` points at the appended manifest.

    Attributes:
        target: The collection that was fetched (``"hologenomes"`` or
            ``"mags"``).
        matched_count: Number of records matched by the filters.
        queued_count: Number of download jobs created from those records.
        missing_url_count: Number of matched records lacking a download URL.
        jobs: The download jobs that were generated.
        results: Per-file download outcomes (empty in batch-script mode).
        batch_script: Path to the generated batch script, or ``None`` when
            files were downloaded directly.
        manifest_path: Path to the manifest file, or ``None`` in
            batch-script mode.
    """

    target: str
    matched_count: int
    queued_count: int
    missing_url_count: int
    jobs: tuple[DownloadJob, ...]
    results: tuple[DownloadResult, ...] = ()
    batch_script: Path | None = None
    manifest_path: Path | None = None


class Database:
    """Public Python interface to the EHItk SQLite catalog.

    A ``Database`` is the entry point of the Python API. It opens the bundled
    catalog by default, or a custom catalog when a ``path`` is given, and
    exposes one collection per EHI data level:

    * :attr:`specimens` — host and specimen metadata
      (:class:`SpecimenCollection`)
    * :attr:`hologenomes` — shotgun sequencing datasets
      (:class:`HologenomeCollection`)
    * :attr:`mags` — metagenome-assembled genomes (:class:`MagCollection`)

    Each collection supports ``query()``, ``values()``, and ``stats()``; the
    hologenome and MAG collections also support ``fetch()``. Filters use the
    same names as the CLI options, with underscores instead of hyphens.

    Use it as a context manager so the catalog handle is released on exit:

    Example:
        >>> import ehitk
        >>> with ehitk.Database() as db:
        ...     mags = db.mags.query(quality="high", host_taxid=40674, limit=5)
        ...     countries = db.hologenomes.values("country")
        >>> mags[0].quality  # doctest: +SKIP
        'high'

    Args:
        path: Path to a SQLite catalog. When ``None`` (the default) the catalog
            bundled with the installed package is used.

    Raises:
        FileNotFoundError: If the resolved catalog path does not exist.
    """

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
        """Mark the database as closed so further queries raise an error."""
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("EHItk database is closed.")


class _Collection:
    """Base class for the per-level collections exposed by :class:`Database`.

    Subclasses bind a ``target`` table and a ``record_type`` dataclass and add
    level-specific keyword arguments. Instances are created by ``Database`` and
    accessed through its :attr:`~Database.specimens`,
    :attr:`~Database.hologenomes`, and :attr:`~Database.mags` attributes rather
    than directly.
    """

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
        """Query records from this collection's table.

        Args:
            where: Optional validated SQL predicate fragment, as accepted by
                the CLI ``--where`` option.
            limit: Maximum number of records to return; ``None`` for no limit.
            columns: Restrict the returned columns. Accepts a comma-separated
                string or a sequence of column names.
            **filters: Field filters using CLI option names with underscores.
                Values may be strings, numbers, or sequences (treated like
                comma-separated CLI values).

        Returns:
            A list of typed records (:class:`Specimen`, :class:`Hologenome`, or
            :class:`Mag` depending on the collection).
        """
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
        """Count distinct values of a field after applying filters.

        Args:
            field: Name of the field whose distinct values to count.
            where: Optional validated SQL predicate fragment.
            limit: Maximum number of distinct values to return.
            **filters: Field filters, as for :meth:`query`.

        Returns:
            A :class:`ValuesResult` holding the resolved field name and the
            distinct values with their counts, ordered by descending count.
        """
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
        """Compute summary statistics and breakdowns for matching records.

        Args:
            where: Optional validated SQL predicate fragment.
            **filters: Field filters, as for :meth:`query`.

        Returns:
            A :class:`~ehitk.stats.TargetStats` object with a raw ``summary``
            dictionary and named breakdown tables.
        """
        self._database._ensure_open()
        return target_stats(
            catalog_path=str(self._database.path),
            target=self.target,
            filters=_normalize_filters(filters),
            where=where,
        )


class SpecimenCollection(_Collection):
    """Collection of specimen records, accessed via ``Database.specimens``.

    Adds explicit keyword arguments for the specimen-level filters on top of
    the shared :meth:`_Collection.query` behaviour.
    """

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
        """Query specimen records.

        All arguments are optional filters; see :meth:`_Collection.query` for
        the shared ``where``, ``limit``, and ``columns`` semantics. ``*_min``
        and ``*_max`` arguments bound the corresponding measurement, and
        ``host_lineage`` matches any host taxonomic rank.

        Returns:
            A list of :class:`Specimen` records.
        """
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
    """Collection of hologenome records, accessed via ``Database.hologenomes``.

    Supports the shared ``query()``, ``values()``, and ``stats()`` methods and
    adds :meth:`fetch` for downloading the paired sequencing read files.
    """

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
        """Download (or script the download of) matching hologenome read files.

        Each matched hologenome contributes its forward (``url1``) and reverse
        (``url2``) read files. Records missing either URL are skipped and
        recorded in the manifest.

        Args:
            output_dir: Directory under which files are written, organised as
                ``<output_dir>/hologenomes/<hologenome_id>/``.
            batch: When given, write a shell script of download commands to
                this path instead of downloading immediately.
            manifest_path: Path of the JSONL manifest appended during direct
                downloads.
            overwrite: Overwrite existing files (or batch script) if present.
            where: Optional validated SQL predicate fragment.
            limit: Maximum number of hologenomes to fetch; ``None`` for no
                limit.
            **filters: Field filters, as for :meth:`query`.

        Returns:
            A :class:`FetchSummary` describing what was matched, queued, and
            downloaded or scripted.
        """
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
    """Collection of MAG records, accessed via ``Database.mags``.

    Supports the shared ``query()``, ``values()``, and ``stats()`` methods and
    adds :meth:`fetch` for downloading the MAG FASTA files.
    """

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
        """Download (or script the download of) matching MAG FASTA files.

        Each matched MAG contributes its ``url`` FASTA file. Records missing a
        URL are skipped and recorded in the manifest.

        Args:
            output_dir: Directory under which files are written, organised as
                ``<output_dir>/mags/<mag_id>/``.
            batch: When given, write a shell script of download commands to
                this path instead of downloading immediately.
            manifest_path: Path of the JSONL manifest appended during direct
                downloads.
            overwrite: Overwrite existing files (or batch script) if present.
            where: Optional validated SQL predicate fragment.
            limit: Maximum number of MAGs to fetch; ``None`` for no limit.
            **filters: Field filters, as for :meth:`query`.

        Returns:
            A :class:`FetchSummary` describing what was matched, queued, and
            downloaded or scripted.
        """
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
