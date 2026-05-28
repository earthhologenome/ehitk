Identifier namespaces
=====================

EHItk keeps identifier columns in the same namespace used by the bundled EHI
catalog or by the external authority that minted the identifier. The table
below lists the identifier fields that can appear in query output or be used in
filters, together with their namespace and a manual resolution route.

.. list-table::
   :header-rows: 1
   :widths: 18 24 34 24

   * - Field
     - Namespace
     - Meaning
     - Manual resolution
   * - ``specimen_id``
     - EHI specimen catalog
     - EHI specimen metadata identifier, for example ``SD00508``.
     - Resolve inside the EHItk catalog with ``ehitk specimens query
       --specimen-id SD00508``.
   * - ``hologenome_id``
     - EHI hologenome catalog
     - EHI shotgun metagenomic dataset identifier, for example ``EHI00001``.
     - Resolve inside the EHItk catalog with ``ehitk hologenomes query
       --hologenome-id EHI00001``.
   * - ``mag_id``
     - EHI MAG catalog
     - EHI metagenome-assembled genome identifier, for example ``EHM00001``.
     - Resolve inside the EHItk catalog with ``ehitk mags query --mag-id
       EHM00001``.
   * - ``host_taxid``
     - NCBI Taxonomy
     - NCBI taxon identifier for the host organism, for example ``8509``.
     - Resolve at ``https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=8509``.
   * - ``biome_envo_id``
     - Environment Ontology (ENVO)
     - ENVO class identifier for the sampled biome, for example
       ``ENVO:01000175``.
     - Resolve at ``https://purl.obolibrary.org/obo/ENVO_01000175``.
   * - ``release`` and ``hologenome_release``
     - EHI data release labels
     - EHI catalog release labels used to group records.
     - Resolve inside EHItk with ``--release`` filters or by pinning the
       corresponding versioned SQLite catalog.
   * - ``url``, ``url1``, and ``url2``
     - Absolute download URLs
     - MAG FASTA or paired-end read download locations.
     - Resolve directly with the URL. Hologenome read URLs commonly include the
       sequencing run accession in the path.

Catalog-local identifiers
-------------------------

``specimen_id``, ``hologenome_id``, and ``mag_id`` are EHI catalog identifiers.
They are stable within a versioned EHItk database artifact, and can be resolved
by querying that catalog with the matching resource command. They are not NCBI,
ENA, BioSample, BioProject, SRA, or INSDC accessions unless a separate output
field explicitly provides such an accession.

External ontology and taxonomy identifiers
------------------------------------------

``host_taxid`` values are NCBI Taxonomy identifiers. ``biome_envo_id`` values
are ENVO CURIEs. EHItk expands these filters to include descendants present in
the bundled catalog, so a higher-level NCBI or ENVO identifier may match records
whose stored value is a descendant identifier.

Taxonomy names
--------------

Fields such as ``host_species``, ``host_genus``, ``mag_genus``, and
``mag_species`` are names or labels, not identifier fields. MAG taxonomy labels
come from GTDB-style MAG assignments; EHItk normalizes ``g__`` and ``s__``
prefixes in query output and filters, but it does not infer NCBI taxon
identifiers for MAG taxa.
