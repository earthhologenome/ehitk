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
ehitk hologenomes values --field country --limit 10
ehitk mags stats --quality high --species "Escherichia coli"
ehitk mags query --quality high --csv | head
ehitk specimens values --field sex --csv --output-file specimen-sex-values.csv
```

Python API:

```python
import ehitk

with ehitk.Database() as ehidb:
    mags = ehidb.mags.query(quality="high", host_taxid=562, limit=5)

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

## Testing and continuous integration

EHItk includes a pytest-based unit test suite in the `tests/` directory. The
repository also uses GitHub Actions continuous integration to run the test suite,
build source and wheel distributions, and perform CLI smoke tests across Python
3.10, 3.11, 3.12, 3.13, and 3.14.
