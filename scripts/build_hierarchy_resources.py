from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ENVO_OBO_URL = "https://purl.obolibrary.org/obo/envo.obo"
NCBI_EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build compact ENVO and NCBI descendant maps for catalog terms."
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("src/ehitk/data/ehitk.sqlite"),
        help="Path to the EHItk SQLite catalog.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/ehitk/data"),
        help="Directory for generated JSON resources.",
    )
    args = parser.parse_args()

    observed_envo, observed_taxids = observed_catalog_terms(args.catalog)
    envo_descendants = build_envo_descendants(observed_envo)
    host_taxon_descendants = build_host_taxon_descendants(observed_taxids)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.output_dir / "envo_descendants.json", envo_descendants)
    write_json(args.output_dir / "host_taxon_descendants.json", host_taxon_descendants)

    # Embed the same maps as auxiliary tables in the catalog so the descendant
    # hierarchy always travels with, and stays in sync with, the SQLite snapshot
    # it describes (including pinned or custom databases used via ``--db``).
    write_descendant_tables(args.catalog, envo_descendants, host_taxon_descendants)

    print(
        f"Wrote {len(envo_descendants)} ENVO ancestor entries for "
        f"{len(observed_envo)} observed ENVO IDs."
    )
    print(
        f"Wrote {len(host_taxon_descendants)} NCBI ancestor entries for "
        f"{len(observed_taxids)} observed host taxids."
    )
    print(
        f"Embedded envo_descendants and host_taxon_descendants tables into {args.catalog}."
    )


def observed_catalog_terms(catalog: Path) -> tuple[list[str], list[str]]:
    with sqlite3.connect(catalog) as connection:
        observed_envo = sorted(
            {
                row[0].strip()
                for row in connection.execute(
                    """
                    SELECT DISTINCT biome_envo_id
                    FROM hologenomes
                    WHERE biome_envo_id IS NOT NULL AND TRIM(biome_envo_id) <> ''
                    """
                )
            }
        )
        observed_taxids = sorted(
            {
                row[0].strip()
                for row in connection.execute(
                    """
                    SELECT DISTINCT host_taxid
                    FROM specimens
                    WHERE host_taxid IS NOT NULL AND TRIM(host_taxid) <> ''
                    """
                )
            },
            key=natural_taxid_key,
        )
    return observed_envo, observed_taxids


def build_envo_descendants(observed_envo: list[str]) -> dict[str, list[str]]:
    obo_text = fetch_text(ENVO_OBO_URL)
    parents: dict[str, set[str]] = defaultdict(set)
    current_id: str | None = None

    for raw_line in obo_text.splitlines():
        line = raw_line.strip()
        if line == "[Term]":
            current_id = None
        elif line.startswith("id: "):
            current_id = line[4:].strip()
        elif current_id and line.startswith("is_a: "):
            parents[current_id].add(line[6:].split()[0])

    descendants: dict[str, set[str]] = defaultdict(set)
    for descendant in observed_envo:
        for ancestor in ancestors_for(descendant, parents):
            if ancestor.startswith("ENVO:"):
                descendants[ancestor].add(descendant)
    return {key: sorted(values) for key, values in sorted(descendants.items())}


def ancestors_for(term: str, parents: dict[str, set[str]]) -> set[str]:
    seen = {term}
    stack = list(parents.get(term, ()))
    while stack:
        parent = stack.pop()
        if parent in seen:
            continue
        seen.add(parent)
        stack.extend(parents.get(parent, ()))
    return seen


def build_host_taxon_descendants(observed_taxids: list[str]) -> dict[str, list[str]]:
    observed = set(observed_taxids)
    descendants: dict[str, set[str]] = defaultdict(set)
    for batch in chunked(observed_taxids, 80):
        query = urllib.parse.urlencode(
            {"db": "taxonomy", "id": ",".join(batch), "retmode": "xml"}
        )
        xml = fetch_bytes(f"{NCBI_EFETCH_URL}?{query}")
        root = ET.fromstring(xml)
        for taxon in root.findall(".//Taxon"):
            taxid = taxon.findtext("TaxId")
            if taxid is None:
                continue
            descendant = taxid.strip()
            if descendant not in observed:
                continue
            ancestors = [descendant]
            for lineage_taxon in taxon.findall("./LineageEx/Taxon"):
                ancestor = lineage_taxon.findtext("TaxId")
                if ancestor:
                    ancestors.append(ancestor.strip())
            for ancestor in ancestors:
                descendants[ancestor].add(descendant)

    return {
        key: sorted(values, key=natural_taxid_key)
        for key, values in sorted(descendants.items(), key=lambda item: natural_taxid_key(item[0]))
    }


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8")


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def chunked(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def natural_taxid_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def write_descendant_tables(
    catalog: Path,
    envo_descendants: dict[str, list[str]],
    host_taxon_descendants: dict[str, list[str]],
) -> None:
    with sqlite3.connect(catalog) as connection:
        _write_descendant_table(connection, "envo_descendants", envo_descendants)
        _write_descendant_table(
            connection, "host_taxon_descendants", host_taxon_descendants
        )
        connection.commit()


def _write_descendant_table(
    connection: sqlite3.Connection,
    table: str,
    mapping: dict[str, list[str]],
) -> None:
    connection.execute(f'DROP TABLE IF EXISTS "{table}"')
    connection.execute(
        f'CREATE TABLE "{table}" (ancestor TEXT NOT NULL, descendant TEXT NOT NULL)'
    )
    connection.executemany(
        f'INSERT INTO "{table}" (ancestor, descendant) VALUES (?, ?)',
        [
            (ancestor, descendant)
            for ancestor, descendants in mapping.items()
            for descendant in descendants
        ],
    )
    connection.execute(
        f'CREATE INDEX "idx_{table}_ancestor" ON "{table}" (ancestor)'
    )


def write_json(path: Path, payload: dict[str, list[str]]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
