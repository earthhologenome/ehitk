Fetching data
=============

Fetch commands are available for ``hologenomes`` and ``mags``.

Data usage terms
----------------

Before downloading, EHItk displays the EHI data usage terms and asks for
confirmation. After you have read and accepted the terms, use
``--accept-terms`` to suppress the prompt in future commands.

Hologenome downloads
--------------------

``ehitk hologenomes fetch`` downloads paired-end reads from ``url1`` and
``url2``. Files are written under:

.. code-block:: text

   downloads/hologenomes/<hologenome_id>/

Example:

.. code-block:: bash

   ehitk hologenomes fetch --host-species "Podarcis muralis" --limit 1

MAG downloads
-------------

``ehitk mags fetch`` downloads MAG FASTA files from ``url``. Files are written
under:

.. code-block:: text

   downloads/mags/<mag_id>/

Example:

.. code-block:: bash

   ehitk mags fetch --quality high --limit 3

Batch scripts
-------------

Use ``--batch PATH`` to write an executable shell script with ``curl`` commands
instead of downloading immediately:

.. code-block:: bash

   ehitk hologenomes fetch --release EHR01 --limit 1 --batch hologenomes.sh
   ehitk mags fetch --quality high --limit 10 --batch mags-downloads.sh

Batch generation does not append manifest entries because the files are not
downloaded by EHItk at generation time.

Snakemake example
-----------------

The following minimal Snakemake template chains EHItk hologenome fetching with
paired-end quality filtering through ``fastp``. It assumes that ``ehitk``,
``snakemake``, and ``fastp`` are available in the execution environment.

Example ``config.yaml``:

.. code-block:: yaml

   hologenome_ids:
     - EHI00001

Example ``Snakefile``:

.. code-block:: python

   from pathlib import Path
   from urllib.parse import urlparse

   import ehitk


   configfile: "config.yaml"

   HOLOGENOME_IDS = config["hologenome_ids"]
   DOWNLOAD_DIR = Path("downloads")


   def filename_from_url(url, fallback):
       name = Path(urlparse(url).path).name
       return name or fallback


   def read_paths(wildcards):
       with ehitk.Database() as ehidb:
           records = ehidb.hologenomes.query(
               hologenome_id=wildcards.hologenome_id,
               columns=["hologenome_id", "url1", "url2"],
               limit=1,
           )

       if not records:
           raise ValueError(f"Unknown hologenome_id: {wildcards.hologenome_id}")

       record = records[0]
       base = DOWNLOAD_DIR / "hologenomes" / record.hologenome_id
       return {
           "r1": base / filename_from_url(
               record.url1, f"{record.hologenome_id}_1.fastq.gz"
           ),
           "r2": base / filename_from_url(
               record.url2, f"{record.hologenome_id}_2.fastq.gz"
           ),
       }


   def read1(wildcards):
       return read_paths(wildcards)["r1"]


   def read2(wildcards):
       return read_paths(wildcards)["r2"]


   rule all:
       input:
           expand(
               "results/fastp/{hologenome_id}_R1.fastq.gz",
               hologenome_id=HOLOGENOME_IDS,
           ),
           expand(
               "results/fastp/{hologenome_id}_R2.fastq.gz",
               hologenome_id=HOLOGENOME_IDS,
           ),


   rule fetch_hologenome:
       output:
           directory("downloads/hologenomes/{hologenome_id}")
       shell:
           """
           ehitk hologenomes fetch \
             --hologenome-id {wildcards.hologenome_id} \
             --output-dir downloads \
             --accept-terms
           """


   rule fastp:
       input:
           raw_dir=rules.fetch_hologenome.output
       output:
           r1="results/fastp/{hologenome_id}_R1.fastq.gz",
           r2="results/fastp/{hologenome_id}_R2.fastq.gz",
           html="results/fastp/{hologenome_id}.html",
           json="results/fastp/{hologenome_id}.json",
       params:
           r1=read1,
           r2=read2,
       threads: 4
       shell:
           """
           fastp \
             --in1 {params.r1} \
             --in2 {params.r2} \
             --out1 {output.r1} \
             --out2 {output.r2} \
             --html {output.html} \
             --json {output.json} \
             --thread {threads}
           """

Run the workflow with:

.. code-block:: bash

   snakemake --cores 4

Fetch options
-------------

``--output-dir PATH``
   Base output directory. Defaults to ``downloads``.

``--batch PATH``
   Write a shell script instead of downloading now.

``--manifest-path PATH``
   Path to the append-only download manifest. Defaults to ``manifest.jsonl``.

``--accept-terms``
   Skip the interactive data usage terms prompt.

``--overwrite``
   Overwrite existing files instead of skipping them.

``--limit N``
   Limit the number of matching records to fetch.

Download manifest
-----------------

Every immediate fetch attempt appends one JSON object per file to
``manifest.jsonl``. Typical fields are:

.. code-block:: json

   {
     "timestamp": "2026-03-06T15:49:23.422576Z",
     "type": "hologenome",
     "hologenome_id": "EHI00366",
     "url": null,
     "path": null,
     "checksum": null,
     "status": "missing_url"
   }

Hologenome entries use ``hologenome_id``. MAG entries use ``mag_id``.

Possible statuses include ``downloaded``, ``skipped_existing``, ``missing_url``,
and ``failed``. Checksums are SHA-256 digests of downloaded files.
