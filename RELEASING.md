# Releasing EHItk

This is the **canonical, cross-repo runbook** for shipping EHItk. It spans two
repositories owned by the same maintainer:

- **`ehitk`** (this repo) — the consumer: the Python CLI/API published to PyPI.
  It bundles a snapshot of the metadata catalog at
  `src/ehitk/data/ehitk.sqlite`.
- **[`ehitk-build`](https://github.com/earthhologenome/ehitk-build)** — the
  producer: builds `ehitk.sqlite` from Airtable. See its own
  `RELEASING.md` for the producer-side steps; this document is the source of
  truth for the end-to-end flow.

## Version lines

EHItk tracks four independent-but-linked version lines. Keep them distinct:

| Version line | Format | Lives in | Bumps when |
| --- | --- | --- | --- |
| `ehitk-build` semver | `X.Y.Z` | `ehitk-build` `pyproject.toml` / `__init__.py` | the generator code changes |
| `data_version` | `YYYY.MM.DD` (calendar) | the catalog's `catalog_meta` table | the catalog is regenerated from Airtable; **this is what Zenodo tracks** |
| `ehitk` semver | `X.Y.Z` | this repo's `pyproject.toml` | the consumer CLI/API changes |
| `schema_version` | integer | the catalog's `catalog_meta` table | the catalog schema changes in a way that breaks the code contract |

Every built catalog carries a `catalog_meta` table recording `data_version`,
`schema_version`, `built_with_ehitk_build`, and `source_snapshot`, so a loose
`.sqlite` is self-identifying. `ehitk` validates `schema_version` when opening a
catalog and `ehitk database` reports `data_version` / `schema_version`.

## Prerequisites

- A clone of both `ehitk` and `ehitk-build` side by side.
- `AIRTABLE_TOKEN` exported (a personal access token with read access to the EHI
  Airtable bases). Needed only to **rebuild** the catalog.
- Network access (the build fetches the ENVO ontology and NCBI taxonomy).
- Release tooling installed in the `ehitk` repo:
  `python -m pip install '.[dev,release]'`.
- Push access to both GitHub repos and the EHItk PyPI project (publishing is via
  Trusted Publishing in GitHub Actions, so no PyPI token is needed locally).

---

## Release checklist

A full release usually means: new data **and** a new `ehitk` version. If you are
only shipping code (no catalog change), skip steps 1–5 and reuse the bundled
catalog.

### 1. Refresh the Airtable source

Make sure the EHI Airtable data is current and the "API view" views are correct
in the **SE Samples (EHI Database)** and **MAGs (EHI MAG Database)** tables. The
builder pulls exactly those views (see the `ehitk-build` README).

### 2. Build the catalog (in `ehitk-build`)

```bash
cd ../ehitk-build
export AIRTABLE_TOKEN="…"
ehitk-build --output /tmp/ehitk.sqlite
```

This produces `ehitk.sqlite` with the data tables (`specimens`, `hologenomes`,
`mags`), the relationship views, the embedded ontology tables
(`envo_descendants`, `host_taxon_descendants`), and the `catalog_meta`
provenance table. The build runs a foreign-key check and fails if it does not
pass.

- Use `--skip-ontology` only for offline/debug builds; a real release catalog
  must include the ontology tables.
- Set the data version with `--data-version YYYY.MM.DD` (defaults to today). This
  is the version Zenodo tracks and that names the database artifact.

### 3. Verify the freshly built catalog

Point `ehitk` at the new file and sanity-check it before adopting it:

```bash
cd ../ehitk
ehitk --db /tmp/ehitk.sqlite database          # path, size, SHA256
ehitk --db /tmp/ehitk.sqlite                    # record counts per level
ehitk --db /tmp/ehitk.sqlite specimens query --host-species "Podarcis muralis" --limit 1
ehitk --db /tmp/ehitk.sqlite mags query --genus Escherichia --limit 1
```

Confirm the record counts and a few biome / host-taxonomy filters look right
(those exercise the embedded descendant tables).

### 4. Deposit the database to Zenodo (in `ehitk-build`)

The database artifact and its Zenodo deposit are owned by `ehitk-build` (the
producer owns the data lifecycle). The automated path is a tag:

```bash
cd ../ehitk-build
git tag data-v<data_version>          # e.g. data-v2026.06.28
git push origin data-v<data_version>
```

This triggers `ehitk-build`'s `data-release.yml`: it builds the catalog, emits
`ehitk-database-<data_version>.sqlite` (+ `.sha256`), deposits a **new version**
under the **database** Zenodo concept DOI
[`10.5281/zenodo.20430293`](https://doi.org/10.5281/zenodo.20430293) (record page
<https://zenodo.org/records/20430294> — a *separate* concept from the software
DOI), and attaches the artifact to a GitHub Release. To run it by hand, use
`ehitk-build --release` (or `ehitk-build --from <file>` to release an existing
catalog); it is idempotent and supports `--dry-run`. See `ehitk-build/RELEASING.md`.

### 5. Bridge the catalog into `ehitk` (producer → consumer)

The bridge is automated: `scripts/release.py` (step 7) fetches the latest
published catalog from Zenodo and writes it to `src/ehitk/data/ehitk.sqlite`, so
the bundled snapshot is always a citable, checksum-verified record. You normally
do **nothing** here — just make sure step 4 published the version you want to
ship before running the release script.

To preview or run the fetch on its own:

```bash
cd ../ehitk
python scripts/sync_catalog.py --dry-run                 # show which version would be embedded
python scripts/sync_catalog.py                           # embed the latest published catalog
python scripts/sync_catalog.py --data-version <data_version>   # pin an older release
```

Notes:

- The fetch refuses to embed a catalog whose `schema_version` this `ehitk`
  cannot read — bump `SUPPORTED_SCHEMA_VERSIONS` and the readers first, or pin a
  compatible `--data-version`.
- `src/ehitk/data/ehitk.sqlite` is the **canonical** bundled catalog; it ships
  in the wheel/sdist and is committed so source/editable installs work offline.
- For an offline or code-only release, pass `--skip-catalog-fetch` to keep the
  committed snapshot as-is. The legacy `sync_database()` path (root-level
  `data/ehitk.sqlite`) is only used when the Zenodo fetch is skipped.

### 6. Write release notes

Add the user-facing changes under the `## [Unreleased]` section of
`CHANGELOG.md` (replace the "No unreleased changes yet." placeholder). The
release script refuses to cut a release if this section is empty or still holds
only the placeholder.

### 7. Run the release script (in `ehitk`)

```bash
python scripts/release.py <ehitk_version>            # e.g. 1.3.0
# preview first:
python scripts/release.py <ehitk_version> --dry-run
```

`scripts/release.py` does all of the following:

- fetches the latest published catalog from Zenodo and embeds it at
  `src/ehitk/data/ehitk.sqlite` (`--catalog-data-version` to pin, or
  `--skip-catalog-fetch` to keep the committed snapshot; the legacy
  `sync_database()` is the fallback when the fetch is skipped),
- refreshes the published database list in the README and docs
  (`scripts/update_db_list.py`; best-effort — skipped with `--skip-db-list`),
- writes a local convenience artifact `dist/ehitk-database-<data_version>.sqlite`
  + `.sha256`, named by the `data_version` read from the bundled catalog. The
  canonical artifact + Zenodo deposit are produced by `ehitk-build` (step 4),
- bumps the version in `pyproject.toml`, `CITATION.cff`, and `codemeta.json`,
- cuts the `[Unreleased]` changelog section into a dated release section,
- runs `pytest`, `python -m build`, and `twine check`.

Useful flags: `--skip-tests`, `--skip-build`, `--skip-twine-check`,
`--skip-catalog-fetch`, `--catalog-data-version`, `--skip-db-list`,
`--skip-db-sync`, `--skip-db-artifact`.

### 8. Commit, tag, and push

```bash
git diff                                   # review every change
git commit -am "Release v<ehitk_version>"
git tag v<ehitk_version>
git push origin main
git push origin v<ehitk_version>
```

### 9. PyPI publish (automatic)

Pushing the `v*` tag triggers `.github/workflows/release.yml`: it verifies the
packaged catalog is present, runs the tests, builds, validates, smoke-tests the
wheel, and publishes to PyPI via Trusted Publishing. Confirm the run is green and
the new version appears on PyPI.

---

## Rollback

- **Bad tag, not yet on PyPI:** delete the tag locally and remotely
  (`git tag -d v<v>` / `git push origin :refs/tags/v<v>`), fix, re-tag.
- **Already on PyPI:** PyPI does not allow re-uploading a version. Yank the bad
  release on PyPI and ship a new patch version with the fix. Never reuse a
  version number.
- **Bad catalog bundled:** restore the previous `src/ehitk/data/ehitk.sqlite`
  from git history (`git checkout <prev> -- src/ehitk/data/ehitk.sqlite`),
  re-run the release script, and ship a patch release.
- **Bad Zenodo deposit:** Zenodo versions are immutable once published; publish a
  corrected new version under the same database concept DOI rather than editing
  in place.

## Quick reference (code-only release)

No catalog change → skip steps 1–5:

```bash
cd ehitk
# edit CHANGELOG.md [Unreleased]
python scripts/release.py <ehitk_version>
git commit -am "Release v<ehitk_version>" && git tag v<ehitk_version>
git push origin main && git push origin v<ehitk_version>
```
