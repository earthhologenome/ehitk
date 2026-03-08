<p align="center">
  <img src="docs/ehitk_logo.png" alt="EHItk logo" width="500">
</p>

[![CI](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml/badge.svg)](https://github.com/earthhologenome/ehitk/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://github.com/earthhologenome/ehitk)

The Earth Hologenome Initiative ToolKit (EHItk) is a command-line tool for finding, summarising and downloading date of EHI specimens, metagenomes and MAGs.

It is designed for two common workflows:

- find datasets by metadata
- download matching shotgun sequencing datasets and MAG FASTA files

## Features

- Query metagenomes by host metadata, sample type, biome, and release
- Query metagenomes by host metadata, geography, specimen measurements, sample type, biome, and release
- Query MAGs by taxonomy, parent metagenome, release, derived quality class, host taxonomy, geography, and specimen measurements
- Query specimens directly, including specimen measurement ranges
- Use friendly filters or an advanced `--where` SQL predicate
- Download paired metagenome reads and MAG FASTA files
- Show Rich progress bars with filename, progress, speed, and size
- Append every fetch outcome to `manifest.jsonl`

## Installation

EHItk requires Python 3.10 or newer.

Install directly from GitHub:

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
ehitk metagenomes query --db /path/to/ehitk.sqlite --limit 5
```

## Command Structure

```text
[ehitk]
├─ * specimens *
│  ├─ query
│  ├─ values
│  └─ stats
├─ * metagenomes *
│  ├─ query
│  ├─ values
│  ├─ stats
│  └─ fetch
└─ * mags *
   ├─ query
   ├─ values
   ├─ stats
   └─ fetch
```

## Quick Start

Query specimens:

```bash
ehitk specimens query --host-species "Podarcis muralis" --limit 5
```

Explore specimen filter values:

```bash
ehitk specimens values --field host_species --limit 10
```

Query metagenomes:

```bash
ehitk metagenomes query --host-species "Podarcis muralis" --limit 5
```

Explore metagenome values:

```bash
ehitk metagenomes values --field country --limit 10
```

Query MAGs:

```bash
ehitk mags query --genus Escherichia --limit 5
```

Explore MAG values:

```bash
ehitk mags values --field genus --limit 10
```

Summarize MAGs:

```bash
ehitk mags stats --quality high --species "Escherichia coli"
```

Fetch one metagenome:

```bash
ehitk metagenomes fetch --host-lineage Reptilia --limit 1
```

Write a metagenome batch download script instead of downloading immediately:

```bash
ehitk metagenomes fetch --host-lineage Reptilia --limit 1 --batch metagenomes.sh
```

Fetch one MAG:

```bash
ehitk mags fetch --species "Escherichia coli" --limit 1
```

Write a MAG batch download script instead of downloading immediately:

```bash
ehitk mags fetch --species "Escherichia coli" --limit 1 --batch mags.sh
```

## Querying Metagenomes

Supported metagenome filters:

- `--metagenome-id`
- `--host-taxid`
- `--host-species`
- `--host-lineage`
- `--sample-type`
- `--biome`
- `--country`
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
ehitk metagenomes query --metagenome-id EHI00001
ehitk metagenomes query --host-taxid 64176
ehitk metagenomes query --host-species "Podarcis muralis"
ehitk metagenomes query --host-lineage Reptilia
ehitk metagenomes query --sample-type Faecal --biome "1000221 - Temperate woodland"
ehitk metagenomes query --country recIUTmSxiyqoU5lQ --latitude-min 42.7 --latitude-max 42.8
ehitk metagenomes query --weight-min 3.0 --weight-max 6.0 --length-min 55 --length-max 65
ehitk metagenomes query --metagenome-id EHI00001,EHI00002
```

Most exact-match filters accept comma-separated values. For example, `--metagenome-id EHI00001,EHI00002` or `--host-species "Homo sapiens,Mus musculus"` matches any of the listed values.

`--host-lineage` matches exactly against:

- `host_species`
- `host_genus`
- `host_family`
- `host_order`
- `host_class`

Metagenome summary statistics:

```bash
ehitk metagenomes stats --host-species "Podarcis muralis"
```

Metagenome value summaries:

```bash
ehitk metagenomes values --field host_species
ehitk metagenomes values --field country --limit 20
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
- `--metagenome-id`
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
ehitk mags query --metagenome-id EHI00392
ehitk mags query --country recrACkHppgdXdQse --weight-min 630 --weight-max 690
ehitk mags query --mag-id EHM00001,EHM00002
```

MAG taxonomy values in the catalog may use GTDB-style prefixes such as `g__` and `s__`. EHItk normalizes those during filtering and display, so `--genus Escherichia` matches `g__Escherichia`.

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

## Controlling Query Columns

All `query` commands support `--columns`:

- `--columns default`: use the configured default columns for that command
- `--columns all`: include every available column in the query target
- `--columns url`: use the URL-focused preset for `metagenomes` and `mags`
- `--columns a,b,c`: include only the named columns

These examples are equivalent:

```bash
ehitk metagenomes query --host-species "Podarcis muralis"
ehitk metagenomes query --host-species "Podarcis muralis" --columns default
```

Examples:

```bash
ehitk specimens query --columns specimen_id,host_species,sex --csv specimens.csv
ehitk metagenomes query --columns url --csv metagenome_urls.csv
ehitk mags query --columns all --limit 1
ehitk mags query --columns url --tsv mag_urls.tsv
ehitk mags query --columns mag_id,host_species,mag_genus --limit 5
```

Column presets are configured in `src/ehitk/data/custom_columns.json`.

The `url` preset is only available for:

- `metagenomes`
- `mags`

It is not available for `specimens`.

## Advanced SQL Filtering

Power users can add an extra SQL predicate with `--where`.

Examples:

```bash
ehitk mags query --where "completeness >= 90 AND contamination <= 5"
ehitk metagenomes query --where "latitude > 40 AND longitude < 10"
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

### Metagenomes

`ehitk metagenomes fetch` downloads paired-end reads from `url1` and `url2`.

- records with missing read URLs are skipped
- files are written under `downloads/metagenomes/<metagenome_id>/`

Example:

```bash
ehitk metagenomes fetch --host-species "Podarcis muralis" --limit 1
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
- `--overwrite`
- `--limit`

Examples:

```bash
ehitk mags fetch --genus Escherichia --limit 2 --output-dir results
ehitk metagenomes fetch --release EHR01 --limit 1 --overwrite
ehitk mags fetch --quality high --limit 10 --batch mags-downloads.sh
```

When `--batch` is used, EHItk writes an executable shell script with `curl` commands and does not download files or append manifest entries at generation time.

## Download Manifest

Every fetch attempt appends a JSON object to `manifest.jsonl`.

Typical fields:

```json
{
  "timestamp": "2026-03-06T15:49:23.422576Z",
  "type": "metagenome",
  "metagenome_id": "EHI00366",
  "url": null,
  "path": null,
  "checksum": null,
  "status": "missing_url"
}
```

The identifier field is entity-specific:

- metagenome entries use `metagenome_id`
- MAG entries use `mag_id`

Possible statuses include:

- `downloaded`
- `skipped_existing`
- `missing_url`
- `failed`

Checksums are SHA-256 digests of the downloaded local file.
