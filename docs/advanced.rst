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
