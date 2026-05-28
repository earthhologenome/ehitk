EHItk documentation
====================

The Earth Hologenome Initiative ToolKit (EHItk) is a command-line tool for
finding, summarizing, exporting, and downloading EHI specimen, hologenome, and
metagenome-assembled genome (MAG) records.

EHItk is organized around three data levels:

* ``specimens`` for host and specimen metadata.
* ``hologenomes`` for shotgun metagenomic sequencing datasets.
* ``mags`` for metagenome-assembled genomes linked to parent hologenomes.

Each level uses the same action pattern where possible: ``query`` returns
matching records, ``values`` counts distinct field values, ``stats`` summarizes
matching records, and ``fetch`` downloads files for hologenomes and MAGs.

Quick example
-------------

.. code-block:: bash

   ehitk specimens query --host-species "Podarcis muralis" --limit 5
   ehitk hologenomes query --host-lineage Reptilia --columns hologenome_id,host_species,data_gb
   ehitk mags stats --quality high --species "Escherichia coli"

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   commands
   specimens
   hologenomes
   mags
   outputs
   fetching
   advanced
