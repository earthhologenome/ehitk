Database catalog
================

EHItk uses a SQLite catalog for specimen, hologenome, and MAG metadata. The
installed package includes a bundled catalog so the command-line interface and
Python API work immediately, including offline and in workflow environments.

Bundled default
---------------

By default, EHItk queries the catalog bundled with the installed package
version. Updating EHItk may therefore update the default metadata catalog:

.. code-block:: bash

   python -m pip install --upgrade ehitk
   ehitk database

The ``ehitk database`` command reports the catalog path, whether the bundled or
a custom catalog is being used, the file size, and the SHA256 checksum.

Versioned catalog releases
--------------------------

The catalog is released as a standalone SQLite artifact named
``ehitk-database-<data_version>.sqlite`` (a calendar ``YYYY.MM.DD`` version) with
a matching ``.sha256`` checksum file. Those database artifacts are intended for
long-term reproducibility and for users who want to pin the metadata catalog
independently of their installed Python package.

The standalone artifact and its Zenodo deposit are produced by the separate
``ehitk-build`` data generator (the producer of the catalog), while each EHItk
Python release bundles a snapshot of the same catalog for convenience. Database
artifacts are attached to a GitHub release and deposited in Zenodo as citable EHI
data releases, under a database concept DOI that is distinct from the software
DOI. The citable Zenodo database record is available at
https://doi.org/10.5281/zenodo.20430293, with the current record page at
https://zenodo.org/records/20430294.

The published database versions (this table is generated from Zenodo by
``scripts/update_db_list.py``):

.. db-list-start

No published database versions found.

.. db-list-end

Embedded descendant hierarchy
-----------------------------

ENVO biome and NCBI host-taxon filters expand to include catalog descendants.
The descendant maps that drive this expansion are stored as two auxiliary tables
inside the SQLite catalog itself, ``envo_descendants`` and
``host_taxon_descendants`` (each with ``ancestor`` and ``descendant`` columns).
Keeping the hierarchy in the same file as the data it describes guarantees that a
pinned or custom catalog used via ``--db`` always expands filters with its own
ENVO and taxonomy snapshot, rather than with whatever metadata happens to ship
with the installed package. When a catalog predates these tables, EHItk falls
back to the descendant maps bundled with the package.

Use a pinned catalog with the global ``--db`` option:

.. code-block:: bash

   ehitk --db /path/to/ehitk-database-1.1.3.sqlite hologenomes stats

The Python API accepts the same path:

.. code-block:: python

   import ehitk

   with ehitk.Database("/path/to/ehitk-database-1.1.3.sqlite") as database:
       records = database.hologenomes.query(limit=5)

Catalog provenance
------------------

The SQLite catalog is a curated EHI metadata product prepared during EHItk
release preparation. The source tree contains the current bundled snapshot at
``src/ehitk/data/ehitk.sqlite`` so source builds and editable installs behave
like packaged installs. Historical catalog snapshots should be obtained from
the versioned release artifacts rather than from old source checkouts.

The public EHItk package does not currently provide an end-user command that
rebuilds the full curated catalog from upstream metadata sources. Fresh
catalogs are made available through EHItk package releases and the separate
database release artifacts.

Versioning policy
-----------------

EHItk separates the software it ships from the data it ships, and tracks four
independent-but-linked version lines:

``ehitk`` package version
   Semantic Versioning for the Python software interface (CLI and API). A new
   ``ehitk`` release may bundle a newer catalog snapshot, so upgrading the
   package can also update the default metadata.

``data_version``
   A **calendar version** (``YYYY.MM.DD``) identifying a regeneration of the
   metadata catalog from the upstream Airtable sources. This is the version that
   the citable database releases and the Zenodo deposits track, independently of
   the ``ehitk`` package version. The standalone database artifacts are named
   ``ehitk-database-<data_version>.sqlite``.

``schema_version``
   An **integer contract** between the catalog and the code that reads it. It
   describes the structural layout of the catalog (its tables, columns, and the
   auxiliary ontology tables). It only changes when the schema changes in a way
   that breaks that contract, which forces a coordinated software release that
   understands the new layout. A given ``ehitk`` release supports a known set of
   ``schema_version`` values and reports a clear error when asked to open a
   catalog outside that range.

``ehitk-build`` version
   Semantic Versioning for the separate generator that builds the catalog. It is
   recorded inside each catalog as provenance and does not affect how ``ehitk``
   reads the data.

Database updates that change the SQLite schema, remove or rename fields, or
otherwise alter command-line or Python API output compatibility are treated as
breaking changes: they bump ``schema_version`` and require a coordinated
``ehitk`` release (a major version bump where output compatibility is affected).
Non-breaking database additions or metadata corrections bump ``data_version``
only and are released as minor or patch ``ehitk`` versions, documented in the
changelog and associated data release notes.

The end-to-end release procedure that coordinates these version lines across the
``ehitk`` and ``ehitk-build`` repositories is documented in the cross-repo
runbook at ``RELEASING.md`` in the repository root.
