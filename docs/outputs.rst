Outputs and columns
===================

Tables, CSV, and TSV
--------------------

By default, ``query`` and ``values`` commands print rich terminal tables.

Use ``--csv`` or ``--tsv`` to write results to a file:

.. code-block:: bash

   ehitk specimens query --host-lineage Reptilia --csv specimens.csv
   ehitk hologenomes values --field country --tsv countries.tsv
   ehitk mags query --quality high --columns mag_id,quality,url --csv high-quality-mags.csv

Use only one export format at a time.

Query column presets
--------------------

All ``query`` commands support ``--columns``.

``--columns default``
   Use the compact default column set for the resource. This is also the
   behavior when ``--columns`` is omitted.

``--columns all``
   Include every available query column for the resource.

``--columns url``
   Include URL-focused columns. This preset is available for ``hologenomes`` and
   ``mags``.

``--columns a,b,c``
   Include only the named columns.

Examples:

.. code-block:: bash

   ehitk specimens query --columns specimen_id,host_species,sex
   ehitk hologenomes query --columns url --csv hologenome-urls.csv
   ehitk mags query --columns all --limit 1
   ehitk mags query --columns url --tsv mag-urls.tsv

Default columns
---------------

``specimens``
   ``specimen_id``, ``host_taxid``, ``host_species``, ``host_order``, ``sex``.

``hologenomes``
   ``hologenome_id``, ``specimen_id``, ``sample_type``, ``host_species``,
   ``biome``, ``data_gb``.

``mags``
   ``mag_id``, ``host_species``, ``quality``, ``completeness``,
   ``contamination``, ``mag_genus``, ``mag_species``.

Value counts
------------

The ``values`` action counts distinct values for any available query field:

.. code-block:: bash

   ehitk specimens values --field host_order
   ehitk hologenomes values --field data_gb
   ehitk mags values --field genus

For MAGs, ``genus`` and ``species`` are aliases for ``mag_genus`` and
``mag_species``. ``quality`` is a derived field.

Statistics
----------

The ``stats`` action prints summaries after applying filters. Hologenome and MAG
statistics include available hologenome data volume in gigabases.
