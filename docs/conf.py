from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ehitk import __version__

project = "EHItk"
author = "Earth Hologenome Initiative"
copyright = "2026, Earth Hologenome Initiative"
release = __version__
version = __version__

extensions = [
    "sphinx.ext.autodoc",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_logo = "ehitk_logo.png"
html_static_path = []
html_title = "EHItk documentation"

autodoc_typehints = "description"
