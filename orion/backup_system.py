from __future__ import annotations

import json
import logging
import shutil
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .memory import ObsidianMemoryBridge

logger = logging.getLogger("orion.backup")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "BACKUPS"


@dataclass
class BackupManifest:
    id: str
    created_at: str
    entry_count: int
    total_size_bytes: int
    description: str
    includes: Dict[str, bool]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class BackupSystem:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self._root = BACKUP_ROOT
        self._root.mkdir(parents=True, exist_ok=True)

    def _new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def create_backup(self, description: str = "") -> Optional[str]:
        backup_id = self._new_id()
        backup_dir = self._root / backup_id
        backup_dir.mkdir(exist_ok=True)

        try:
            memory_zip = backup_dir / "memory.zip"
            with zipfile.ZipFile(memory_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for md_file in self.memory.vault_root.glob("*.md"):
                    zf.write(md_file, f"memory/{md_file.name}")
                index_file = self.memory.vault_root / "MEMORY_INDEX.json"
                if index_file.exists():
                    zf.write(index_file, "memory/MEMORY_INDEX.json")

            entries = self.memory.list_entries()
            total_size = sum(len(e.content) for e in entries)

            manifest = BackupManifest(
                id=backup_id,
                created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                entry_count=len(entries),
                total_size_bytes=total_size,
                description=description,
                includes={"memory": True, "skills": False, "reflections": False, "knowledge_graph": False},
            )

            for subdir_name in ["SKILLS", "REFLECTIONS", "KNOWLEDGE_GRAPH", "PLANS"]:
                subdir = self.memory.vault_root.parent / subdir_name
                if subdir.exists():
                    sub_zip = backup_dir / f"{subdir_name.lower()}.zip"
                    with zipfile.ZipFile(sub_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                        for item in subdir.rglob("*"):
                            if item.is_file():
                                zf.write(item, f"{subdir_name}/{item.relative_to(subdir)}")
                    manifest.includes[subdir_name.lower()] = True

            manifest_file = backup_dir / "manifest.json"
            manifest_file.write_text(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

            logger.info("Backup criado: %s (%d entradas, %d bytes)", backup_id, len(entries), total_size)
            return backup_id

        except Exception as e:
            logger.error("Erro ao criar backup: %s", e)
            shutil.rmtree(backup_dir, ignore_errors=True)
            return None

    def restore_backup(self, backup_id: str) -> bool:
        backup_dir = self._root / backup_id
        if not backup_dir.exists():
            logger.error("Backup não encontrado: %s", backup_id)
            return False

        try:
            manifest_file = backup_dir / "manifest.json"
            if manifest_file.exists():
                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            else:
                manifest_data = {}

            memory_zip = backup_dir / "memory.zip"
            if memory_zip.exists():
                with zipfile.ZipFile(memory_zip, "r") as zf:
                    zf.extractall(self.memory.vault_root.parent)

            logger.info("Backup restaurado: %s", backup_id)
            return True

        except Exception as e:
            logger.error("Erro ao restaurar backup: %s", e)
            return False

    def list_backups(self) -> List[Dict[str, object]]:
        backups = []
        for backup_dir in sorted(self._root.iterdir(), reverse=True):
            if backup_dir.is_dir():
                manifest_file = backup_dir / "manifest.json"
                if manifest_file.exists():
                    try:
                        data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        backups.append(data)
                    except (json.JSONDecodeError, TypeError):
                        backups.append({"id": backup_dir.name, "created_at": "unknown"})
                else:
                    backups.append({"id": backup_dir.name, "created_at": "unknown"})
        return backups

    def delete_backup(self, backup_id: str) -> bool:
        backup_dir = self._root / backup_id
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
            logger.info("Backup eliminado: %s", backup_id)
            return True
        return False

    def get_latest_backup(self) -> Optional[Dict[str, object]]:
        backups = self.list_backups()
        return backups[0] if backups else None
