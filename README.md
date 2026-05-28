<p align="center">
  <img src="https://raw.githubusercontent.com/earthhologenome/ehitk/main/docs/ehitk_logo.png" alt="EHItk logo" width="500">
</p>

[![CI](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml/badge.svg)](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/earthhologenome/ehitk)

# EHItk

The Earth Hologenome Initiative ToolKit (EHItk) is a command-line tool for
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
```

## Documentation

Full installation instructions, command reference, examples, output formats, and
download guidance are available at:

https://ehitk.readthedocs.io/

Use the built-in help for local command details:

```bash
ehitk --help
ehitk specimens --help
ehitk hologenomes fetch --help
ehitk mags query --help
```
