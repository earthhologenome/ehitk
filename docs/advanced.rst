Advanced usage
==============

Comma-separated values
----------------------

Most exact-match filters accept comma-separated values:

.. code-block:: bash

   ehitk hologenomes query --hologenome-id EHI00001,EHI00002
   ehitk mags query --mag-id EHM00001,EHM00002
   ehitk mags query --quality high,medium

Values are matched case-insensitively after trimming surrounding whitespace.

Host lineage matching
---------------------

``--host-lineage`` matches a term against all of these fields:

* ``host_species``
* ``host_genus``
* ``host_family``
* ``host_order``
* ``host_class``

This is useful when you want broad host groups:

.. code-block:: bash

   ehitk specimens query --host-lineage Reptilia
   ehitk hologenomes query --host-lineage Mammalia
   ehitk mags query --host-lineage Aves

Descendant matching
-------------------

EHItk bundles compact descendant maps generated from ENVO and NCBI Taxonomy for
the terms present in the bundled catalog. ENVO identifier filters and NCBI
``--host-taxid`` filters therefore include catalog descendants:

.. code-block:: bash

   ehitk hologenomes query --biome ENVO:01000175
   ehitk specimens query --host-taxid 8509
   ehitk mags query --host-taxid 40674

If a queried identifier is not present in the bundled descendant map, EHItk
falls back to matching the exact value.

Advanced SQL predicates
-----------------------

Power users can add an extra SQL predicate with ``--where``:

.. code-block:: bash

   ehitk mags query --where "completeness >= 90 AND contamination <= 5"
   ehitk hologenomes query --where "latitude > 40 AND longitude < 10"
   ehitk specimens query --where "weight IS NOT NULL"

The predicate is appended to the generated ``WHERE`` clause after validation.
For safety, EHItk rejects predicates containing semicolons, SQL comments, and
mutating SQL keywords such as ``DROP``, ``DELETE``, ``INSERT``, ``UPDATE``,
``ALTER``, ``ATTACH``, and ``PRAGMA``.

Alternate catalogs
------------------

Use ``--db`` to query a custom SQLite catalog:

.. code-block:: bash

   ehitk --db /path/to/ehitk.sqlite hologenomes stats --host-lineage Reptilia

The option can be placed at the top level or on an action command.
The Python API accepts the same catalog path with
``ehitk.Database("/path/to/ehitk.sqlite")``.

This is also how legacy EHI database files from older data releases can be used
after installing a newer EHItk package.
