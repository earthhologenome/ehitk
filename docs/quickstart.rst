Quick start
===========

Start with ``query`` when you want rows, ``values`` when you want to discover
available filter values, and ``stats`` when you want a summary of a subset.

Python API
----------

Use ``ehitk.Database`` when you want typed Python objects instead of CLI output.

.. code-block:: python

   import ehitk

   with ehitk.Database() as ehidb:
       mags = ehidb.mags.query(quality="high", host_taxid=40674, limit=5)
       countries = ehidb.hologenomes.values("country", host_lineage="Reptilia")

   for mag in mags:
       print(mag.mag_id, mag.quality, mag.host_species)

Inspect specimen metadata
-------------------------

.. code-block:: bash

   ehitk specimens query --host-species "Podarcis muralis" --limit 5
   ehitk specimens values --field host_species --limit 10
   ehitk specimens stats --host-lineage Reptilia

Find hologenome datasets
------------------------

.. code-block:: bash

   ehitk hologenomes query --host-species "Podarcis muralis" --limit 5
   ehitk hologenomes query --biome ENVO:01000175 --limit 5
   ehitk hologenomes values --field country --limit 10
   ehitk hologenomes stats --host-lineage Reptilia

Find MAGs
---------

.. code-block:: bash

   ehitk mags query --genus Escherichia --limit 5
   ehitk mags values --field quality
   ehitk mags stats --quality high --species "Escherichia coli"

Download data
-------------

Fetch commands can download immediately or write shell scripts for later
execution.

.. code-block:: bash

   ehitk hologenomes fetch --host-lineage Reptilia --limit 1
   ehitk hologenomes fetch --host-lineage Reptilia --limit 1 --batch hologenomes.sh
   ehitk mags fetch --species "Escherichia coli" --limit 1
   ehitk mags fetch --species "Escherichia coli" --limit 1 --batch mags.sh

Use help at any level
---------------------

.. code-block:: bash

   ehitk --help
   ehitk specimens --help
   ehitk specimens query --help
   ehitk hologenomes fetch --help
   ehitk mags values --help
