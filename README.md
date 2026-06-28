<p align="center">
  <img src="https://raw.githubusercontent.com/earthhologenome/ehitk/main/docs/ehitk_logo.png" alt="EHItk logo" width="500">
</p>

[![CI](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml/badge.svg)](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/earthhologenome/ehitk)
[![Database DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20430293.svg)](https://doi.org/10.5281/zenodo.20430293)

# EHItk

The Earth Hologenome Initiative ToolKit (EHItk) is a Python package and
command-line tool for
finding, summarizing, exporting, and downloading EHI specimens, hologenomes, and
metagenome-assembled genomes.

## Installation

```bash
pip install ehitk
```

## Example

```bash
ehitk specimens query --host-species "Podarcis muralis" --limit 5
ehitk hologenomes query --biome ENVO:01000175 --limit 5
ehitk hologenomes fields
ehitk hologenomes values --field country --limit 10
ehitk mags stats --quality high --species "Escherichia coli"
ehitk mags query --quality high --csv | head
ehitk specimens values --field sex --csv --output-file specimen-sex-values.csv
```

Python API:

```python
import ehitk

with ehitk.Database() as ehidb:
    mags = ehidb.mags.query(quality="high", host_taxid=40674, limit=5)

for mag in mags:
    print(
        mag.mag_id,
        mag.quality,
        mag.host_taxid,
        mag.host_species,
        mag.mag_family,
        mag.mag_genus,
    )
```

## Documentation

Full installation instructions, command reference, examples, output formats,
identifier namespaces, download guidance, and Python API examples are available
at:

https://ehitk.readthedocs.io/

Use the built-in help for local command details:

```bash
ehitk --help
ehitk specimens --help
ehitk hologenomes fetch --help
ehitk mags query --help
```

## Bundled database and versioning

EHItk ships with a bundled SQLite EHI database, which is the default database
used by the command-line interface and Python API. Updating the Python package
may therefore also update the default EHI database.

Use `ehitk database` to inspect the catalog currently in use, including its
path, source, size, SHA256 checksum, and its `data_version` / `schema_version`
(`unknown` for older catalogs built before this metadata existed). EHItk
validates `schema_version` when it opens a catalog and reports a clear error if
the catalog is too new or too old for the installed package.

Database updates are paired with documented EHI data releases. Each release
produces a standalone `ehitk-database-<data_version>.sqlite` artifact and
checksum file for GitHub Releases and Zenodo, while the same SQLite file remains
bundled inside the matching Python package for convenience. The citable Zenodo
database record is available at https://doi.org/10.5281/zenodo.20430293. Older
database files can be used to rerun analyses against the same database version by
passing the file with `--db` or by opening it with
`ehitk.Database("/path/to/ehitk.sqlite")`.

Published database versions (generated from Zenodo by
`scripts/update_db_list.py`):

<!-- db-list-start -->

_No published database versions found._

<!-- db-list-end -->


The public package does not rebuild the curated EHI metadata catalog from
upstream sources; that is done by the separate
[`ehitk-build`](https://github.com/earthhologenome/ehitk-build) generator, which
publishes each catalog to Zenodo. Fresh catalogs are obtained by upgrading EHItk
or by downloading a versioned database artifact.

EHItk package versions follow Semantic Versioning for the software interface.
Database updates that break the SQLite schema contract bump the catalog's
`schema_version` and require a coordinated (major) EHItk release; non-breaking
database additions or metadata corrections bump the `data_version` only and are
released as minor or patch versions. All are documented in the changelog and
associated data release notes.

## Testing and continuous integration

EHItk includes a pytest-based unit test suite in the `tests/` directory. The
repository also uses GitHub Actions continuous integration to run the test suite,
build source and wheel distributions, and perform CLI smoke tests across Python
3.10, 3.11, 3.12, 3.13, and 3.14.
