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
