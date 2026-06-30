from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("orion.data_retention")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
RETENTION_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "DATA_RETENTION"


@dataclass
class RetentionRule:
    name: str
    path: Path
    max_age_days: int
    file_pattern: str = "*.json"
    keep_latest: int = 0
    enabled: bool = True
    last_cleanup: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {k: str(v) if isinstance(v, Path) else v for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> RetentionRule:
        data = data.copy()
        if "path" in data:
            data["path"] = Path(str(data["path"]))
        return cls(**data)


@dataclass
class CleanupReport:
    timestamp: str
    rules_run: int = 0
    files_deleted: int = 0
    bytes_freed: int = 0
    errors: List[str] = field(default_factory=list)
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class DataRetentionManager:
    """Manages data lifecycle with TTL-based cleanup rules."""

    def __init__(self, root: Optional[Path] = None):
        self.root = root or RETENTION_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self._rules: List[RetentionRule] = []
        self._cleanup_hooks: Dict[str, Callable] = {}
        self._load()
        self._register_default_rules()

    def _load(self) -> None:
        rules_file = self.root / "rules.json"
        if rules_file.exists():
            try:
                data = json.loads(rules_file.read_text(encoding="utf-8"))
                self._rules = [RetentionRule.from_dict(r) for r in data]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save(self) -> None:
        rules_file = self.root / "rules.json"
        data = [r.to_dict() for r in self._rules]
        rules_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _register_default_rules(self) -> None:
        base = _PROJECT_ROOT / "ORION_SYSTEM"
        defaults = [
            RetentionRule(
                name="audit_trail",
                path=base / "AUDIT_TRAIL",
                max_age_days=90,
                file_pattern="audit.json",
                keep_latest=500,
            ),
            RetentionRule(
                name="performance_metrics",
                path=base / "PERFORMANCE_METRICS",
                max_age_days=60,
                file_pattern="metrics.json",
                keep_latest=500,
            ),
            RetentionRule(
                name="episodic_memory",
                path=base / "EPISODIC_MEMORY",
                max_age_days=90,
                file_pattern="episodes.json",
                keep_latest=500,
            ),
            RetentionRule(
                name="prospective_memory",
                path=base / "PROSPECTIVE_MEMORY",
                max_age_days=30,
                file_pattern="intentions.json",
                keep_latest=200,
            ),
            RetentionRule(
                name="backups",
                path=base / "BACKUPS",
                max_age_days=30,
                keep_latest=7,
            ),
            RetentionRule(
                name="idle_logs",
                path=base / "IDLE_PROCESSOR",
                max_age_days=30,
                file_pattern="results.json",
                keep_latest=200,
            ),
            RetentionRule(
                name="memory_guard",
                path=base / "MEMORY_GUARD",
                max_age_days=60,
                file_pattern="threats.json",
                keep_latest=200,
            ),
            RetentionRule(
                name="reflections",
                path=base / "REFLECTIONS",
                max_age_days=180,
                file_pattern="*.json",
            ),
        ]
        for rule in defaults:
            if not any(r.name == rule.name for r in self._rules):
                self._rules.append(rule)
                rule.path.mkdir(parents=True, exist_ok=True)
        self._save()

    def add_rule(self, name: str, path: Path, max_age_days: int,
                 file_pattern: str = "*.json", keep_latest: int = 0) -> RetentionRule:
        rule = RetentionRule(
            name=name,
            path=path,
            max_age_days=max_age_days,
            file_pattern=file_pattern,
            keep_latest=keep_latest,
        )
        self._rules.append(rule)
        self._save()
        return rule

    def register_cleanup_hook(self, name: str, hook: Callable) -> None:
        self._cleanup_hooks[name] = hook

    def run_cleanup(self, rule_name: Optional[str] = None) -> CleanupReport:
        report = CleanupReport(
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        rules = [r for r in self._rules if r.enabled]
        if rule_name:
            rules = [r for r in rules if r.name == rule_name]
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)

        for rule in rules:
            report.rules_run += 1
            try:
                self._cleanup_rule(rule, report)
                rule.last_cleanup = report.timestamp

                hook = self._cleanup_hooks.get(rule.name)
                if hook:
                    try:
                        hook()
                    except Exception as e:
                        logger.warning("Hook %s falhou: %s", rule.name, e)

            except Exception as e:
                msg = f"Regra '{rule.name}': {e}"
                report.errors.append(msg)
                logger.error(msg)

        self._save()
        logger.info("Cleanup concluido: %d regras, %d ficheiros (%d bytes)", 
                     report.rules_run, report.files_deleted, report.bytes_freed)
        return report

    def _cleanup_rule(self, rule: RetentionRule, report: CleanupReport) -> None:
        if not rule.path.exists():
            return

        if rule.file_pattern == "*":
            items = sorted(rule.path.iterdir(), key=lambda p: p.stat().st_mtime)
        else:
            items = sorted(rule.path.glob(rule.file_pattern), key=lambda p: p.stat().st_mtime)

        if rule.keep_latest > 0 and len(items) > rule.keep_latest:
            to_delete = items[:-rule.keep_latest]
            for item in to_delete:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    report.files_deleted += 1
                    report.bytes_freed += size
                    report.details.append(f"{rule.name}: removido {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    report.details.append(f"{rule.name}: removida pasta {item.name}")

        cutoff = datetime.now(timezone.utc) - timedelta(days=rule.max_age_days)
        for item in items:
            if item.is_file():
                mtime = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    size = item.stat().st_size
                    item.unlink()
                    report.files_deleted += 1
                    report.bytes_freed += size

    def get_stats(self) -> Dict[str, object]:
        total = len(self._rules)
        enabled = sum(1 for r in self._rules if r.enabled)
        return {
            "total_rules": total,
            "enabled_rules": enabled,
            "rules": [
                {
                    "name": r.name,
                    "max_age_days": r.max_age_days,
                    "keep_latest": r.keep_latest,
                    "enabled": r.enabled,
                    "last_cleanup": r.last_cleanup,
                }
                for r in self._rules
            ],
        }
