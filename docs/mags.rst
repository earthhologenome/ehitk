MAGs
====

Use ``ehitk mags`` to find metagenome-assembled genomes. MAG records are linked
to parent hologenomes, so MAG queries can also use host taxonomy, geography, and
specimen measurement filters.

Query MAGs
----------

.. code-block:: bash

   ehitk mags query --quality high
   ehitk mags query --quality high,medium
   ehitk mags query --mag-id EHM00001
   ehitk mags query --genus Escherichia
   ehitk mags query --species "Escherichia coli"
   ehitk mags query --host-species "Sciurus carolinensis"
   ehitk mags query --host-taxid 40674
   ehitk mags query --biome ENVO:01000175
   ehitk mags query --hologenome-id EHI00392
   ehitk mags query --country Italy --weight-min 630 --weight-max 690

Filters
-------

``--mag-id``
   Exact MAG ID. Comma-separated values are accepted.

``--quality``
   Derived MAG quality class. Accepted values are ``high``, ``medium``, and
   ``low``. Comma-separated values are accepted.

``--genus`` and ``--species``
   Exact MAG taxonomy. EHItk normalizes GTDB-style ``g__`` and ``s__`` prefixes,
   so ``--genus Escherichia`` also matches ``g__Escherichia``.

``--host-taxid``, ``--host-species``, ``--host-lineage``
   Linked host taxonomy filters. ``--host-taxid`` is an NCBI host taxon
   identifier filter and includes catalog descendants. MAG taxonomy itself is
   still filtered with ``--genus`` and ``--species``.

Taxonomy output
   The default MAG query output includes the host NCBI ``host_taxid`` together
   with host species, genus, and family names, plus MAG family, genus, and
   species labels. MAG taxonomic labels come from GTDB-style MAG assignments;
   NCBI taxon identifiers are therefore reported for hosts, but not inferred
   for MAG taxa.

``--biome-envo-id``/``--biome`` and ``--biome-name``
   Linked parent-hologenome biome filters. ENVO identifier filters include
   catalog descendants; biome name filters are exact.

Geography filters
   Linked sampling geography filters.

   Options: ``--country``, ``--latitude-min``, ``--latitude-max``,
   ``--longitude-min``, and ``--longitude-max``.

``--release``
   Exact MAG release ID.

``--hologenome-id``
   Exact parent hologenome ID.

``--weight-min``, ``--weight-max``, ``--length-min``, ``--length-max``
   Linked specimen measurement filters.

MAG quality classes
-------------------

``high``
   ``completeness >= 90`` and ``contamination <= 5``.

``medium``
   ``completeness >= 50`` and ``contamination <= 10``.

``low``
   Records that do not meet the medium threshold.

Summarize MAGs
--------------

.. code-block:: bash

   ehitk mags stats --quality high --species "Escherichia coli"
   ehitk mags stats --host-species "Sciurus carolinensis"
   ehitk mags fields
   ehitk mags values --field genus
   ehitk mags values --field species
   ehitk mags values --field quality

Download MAGs
-------------

``ehitk mags fetch`` downloads the MAG FASTA from ``url``.

.. code-block:: bash

   ehitk mags fetch --host-lineage Mammalia --quality high --limit 3
   ehitk mags fetch --quality high --limit 10 --batch mags-downloads.sh

Available query columns
-----------------------

``mag_id``, ``release``, ``quality``, ``completeness``, ``contamination``,
``size``, ``gc``, ``n50``, ``contigs``, ``mag_domain``, ``mag_phylum``,
``mag_class``, ``mag_order``, ``mag_family``, ``mag_genus``, ``url``,
``mag_species``, ``hologenome_id``, ``hologenome_release``, ``sample_type``,
``latitude``, ``longitude``, ``country``, ``date``, ``url1``, ``url2``,
``biome_envo_id``, ``biome_name``, ``data_gb``, ``specimen_id``,
``host_taxid``, ``host_species``, ``host_genus``, ``host_family``,
``host_order``, ``host_class``, ``weight``, ``length``, and ``sex``.
