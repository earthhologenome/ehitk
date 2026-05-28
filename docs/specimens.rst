Specimens
=========

Use ``ehitk specimens`` to inspect host and specimen metadata.

Query specimens
---------------

.. code-block:: bash

   ehitk specimens query --host-species "Podarcis muralis"
   ehitk specimens query --host-lineage Mammalia --sex Female
   ehitk specimens query --weight-min 8 --weight-max 9 --length-min 40 --length-max 41
   ehitk specimens query --specimen-id SD00508 --columns specimen_id,host_species,sex

Filters
-------

``--specimen-id``
   Exact specimen ID.

``--host-taxid``
   Exact host taxon ID.

``--host-species``
   Exact host species name.

``--host-lineage``
   Exact term matched against ``host_species``, ``host_genus``,
   ``host_family``, ``host_order``, and ``host_class``.

``--sex``
   Exact sex label.

``--weight-min`` and ``--weight-max``
   Minimum and maximum recorded specimen weight.

``--length-min`` and ``--length-max``
   Minimum and maximum recorded specimen length.

The catalog may store multiple recorded weight or length values per specimen.
Range filters match when any recorded value falls inside the requested range.

Summarize specimens
-------------------

.. code-block:: bash

   ehitk specimens stats --host-lineage Reptilia
   ehitk specimens values --field host_order
   ehitk specimens values --field sex --csv --output-file specimen-sex-values.csv

Available query columns
-----------------------

``specimen_id``, ``host_taxid``, ``host_species``, ``host_genus``,
``host_family``, ``host_order``, ``host_class``, ``weight``, ``length``, and
``sex``.
