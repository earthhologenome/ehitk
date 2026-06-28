Installation
============

Requirements
------------

EHItk requires Python 3.10 or newer.

Install from PyPI
-----------------

.. code-block:: bash

   pip install ehitk

Bioconda recipe and BioContainers
---------------------------------

A Bioconda recipe is maintained in ``packaging/bioconda`` for submission to the
``bioconda`` channel. After the Bioconda pull request is merged, EHItk can be
installed from conda-compatible workflow environments with:

.. code-block:: bash

   mamba install -c conda-forge -c bioconda ehitk

The corresponding BioContainers image is expected to be generated automatically
from the accepted Bioconda package and listed under
``quay.io/biocontainers/ehitk``.

Install the latest development version
--------------------------------------

Use the GitHub version only when you need changes that have not yet been
released to PyPI.

.. code-block:: bash

   pip install git+https://github.com/earthhologenome/ehitk

Check the installation
----------------------

.. code-block:: bash

   ehitk --version
   ehitk --help

Database selection
------------------

By default, EHItk uses the bundled SQLite catalog that ships with the installed
package version. Package updates therefore update the default catalog.

Use ``ehitk database`` to inspect the catalog currently in use, including its
path, source, size, SHA256 checksum, and its ``data_version`` / ``schema_version``
(shown as ``unknown`` for older catalogs built before this metadata existed).

Database updates are paired with documented EHI data releases. Each release
produces a standalone ``ehitk-database-<data_version>.sqlite`` artifact (a
calendar ``YYYY.MM.DD`` version) and checksum file, deposited on Zenodo and
attached to a GitHub Release, while the same SQLite file remains bundled inside
the matching Python package for convenience. Older database files can be used to
rerun analyses against the same catalog version. See the
:doc:`database catalog <database>` page for the published versions and the full
versioning policy.

The public package does not rebuild the curated EHI metadata catalog from
upstream sources; that is done by the separate ``ehitk-build`` generator. Fresh
catalogs are obtained by upgrading EHItk or by downloading the versioned database
artifact for a specific release.

EHItk package versions follow Semantic Versioning for the software interface.
Database updates that change the SQLite schema in a way that breaks the
command-line or Python API output contract bump the catalog's ``schema_version``
and require a coordinated (major) EHItk release; EHItk validates ``schema_version``
when it opens a catalog and reports a clear error on mismatch. Non-breaking
database additions or metadata corrections bump the ``data_version`` only and are
released as minor or patch versions, documented in the changelog and associated
data release notes.

Use ``--db`` when you want to query a specific SQLite catalog:

.. code-block:: bash

   ehitk --db /path/to/ehitk.sqlite --help
   ehitk hologenomes query --db /path/to/ehitk.sqlite --limit 5
