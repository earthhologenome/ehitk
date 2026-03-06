# EHItk

The Earth Hologenome Initiative ToolKit (EHItk) is a command-line tool for easily fetching EHI.produced metagenomes, MAGs and related metadata.

It is designed for two common workflows:

- find datasets by metadata
- download matching shotgun sequencing datasets and MAG fasta files

## Features

- Query metagenomes by host metadata, sample type, biome, and release
- Query MAGs by taxonomy, parent metagenome, release, and derived quality class
- Use friendly filters or an advanced `--where` SQL predicate
- Download paired metagenome reads and MAG FASTA files
- Show Rich progress bars with filename, progress, speed, and size
- Append every fetch outcome to `manifest.jsonl`

## Installation

EHItk requires Python 3.10 or newer.

Install locally from this repository:

```bash
pip install git+https://github.com/earthhologenome/ehitk
```

Show the top-level help:

```bash
ehitk --help
```

## Command Structure

```text
ehitk
├─ metagenomes
│  ├─ query
│  └─ fetch
└─ mags
   ├─ query
   └─ fetch
```

## Quick Start

Query metagenomes:

```bash
ehitk metagenomes query --host-species "Podarcis muralis" --limit 5
```

Query MAGs:

```bash
ehitk mags query --genus Escherichia --limit 5
```

Fetch one MAG:

```bash
ehitk mags fetch --species "Escherichia coli" --limit 1
```

Fetch one metagenome:

```bash
ehitk metagenomes fetch --host-lineage Reptilia --limit 1
```

## Querying Metagenomes

Supported metagenome filters:

- `--host-taxid`
- `--host-species`
- `--host-lineage`
- `--sample-type`
- `--biome`
- `--release`
- `--where`
- `--limit`

Examples:

```bash
ehitk metagenomes query --host-taxid 64176
ehitk metagenomes query --host-species "Podarcis muralis"
ehitk metagenomes query --host-lineage Reptilia
ehitk metagenomes query --sample-type Faecal --biome "1000221 - Temperate woodland"
```

`--host-lineage` matches exactly against the lineage-related host columns already present in the catalog:

- `host_species`
- `host_genus`
- `host_family`
- `host_order`
- `host_class`

## Querying MAGs

Supported MAG filters:

- `--quality`
- `--genus`
- `--species`
- `--release`
- `--metagenome-id`
- `--where`
- `--limit`

Examples:

```bash
ehitk mags query --quality high
ehitk mags query --genus Escherichia
ehitk mags query --species "Escherichia coli"
ehitk mags query --metagenome-id EHI00392
```

MAG taxonomy values in the catalog may use GTDB-style prefixes such as `g__` and `s__`. EHItk normalizes those during filtering and display, so `--genus Escherichia` matches `g__Escherichia`.

Derived MAG quality classes are defined as:

- `high`: `completeness >= 90` and `contamination <= 5`
- `medium`: `completeness >= 50` and `contamination <= 10`
- `low`: everything else

## Advanced SQL Filtering

Power users can add an extra SQL predicate with `--where`.

Example:

```bash
ehitk mags query --where "completeness >= 90 AND contamination <= 5"
ehitk metagenomes query --where "latitude > 40 AND longitude < 10"
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

- both URLs must be present
- records with missing read URLs are skipped
- files are written under `downloads/metagenomes/<metagenome_id>/`

Example:

```bash
ehitk metagenomes fetch --host-species "Podarcis muralis" --limit 1
```

### MAGs

`ehitk mags fetch` downloads the MAG FASTA from `url`.

- files are written under `downloads/mags/<mag_id>/`

Example:

```bash
ehitk mags fetch --quality high --limit 3
```

### Output Options

Both `fetch` commands support:

- `--output-dir PATH`
- `--manifest-path PATH`
- `--overwrite`
- `--limit`

Examples:

```bash
ehitk mags fetch --genus Escherichia --limit 2 --output-dir results
ehitk metagenomes fetch --release recActKG66780K7SC --limit 1 --overwrite
```

## Download Manifest

Every fetch attempt appends a JSON object to `manifest.jsonl`.

Typical fields:

```json
{
  "timestamp": "2026-03-06T15:49:23.422576Z",
  "type": "metagenome",
  "genome_id": "EHI00366",
  "url": null,
  "path": null,
  "checksum": null,
  "status": "missing_url"
}
```

Possible statuses include:

- `downloaded`
- `skipped_existing`
- `missing_url`
- `failed`

Checksums are SHA-256 digests of the downloaded local file.

## Catalog Notes

The repository currently contains the source catalog at:

```text
data/ehitk.sqlite
```

The Python package bundles a copy at install time so the CLI works out of the box.

The current catalog includes:

- metagenome metadata and paired read URLs (`url1`, `url2`)
- MAG metadata and MAG FASTA URLs (`url`)
- a MAG-to-metagenome relationship through `metagenome_id`

## Development

Run tests:

```bash
python3 -m pytest
```

Run the CLI without installing:

```bash
PYTHONPATH=src python3 -m ehitk.cli --help
```
