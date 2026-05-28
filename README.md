<p align="center">
  <img src="https://raw.githubusercontent.com/earthhologenome/ehitk/main/docs/ehitk_logo.png" alt="EHItk logo" width="500">
</p>

[![CI](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml/badge.svg)](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/earthhologenome/ehitk)

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
    print(mag.mag_id, mag.quality, mag.host_species)
```

## Documentation

Full installation instructions, command reference, examples, output formats, and
download guidance, and Python API examples are available at:

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

Database updates are paired with documented EHI data releases. Older legacy
database files are archived with those data releases so analyses can be rerun
against the same database version by passing the file with `--db` or by opening
it with `ehitk.Database("/path/to/ehitk.sqlite")`.

EHItk package versions follow Semantic Versioning for the software interface.
Database updates that change the SQLite schema, remove or rename fields, or
otherwise alter command-line or Python API output compatibility are treated as
breaking changes and require a major version bump. Non-breaking database
additions or metadata corrections are released as minor or patch versions and
are documented in the changelog and associated data release notes.

## Testing and continuous integration

EHItk includes a pytest-based unit test suite in the `tests/` directory. The
repository also uses GitHub Actions continuous integration to run the test suite,
build source and wheel distributions, and perform CLI smoke tests across Python
3.10, 3.11, 3.12, 3.13, and 3.14.
