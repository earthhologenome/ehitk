Command model
=============

EHItk commands have the form:

.. code-block:: text

   ehitk [global options] <resource> <action> [action options]

Resources
---------

``specimens``
   Host and specimen metadata. This resource supports ``fields``, ``query``,
   ``values``, and ``stats``.

``hologenomes``
   Shotgun sequencing datasets linked to specimens. This resource supports
   ``fields``, ``query``, ``values``, ``stats``, and ``fetch``.

``mags``
   Metagenome-assembled genomes linked to parent hologenomes and host
   specimens. This resource supports ``fields``, ``query``, ``values``,
   ``stats``, and ``fetch``.

``database``
   Show the SQLite catalog currently used by EHItk: whether it is the bundled
   catalog or an alternate catalog passed with ``--db``, its path, size, SHA256
   checksum, and its ``data_version`` / ``schema_version`` (``unknown`` for older
   catalogs built before this metadata existed).

Actions
-------

``fields``
   Lists the field names accepted by ``values --field``, including aliases and
   the canonical field each alias resolves to.

``query``
   Prints matching records as a rich table by default, or emits CSV/TSV to
   standard output or ``--output-file``.

``values``
   Counts distinct values for one field after applying the same filters used by
   ``query``.

``stats``
   Prints a compact summary of a filtered subset.

``fetch``
   Downloads files for matching hologenomes or MAGs, or writes a batch shell
   script with ``curl`` commands.

Global options
--------------

``--version``
   Show the installed EHItk version and exit.

``--db PATH``
   Use an alternate SQLite catalog instead of the bundled database.

Help
----

All command levels include help text:

.. code-block:: bash

   ehitk --help
   ehitk specimens --help
   ehitk hologenomes --help
   ehitk mags --help
   ehitk mags query --help
