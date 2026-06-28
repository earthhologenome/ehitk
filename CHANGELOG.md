# Changelog

All notable changes to EHItk are documented in this file.

The format follows Keep a Changelog principles and the project versions follow Semantic Versioning.

## [Unreleased]

### Added

- No unreleased changes yet.

## [1.2.1] - 2026-06-28

### Added

- `ehitk database` now reports the catalog's `data_version` and `schema_version`
  from the embedded `catalog_meta` provenance table, so any install
  self-identifies exactly which data snapshot it ships.
- `ehitk` now validates a catalog's `schema_version` when opening it and raises a
  clear `UnsupportedSchemaVersionError` (exported from the public API) when the
  catalog is newer than the installed code can read, instead of failing later
  with an opaque error.
- Software releases are now archived to Zenodo automatically: each tagged release
  creates a GitHub Release that the Zenodo–GitHub integration deposits under a
  software concept DOI, with metadata (including the author ORCID) supplied by a
  new `.zenodo.json`.

### Changed

- The bundled catalog is now fetched from the published Zenodo record at release
  time rather than copied from a local build, so the snapshot shipped in the
  wheel is always a citable, checksum- and schema-verified record. The published
  database-version list in the README and docs is refreshed automatically.

## [1.2.0] - 2026-06-27

### Fixed

- Fixed shell quoting of the progress messages in the batch download scripts
  written by `hologenomes fetch --batch` and `mags fetch --batch`. The `echo`
  lines interpolated the file name inside literal single quotes without
  escaping, so a name containing a single quote produced a syntactically broken
  script and, in principle, allowed arbitrary shell command injection. The
  message text is now escaped with `shlex.quote`, matching the already-correct
  handling of the `mkdir`, existence-check, and `curl` lines.

### Added

- Documented how the typed dataclass records returned by the Python API
  (`query()`, `values().rows`, and `stats()` breakdown rows) convert directly
  into a pandas `DataFrame` with no glue code, in the Python API guide.
- Added comprehensive docstrings across the public Python API (the `Database`
  entry point, the per-level collections, and the typed record and result
  dataclasses), improving inline `help()` and IDE documentation.
- Added download integrity validation to `hologenomes fetch` and `mags fetch`:
  downloaded files are checked against the server-reported size (detecting
  truncated downloads) and, for gzip-compressed files, validated with a
  streaming gzip integrity check (header, CRC-32, and trailer length). Files
  that fail validation are left with a `.part` suffix and recorded with a
  `corrupt` status instead of being promoted to their final name.
- Added the downloaded file size as a `bytes` field in the download manifest,
  alongside the existing SHA-256 `checksum`, to provide a per-file integrity
  record for reproducing and comparing downloads.
- Embedded the ENVO and NCBI host-taxon descendant maps as `envo_descendants`
  and `host_taxon_descendants` auxiliary tables inside the SQLite catalog, so a
  pinned or custom catalog used via `--db` expands biome and host-taxon filters
  with its own hierarchy instead of the package-bundled metadata. EHItk reads the
  descendants from the catalog in use and falls back to the bundled JSON
  resources for older catalogs that predate the tables. The build script now
  writes these tables alongside the existing JSON resources.

## [1.1.3] - 2026-05-28

### Added

- Added `ehitk database` for reporting the active SQLite catalog path, source,
  size, and SHA256 checksum.
- Documented standalone database catalog releases, including GitHub/Zenodo
  archiving, pinned catalog usage, and the relationship between bundled and
  archived SQLite files.
- Added release-script generation of versioned SQLite database artifacts and
  checksum files for separate catalog release deposits.
- Added `CITATION.cff` and `codemeta.json` software metadata files for
  repository citation, indexing, and archival reuse.
- Added the citable Zenodo DOI for standalone EHItk database catalog releases
  to the README and database documentation.
- Added a Bioconda recipe for EHItk packaging and downstream BioContainers
  integration.
- Documented planned Bioconda installation and BioContainers availability after
  the recipe is accepted upstream.
- Added host NCBI taxids and host/MAG family-genus taxonomy context to the
  default MAG query output.
- Documented identifier namespaces and manual resolution routes for EHI catalog
  IDs, NCBI host taxids, ENVO biome IDs, release labels, and download URLs.

## [1.1.2] - 2026-05-28

### Added

- Added `fields` commands for specimens, hologenomes, and MAGs so users can
  list the names accepted by `values --field`, including aliases.
- Added a Snakemake documentation example showing how to fetch hologenome reads
  with EHItk and quality-filter the paired FASTQ files with fastp.

## [1.1.1] - 2026-05-28

### Added

- Documented the bundled database update policy, legacy database access, and
  how database releases interact with Semantic Versioning.
- Added bundled ENVO and NCBI Taxonomy descendant resources so ENVO biome
  filters and NCBI `host_taxid` filters include catalog descendants.

### Changed

- Split hologenome biome metadata into `biome_envo_id` and `biome_name`
  fields, replacing the previous merged biome label in query output, filters,
  documentation, and the bundled SQLite catalog.
- Added `--biome` as a CLI alias for ENVO biome identifier filtering and
  enabled parent-hologenome biome filters for MAG queries.

## [1.1.0] - 2026-05-28

### Added

- Added Read the Docs documentation with installation, quick-start, command,
  entity-specific, output, fetch, and advanced usage pages.
- Added descriptions for entity subcommands so `ehitk specimens --help`,
  `ehitk hologenomes --help`, and `ehitk mags --help` document their child
  commands.
- Extended the GitHub Actions test matrix and package classifiers through Python 3.14.
- Added CSV/TSV streaming to standard output for `query` and `values` commands.
- Documented the repository's pytest unit tests and GitHub Actions continuous
  integration setup.
- Added a public Python API via `ehitk.Database`, typed record dataclasses,
  structured `values`/`stats` results, and programmatic `fetch` summaries.
- Added Python API documentation with query, values, stats, alternate database,
  and batch fetch examples.

### Changed

- Reduced the README to a concise project overview with a link to the full
  Read the Docs documentation.
- Changed `query` and `values` delimited output options to use `--csv` or
  `--tsv` as format flags, with `--output-file PATH` for file export.
- Split stats calculation from Rich rendering so the CLI and Python API can
  share the same summary logic.

## [1.0.6] - 2026-03-23

### Changed

- Improved the README so it reads as end-user documentation, with clearer command descriptions, examples, and fetch behavior notes.
- Standardized the user-facing data-size column name to `data_gb` in query and values output, while keeping `data` as a compatibility alias.

## [1.0.5] - 2026-03-19

### Changed

- Added `--data-min` and `--data-max` hologenome filters for constraining available dataset size in GB.
- Added the derived MAG `quality` column to default query output and to `--columns all`.
- Added a fetch-time data usage terms prompt for hologenome and MAG downloads, with `--accept-terms` to suppress it after acceptance.
- Standardized the user-facing hologenome and MAG data-size column name to `data_gb`.

## [1.0.4] - 2026-03-18

### Changed

- Updated the README to document installation from PyPI with `pip install ehitk`.
- Switched the README logo image to an absolute GitHub URL so it renders correctly outside the repository context.
- Removed maintainer-only release instructions from the public README.

## [1.0.3] - 2026-03-18

### Fixed

- Installed test dependencies in the GitHub release workflow so tag-based releases can run `pytest` before building and publishing.
- Updated the local release preparation guidance to use both development and release extras.
- Improved the release script error message so missing `pytest` points to the correct dependency install command.

## [1.0.2] - 2026-03-18

### Fixed

- Added the missing GitHub release workflow to the repository so tag-based PyPI publishing can run.
- Added the release tooling files required for automated publication.

### Changed

- Prepared the project for the next PyPI release after the incomplete 1.0.1 tag.

## [1.0.1] - 2026-03-18

### Added

- Automated release preparation with `scripts/release.py`.
- Tag-triggered GitHub Actions release workflow for building, validating, and publishing Python distributions to PyPI through Trusted Publishing.
- Dedicated `release` optional dependency group with the tooling needed for `build` and `twine check`.

### Changed

- Updated package metadata and documentation to support PyPI publication and repeatable versioned releases.
- Pointed project changelog metadata to `CHANGELOG.md` and formalized the versioned release history.

### Fixed

- Added release-time checks to ensure the packaged SQLite catalog stays synchronized with the source database before publishing.

## [1.0.0] - 2026-03-18

### Added

- Entity-oriented CLI namespaces for `specimens`, `hologenomes`, and `mags`.
- Consistent `query`, `values`, and `stats` commands across all metadata entities.
- `fetch` support for paired hologenome reads and MAG FASTA downloads.
- Batch download script generation with `fetch --batch PATH`.
- CSV and TSV export support for query and values outputs.
- Configurable query column presets via `src/ehitk/data/custom_columns.json`.
- Safe advanced SQL filtering through `--where` with banned keyword and comment checks.
- Friendly metadata filters for host taxonomy, geography, specimen measurements, MAG taxonomy, and derived MAG quality.
- Comma-separated multi-value filtering for exact-match filters and MAG quality classes.
- Distinct-value summaries through the `values` subcommand.
- Summary statistics for specimens, hologenomes, and MAGs, including hologenome data volume summaries in GB.
- Append-only `manifest.jsonl` logging for fetch outcomes.
- Rich download progress display and atomic partial-file handling.
- Bundled SQLite catalog and packaged metadata assets.
- GitHub Actions CI for testing, building, and CLI smoke checks.
- Project architecture diagram source under `docs/`.
