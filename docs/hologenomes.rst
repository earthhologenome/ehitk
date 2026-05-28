Hologenomes
===========

Use ``ehitk hologenomes`` to find shotgun metagenomic sequencing datasets and
download paired-end reads.

Query hologenomes
-----------------

.. code-block:: bash

   ehitk hologenomes query --hologenome-id EHI00001
   ehitk hologenomes query --host-species "Podarcis muralis"
   ehitk hologenomes query --host-taxid 8509
   ehitk hologenomes query --host-lineage Reptilia
   ehitk hologenomes query --sample-type Faecal --biome-name "Temperate woodland"
   ehitk hologenomes query --biome ENVO:01000175
   ehitk hologenomes query --data-min 5 --data-max 25
   ehitk hologenomes query --country Italy --latitude-min 42.7 --latitude-max 42.8
   ehitk hologenomes query --hologenome-id EHI00001,EHI00002

Filters
-------

``--hologenome-id``
   Exact hologenome ID. Comma-separated values are accepted.

``--host-taxid``, ``--host-species``, ``--host-lineage``
   Host taxonomy filters. ``--host-taxid`` accepts NCBI taxon identifiers and
   includes catalog descendants, so ``8509`` matches Squamata host species.
   ``--host-lineage`` matches species, genus, family, order, or class.

``--sample-type``
   Exact sample metadata label.

``--biome-envo-id``/``--biome`` and ``--biome-name``
   Biome filters. ENVO identifier filters include catalog descendants, so
   ``ENVO:01000175`` matches woodland biome subclasses such as
   ``ENVO:01000221``. ``--biome-name`` matches the human-readable biome name
   exactly.

``--country``
   Exact country label.

``--release``
   Exact EHI release ID.

``--data-min`` and ``--data-max``
   Minimum and maximum available data volume in gigabases.

``--latitude-min``, ``--latitude-max``, ``--longitude-min``, ``--longitude-max``
   Coordinate range filters.

``--weight-min``, ``--weight-max``, ``--length-min``, ``--length-max``
   Linked specimen measurement filters.

Summarize hologenomes
---------------------

.. code-block:: bash

   ehitk hologenomes stats --host-species "Podarcis muralis"
   ehitk hologenomes fields
   ehitk hologenomes values --field host_species
   ehitk hologenomes values --field biome_name
   ehitk hologenomes values --field country --limit 20
   ehitk hologenomes values --field data_gb --limit 10

Download hologenomes
--------------------

``ehitk hologenomes fetch`` downloads paired-end reads from ``url1`` and
``url2``. Records with missing read URLs are skipped.

.. code-block:: bash

   ehitk hologenomes fetch --host-species "Podarcis muralis" --limit 1
   ehitk hologenomes fetch --release EHR01 --limit 1 --batch hologenomes.sh

Available query columns
-----------------------

``hologenome_id``, ``release``, ``sample_type``, ``latitude``, ``longitude``,
``country``, ``date``, ``url1``, ``url2``, ``biome_envo_id``,
``biome_name``, ``data_gb``, ``specimen_id``, ``host_taxid``,
``host_species``, ``host_genus``, ``host_family``, ``host_order``,
``host_class``, ``weight``, ``length``, and ``sex``.
