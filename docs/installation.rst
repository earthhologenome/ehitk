Installation
============

Requirements
------------

EHItk requires Python 3.10 or newer.

Install from PyPI
-----------------

.. code-block:: bash

   pip install ehitk

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

Database updates are paired with documented EHI data releases. Older legacy
database files are archived with those data releases so analyses can be rerun
against the same catalog version.

EHItk package versions follow Semantic Versioning for the software interface.
Database updates that change the SQLite schema, remove or rename fields, or
otherwise alter command-line or Python API output compatibility are treated as
breaking changes and require a major version bump. Non-breaking database
additions or metadata corrections are released as minor or patch versions and
are documented in the changelog and associated data release notes.

Use ``--db`` when you want to query a specific SQLite catalog:

.. code-block:: bash

   ehitk --db /path/to/ehitk.sqlite --help
   ehitk hologenomes query --db /path/to/ehitk.sqlite --limit 5
