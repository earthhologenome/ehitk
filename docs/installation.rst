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

Use ``--db`` when you want to query a specific SQLite catalog:

.. code-block:: bash

   ehitk --db /path/to/ehitk.sqlite --help
   ehitk hologenomes query --db /path/to/ehitk.sqlite --limit 5
