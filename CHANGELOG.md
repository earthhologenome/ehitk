# Changelog

All notable changes to EHItk are documented in this file.

The format follows Keep a Changelog principles and the project versions follow Semantic Versioning.

## [Unreleased]

### Added

- No unreleased changes yet.

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
