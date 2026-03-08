"""Earth Hologenome Initiative Toolkit."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import re

__all__ = ["__version__"]


def _version_from_pyproject() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject_path.exists():
        raise PackageNotFoundError("pyproject.toml not found")

    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "([^"]+)"$', content)
    if not match:
        raise PackageNotFoundError("version not found in pyproject.toml")
    return match.group(1)


try:
    __version__ = _version_from_pyproject()
except PackageNotFoundError:
    __version__ = package_version("ehitk")
