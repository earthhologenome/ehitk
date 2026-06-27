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

Each EHItk release also produces a standalone SQLite artifact named
``ehitk-database-<version>.sqlite`` with a matching ``.sha256`` checksum file.
Those database artifacts are intended for long-term reproducibility and for
users who want to pin the metadata catalog independently of their installed
Python package.

Database artifacts are attached to the corresponding GitHub release and are
deposited in Zenodo as citable EHI data releases. The citable Zenodo database
record is available at https://doi.org/10.5281/zenodo.20430293, with the current
record page at https://zenodo.org/records/20430294. The same SQLite file is also
included inside the matching EHItk Python package for convenience.

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

EHItk package versions follow Semantic Versioning for the software interface.
Database updates that change the SQLite schema, remove or rename fields, or
otherwise alter command-line or Python API output compatibility are treated as
breaking changes and require a major version bump. Non-breaking database
additions or metadata corrections are released as minor or patch versions and
are documented in the changelog and associated data release notes.
