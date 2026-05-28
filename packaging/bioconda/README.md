# Bioconda recipe

This directory contains the EHItk Bioconda recipe prepared for submission to
the `bioconda-recipes` repository.

To submit or update the package in Bioconda, copy `meta.yaml` to:

```text
bioconda-recipes/recipes/ehitk/meta.yaml
```

The recipe packages the PyPI source distribution as a pure Python `noarch`
package, installs the `ehitk` console entry point, and smoke-tests both the
Python import and command-line interface. After the Bioconda pull request is
merged, BioContainers should automatically build and publish the matching
container image from the Bioconda package.
