<p align="center">
  <img src="https://raw.githubusercontent.com/earthhologenome/ehitk/main/docs/ehitk_logo.png" alt="EHItk logo" width="500">
</p>

[![CI](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml/badge.svg)](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/earthhologenome/ehitk)

The Earth Hologenome Initiative ToolKit (EHItk) is a command-line tool for finding, summarising and downloading data from EHI specimens, hologenomes and MAGs.

It supports three common tasks:

- find datasets by metadata
- summarise matching records and available data volume
- download matching shotgun sequencing datasets and MAG FASTA files

## Features

- Explore `specimens`, `hologenomes`, and `mags` through a consistent CLI
- Filter hologenomes by host taxonomy, geography, biome, sample type, and available data volume
- Filter MAGs by microbial taxonomy, derived quality class, parent hologenome metadata, and linked specimen metadata
- Inspect distinct field values with `values` and summarise filtered subsets with `stats`
- Export query results to CSV or TSV
- Download paired hologenome reads and MAG FASTA files, or emit batch download scripts
- Track fetch outcomes in `manifest.jsonl`
- Use the bundled SQLite catalog by default, or point to an alternate database with `--db`
- Add advanced SQL predicates with `--where` when needed

## Installation

EHItk requires Python 3.10 or newer.

Install from PyPI:

```bash
pip install ehitk
```

Install from GitHub if you need the latest unreleased version:

```bash
pip install git+https://github.com/earthhologenome/ehitk
```

Show the top-level help:

```bash
ehitk --help
```

Show the installed version:

```bash
ehitk --version
```

Use a specific SQLite database file:

```bash
ehitk --db /path/to/ehitk.sqlite --help
ehitk hologenomes query --db /path/to/ehitk.sqlite --limit 5
```

By default, EHItk uses the bundled SQLite catalog that ships with the installed package version. This means package updates also update the default catalog unless you explicitly override it with `--db`.

## Command Overview

EHItk is organised around three resource types:

- `specimens`: inspect host and specimen metadata
- `hologenomes`: query and download shotgun sequencing datasets
- `mags`: query and download metagenome-assembled genomes

Each resource type supports a consistent action model:

- `query`: return matching records
- `values`: list distinct values and counts for a chosen field
- `stats`: summarise a filtered subset
- `fetch`: download matching files, available for `hologenomes` and `mags`

## Quick Start

Inspect specimen metadata:

```bash
ehitk specimens query --host-species "Podarcis muralis" --limit 5
```

Explore specimen filter values:

```bash
ehitk specimens values --field host_species --limit 10
```

Query hologenomes:

```bash
ehitk hologenomes query --host-species "Podarcis muralis" --limit 5
```

Inspect available hologenome values:

```bash
ehitk hologenomes values --field country --limit 10
ehitk hologenomes values --field data_gb --limit 10
```

Query MAGs:

```bash
ehitk mags query --genus Escherichia --limit 5
```

Inspect available MAG values:

```bash
ehitk mags values --field genus --limit 10
```

Summarise MAGs:

```bash
ehitk mags stats --quality high --species "Escherichia coli"
```

Fetch one hologenome:

```bash
ehitk hologenomes fetch --host-lineage Reptilia --limit 1
```

Generate a hologenome batch download script instead of downloading immediately:

```bash
ehitk hologenomes fetch --host-lineage Reptilia --limit 1 --batch hologenomes.sh
```

Fetch one MAG:

```bash
ehitk mags fetch --species "Escherichia coli" --limit 1
```

Generate a MAG batch download script instead of downloading immediately:

```bash
ehitk mags fetch --species "Escherichia coli" --limit 1 --batch mags.sh
```

## Querying Specimens

Supported specimen filters:

- `--specimen-id`
- `--host-taxid`
- `--host-species`
- `--host-lineage`
- `--sex`
- `--weight-min`
- `--weight-max`
- `--length-min`
- `--length-max`
- `--columns`
- `--where`
- `--limit`

Examples:

```bash
ehitk specimens query --specimen-id SD00508
ehitk specimens query --host-species "Podarcis muralis"
ehitk specimens query --host-lineage Mammalia --sex Female
ehitk specimens query --weight-min 8 --weight-max 9 --length-min 40 --length-max 41
```

For `weight` and `length`, the catalog may store multiple recorded values per specimen. Range filters match when any recorded value falls within the requested interval.

Specimen summary statistics:

```bash
ehitk specimens stats --host-lineage Reptilia
```

Specimen value summaries:

```bash
ehitk specimens values --field host_order
ehitk specimens values --field sex --csv specimen-sex-values.csv
```

`values` prints distinct values with counts for a chosen field after applying any other filters. For MAGs, `--field genus`, `--field species`, and `--field quality` are supported aliases.

## Querying Hologenomes

Supported hologenome filters:

- `--hologenome-id`
- `--host-taxid`
- `--host-species`
- `--host-lineage`
- `--sample-type`
- `--biome`
- `--country`
- `--data-min`
- `--data-max`
- `--latitude-min`
- `--latitude-max`
- `--longitude-min`
- `--longitude-max`
- `--weight-min`
- `--weight-max`
- `--length-min`
- `--length-max`
- `--release`
- `--columns`
- `--where`
- `--limit`

Examples:

```bash
ehitk hologenomes query --hologenome-id EHI00001
ehitk hologenomes query --host-taxid 64176
ehitk hologenomes query --host-species "Podarcis muralis"
ehitk hologenomes query --host-lineage Reptilia
ehitk hologenomes query --sample-type Faecal --biome "1000221 - Temperate woodland"
ehitk hologenomes query --data-min 5 --data-max 25
ehitk hologenomes query --country Italy --latitude-min 42.7 --latitude-max 42.8
ehitk hologenomes query --weight-min 3.0 --weight-max 6.0 --length-min 55 --length-max 65
ehitk hologenomes query --hologenome-id EHI00001,EHI00002
```

Most exact-match filters accept comma-separated values. For example, `--hologenome-id EHI00001,EHI00002` or `--host-species "Homo sapiens,Mus musculus"` matches any of the listed values.

`--host-lineage` matches exactly against:

- `host_species`
- `host_genus`
- `host_family`
- `host_order`
- `host_class`

Hologenome summary statistics:

```bash
ehitk hologenomes stats --host-species "Podarcis muralis"
```

Hologenome and MAG statistics include available hologenome data totals in gigabases (GB).

Hologenome value summaries:

```bash
ehitk hologenomes values --field host_species
ehitk hologenomes values --field country --limit 20
```

## Querying MAGs

Supported MAG filters:

- `--mag-id`
- `--quality`
- `--genus`
- `--species`
- `--host-taxid`
- `--host-species`
- `--host-lineage`
- `--country`
- `--release`
- `--hologenome-id`
- `--latitude-min`
- `--latitude-max`
- `--longitude-min`
- `--longitude-max`
- `--weight-min`
- `--weight-max`
- `--length-min`
- `--length-max`
- `--columns`
- `--where`
- `--limit`

Examples:

```bash
ehitk mags query --quality high
ehitk mags query --quality high,medium
ehitk mags query --mag-id EHM00001
ehitk mags query --genus Escherichia
ehitk mags query --species "Escherichia coli"
ehitk mags query --host-species "Sciurus carolinensis"
ehitk mags query --hologenome-id EHI00392
ehitk mags query --country Italy --weight-min 630 --weight-max 690
ehitk mags query --mag-id EHM00001,EHM00002
```

MAG taxonomy values in the catalog may use GTDB-style prefixes such as `g__` and `s__`. EHItk normalizes those during filtering and display, so `--genus Escherichia` matches `g__Escherichia`.

Because MAGs are linked to parent hologenomes and specimens in the catalog, MAG queries can also use host taxonomy, geography, and specimen measurement filters.

Derived MAG quality classes are defined as:

- `high`: `completeness >= 90` and `contamination <= 5`
- `medium`: `completeness >= 50` and `contamination <= 10`
- `low`: everything else

MAG summary statistics:

```bash
ehitk mags stats --quality high --species "Escherichia coli"
ehitk mags stats --host-species "Sciurus carolinensis"
```

MAG value summaries:

```bash
ehitk mags values --field genus
ehitk mags values --field quality
```

## Controlling Query Columns

All `query` commands support `--columns`:

- `--columns default`: use the configured default columns for that command
- `--columns all`: include every available column in the query target
- `--columns url`: use the URL-focused preset for `hologenomes` and `mags`
- `--columns a,b,c`: include only the named columns

These examples are equivalent:

```bash
ehitk hologenomes query --host-species "Podarcis muralis"
ehitk hologenomes query --host-species "Podarcis muralis" --columns default
```

Examples:

```bash
ehitk specimens query --columns specimen_id,host_species,sex --csv specimens.csv
ehitk hologenomes query --columns url --csv hologenome_urls.csv
ehitk mags query --columns all --limit 1
ehitk mags query --columns url --tsv mag_urls.tsv
ehitk mags query --columns mag_id,host_species,mag_genus --limit 5
```

Default columns are chosen to give a compact, user-friendly view for each resource.

The default hologenome view includes the `data_gb` column so dataset size is visible without requesting extra columns.

The default MAG view includes the derived `quality` column, and `--columns all` includes `quality` as well.

The `url` preset is only available for:

- `hologenomes`
- `mags`

It is not available for `specimens`.

## Advanced SQL Filtering

Power users can add an extra SQL predicate with `--where`.

Examples:

```bash
ehitk mags query --where "completeness >= 90 AND contamination <= 5"
ehitk hologenomes query --where "latitude > 40 AND longitude < 10"
ehitk specimens query --where "weight IS NOT NULL"
```

The `--where` string is appended to the generated SQL query after validation.

For safety, EHItk rejects predicates containing:

- `;`
- `DROP`
- `DELETE`
- `INSERT`
- `UPDATE`
- `ALTER`
- `ATTACH`
- `PRAGMA`
- SQL comment markers such as `--` and `/* ... */`

## Fetching Data

### Hologenomes

`ehitk hologenomes fetch` downloads paired-end reads from `url1` and `url2`.

- records with missing read URLs are skipped
- files are written under `downloads/hologenomes/<hologenome_id>/`

On first use, EHItk asks you to confirm the EHI data usage terms before continuing.

Example:

```bash
ehitk hologenomes fetch --host-species "Podarcis muralis" --limit 1
```

### MAGs

`ehitk mags fetch` downloads the MAG FASTA from `url`.

- files are written under `downloads/mags/<mag_id>/`
- MAG selection can include host taxonomy filters because host metadata is resolved through specimens

Example:

```bash
ehitk mags fetch --host-lineage Mammalia --quality high --limit 3
```

### Output Options

Both `fetch` commands support:

- `--output-dir PATH`
- `--batch PATH`
- `--manifest-path PATH`
- `--accept-terms`
- `--overwrite`
- `--limit`

Examples:

```bash
ehitk mags fetch --genus Escherichia --limit 2 --output-dir results
ehitk hologenomes fetch --release EHR01 --limit 1 --overwrite
ehitk mags fetch --quality high --limit 10 --batch mags-downloads.sh
```

When `--batch` is used, EHItk writes an executable shell script with `curl` commands and does not download files or append manifest entries at generation time.

Before any fetch operation, EHItk displays the EHI data usage terms and asks for confirmation. After you have read and accepted them, use `--accept-terms` to suppress the prompt in future commands.

## Download Manifest

Every fetch attempt appends a JSON object to `manifest.jsonl`.

Typical fields:

```json
{
  "timestamp": "2026-03-06T15:49:23.422576Z",
  "type": "hologenome",
  "hologenome_id": "EHI00366",
  "url": null,
  "path": null,
  "checksum": null,
  "status": "missing_url"
}
```

The identifier field is entity-specific:

- hologenome entries use `hologenome_id`
- MAG entries use `mag_id`

Possible statuses include:

- `downloaded`
- `skipped_existing`
- `missing_url`
- `failed`

Checksums are SHA-256 digests of the downloaded local file.
