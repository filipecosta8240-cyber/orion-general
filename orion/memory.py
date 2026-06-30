from __future__ import annotations

import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "MEMORIA"
INDEX_FILE = VAULT_ROOT / "MEMORY_INDEX.json"

@dataclass
class MemoryEntry:
    id: str
    created_at: str
    title: str
    content: str
    tags: Dict[str, str]
    source: str = "orion"
    version: int = 1

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_markdown(self) -> str:
        frontmatter = "---\n"
        for key, value in self.tags.items():
            frontmatter += f"{key}: {value}\n"
        frontmatter += f"source: {self.source}\n"
        frontmatter += f"version: {self.version}\n"
        frontmatter += f"created_at: {self.created_at}\n"
        frontmatter += "---\n\n"
        return f"{frontmatter}# {self.title}\n\n{self.content.strip()}\n"

class ObsidianMemoryBridge:
    def __init__(self, vault_root: Optional[Path] = None):
        self.vault_root = vault_root or VAULT_ROOT
        self.vault_root.mkdir(parents=True, exist_ok=True)
        self.index_file = INDEX_FILE if vault_root is None else self.vault_root / "MEMORY_INDEX.json"
        self.index = self._load_index()
        self._lock = threading.RLock()

    def _load_index(self) -> Dict[str, Dict[str, object]]:
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_index(self) -> None:
        self.index_file.write_text(json.dumps(self.index, indent=2, ensure_ascii=False), encoding="utf-8")

    def _sanitize_filename(self, title: str, entry_id: str) -> str:
        safe_title = re.sub(r"[^\w\- ]+", "", title).strip().replace(" ", "_")
        return f"{entry_id}_{safe_title}.md"

    def write_entry(self, entry: MemoryEntry) -> Path:
        filename = self._sanitize_filename(entry.title, entry.id)
        path = self.vault_root / filename
        path.write_text(entry.to_markdown(), encoding="utf-8")
        with self._lock:
            self.index[entry.id] = entry.to_dict()
            self._save_index()
        return path

    def read_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        record = self.index.get(entry_id)
        if not record:
            return None
        return MemoryEntry(**record)

    def list_entries(self) -> List[MemoryEntry]:
        return [MemoryEntry(**value) for value in self.index.values()]

    def search(self, scope_filters: Dict[str, str]) -> List[MemoryEntry]:
        results = []
        for record in self.index.values():
            tags = record.get("tags", {})
            if all(tags.get(key) == value for key, value in scope_filters.items()):
                results.append(MemoryEntry(**record))
        return results

    def create_entry(self, title: str, content: str, tags: Dict[str, str], source: str = "orion") -> MemoryEntry:
        entry_id = uuid.uuid4().hex[:20]
        entry = MemoryEntry(
            id=entry_id,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            title=title,
            content=content,
            tags=tags,
            source=source,
            version=1,
        )
        self.write_entry(entry)
        return entry
