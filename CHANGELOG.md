# Changelog

All notable changes to EHItk are documented in this file.

The format follows Keep a Changelog principles and the project versions follow Semantic Versioning.

## [Unreleased]

### Added

- No unreleased changes yet.

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
