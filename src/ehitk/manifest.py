from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass(frozen=True)
class ManifestEntry:
    entry_type: str
    genome_id: str
    url: str | None
    path: str | None
    checksum: str | None
    status: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": self.entry_type,
            "genome_id": self.genome_id,
            "url": self.url,
            "path": self.path,
            "checksum": self.checksum,
            "status": self.status,
        }


def append_manifest_entry(manifest_path: str | Path, entry: ManifestEntry) -> None:
    path = Path(manifest_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as handle:
        json.dump(entry.as_dict(), handle, ensure_ascii=True)
        handle.write("\n")

