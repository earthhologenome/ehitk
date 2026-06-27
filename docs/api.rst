Python API
==========

EHItk can be used directly from Python through ``ehitk.Database``. The Python
API uses the same bundled SQLite catalog and filter semantics as the command
line interface, but returns structured Python objects instead of rendered
tables.

Basic usage
-----------

.. code-block:: python

   import ehitk

   with ehitk.Database() as ehidb:
       mags = ehidb.mags.query(
           quality="high",
           host_taxid=40674,
           columns=(
               "mag_id",
               "quality",
               "mag_family",
               "mag_genus",
               "host_taxid",
               "host_species",
           ),
       )

   for mag in mags:
       print(
           mag.mag_id,
           mag.quality,
           mag.mag_family,
           mag.mag_genus,
           mag.host_taxid,
           mag.host_species,
       )

Use an alternate catalog by passing a path:

.. code-block:: python

   with ehitk.Database("/path/to/another/db.sqlite") as ehidb:
       specimens = ehidb.specimens.query(host_species="Podarcis muralis", limit=10)

Collections
-----------

``Database`` exposes one collection per EHI data level:

``ehidb.specimens``
   Host and specimen metadata.

``ehidb.hologenomes``
   Shotgun sequencing datasets linked to specimens.

``ehidb.mags``
   Metagenome-assembled genomes linked to parent hologenomes and specimens.

Each collection supports ``query()``, ``values()``, and ``stats()``. The
``hologenomes`` and ``mags`` collections also support ``fetch()``.

Query records
-------------

``query()`` returns typed dataclass records: ``Specimen``, ``Hologenome``, or
``Mag``. Filters are passed as keyword arguments using the same names as CLI
options, with underscores instead of hyphens.

.. code-block:: python

   with ehitk.Database() as ehidb:
       specimens = ehidb.specimens.query(
           host_lineage="Reptilia",
           weight_min=10,
           limit=5,
       )
       hologenomes = ehidb.hologenomes.query(
           country="Denmark",
           biome_envo_id="ENVO:01000175",
           data_min=1.0,
           columns=("hologenome_id", "biome_envo_id", "biome_name", "country", "data_gb"),
       )
       mags = ehidb.mags.query(
           quality=("high", "medium"),
           species="Escherichia coli",
           limit=20,
       )

Filter values may be strings, numbers, or sequences. Sequence values are treated
like comma-separated CLI filter values.
ENVO identifier filters and NCBI ``host_taxid`` filters include catalog
descendants when those descendants are present in the bundled hierarchy
resources.

Values and stats
----------------

``values()`` counts distinct field values after applying filters:

.. code-block:: python

   with ehitk.Database() as ehidb:
       countries = ehidb.hologenomes.values("country", host_lineage="Reptilia")

   for row in countries.rows:
       print(row.value, row.count)

``stats()`` returns a ``TargetStats`` object with a raw ``summary`` dictionary
and named breakdown tables:

.. code-block:: python

   with ehitk.Database() as ehidb:
       stats = ehidb.mags.stats(quality="high")

   print(stats.summary["matched_mags"])
   for breakdown in stats.breakdowns:
       print(breakdown.title, breakdown.rows)

Fetching data
-------------

``fetch()`` is available for hologenomes and MAGs. It can download files
immediately or write a shell script with ``curl`` commands when ``batch`` is
provided. The method returns a ``FetchSummary`` object.

.. code-block:: python

   with ehitk.Database() as ehidb:
       summary = ehidb.mags.fetch(
           country="Denmark",
           output_dir="downloads",
           batch="download-mags.sh",
       )

   print(summary.matched_count, summary.queued_count, summary.batch_script)

Working with pandas
-------------------

Because ``query()`` returns lists of dataclass records, the results drop
straight into a `pandas <https://pandas.pydata.org/>`_ ``DataFrame`` with no
conversion code: ``pandas.DataFrame`` understands a list of dataclasses and
turns each field into a column.

.. code-block:: python

   import ehitk
   import pandas as pd

   with ehitk.Database() as ehidb:
       mags = ehidb.mags.query(quality="high", host_taxid=40674)

   frame = pd.DataFrame(mags)
   print(frame[["mag_id", "quality", "completeness", "mag_genus"]].head())

The same pattern works for the ``rows`` of a ``values()`` result and for the
``rows`` of each ``stats()`` breakdown:

.. code-block:: python

   with ehitk.Database() as ehidb:
       countries = ehidb.hologenomes.values("country", host_lineage="Reptilia")
       stats = ehidb.mags.stats(quality="high")

   country_counts = pd.DataFrame(countries.rows)            # columns: value, count
   quality_breakdown = pd.DataFrame(stats.breakdowns[0].rows)

A few notes:

* A record carries every field of its dataclass even when you restrict the
  query with ``columns``; the columns you did not request are present in the
  ``DataFrame`` with ``None`` values. Subset the frame afterwards (for example
  ``frame[list(columns)]``) when you want only the requested columns.
* The ``weight`` and ``length`` specimen measurements are tuples of values, so
  they appear as object-dtype columns holding Python tuples. Use
  ``frame.explode("weight")`` if you need one row per measurement.

``pandas`` is not a dependency of EHItk; install it separately (``pip install
pandas``) to use these examples.

Advanced SQL predicates
-----------------------

The ``where`` argument accepts the same validated SQL predicate fragments as
the CLI ``--where`` option:

.. code-block:: python

   with ehitk.Database() as ehidb:
       mags = ehidb.mags.query(where="completeness >= 95", limit=10)
