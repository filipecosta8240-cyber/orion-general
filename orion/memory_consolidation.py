from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from .memory import MemoryEntry, ObsidianMemoryBridge

logger = logging.getLogger("orion.memory_consolidation")


@dataclass
class ConsolidationReport:
    total_entries: int
    entries_archived: int
    entries_pruned: int
    summaries_created: int
    domain_stats: Dict[str, int]
    archived_ids: List[str] = field(default_factory=list)
    pruned_ids: List[str] = field(default_factory=list)
    summary_ids: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# RELATORIO DE CONSOLIDACAO DE MEMORIA",
            f"**Data:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "",
            f"- Total de entradas: {self.total_entries}",
            f"- Arquivadas: {self.entries_archived}",
            f"- Removidas (redundantes): {self.entries_pruned}",
            f"- Resumos criados: {self.summaries_created}",
            "",
            "## Dominios",
        ]
        for domain, count in sorted(self.domain_stats.items(), key=lambda x: -x[1]):
            lines.append(f"- {domain}: {count} entradas")
        return "\n".join(lines)


class MemoryConsolidationEngine:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self._archive_root = memory.vault_root / "_ARCHIVE"
        self._archive_root.mkdir(exist_ok=True)

    def _get_domain(self, entry: MemoryEntry) -> str:
        return entry.tags.get("domain", entry.tags.get("source", "geral"))

    def _get_age_days(self, entry: MemoryEntry) -> int:
        try:
            created = datetime.fromisoformat(entry.created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            return (now - created).days
        except (ValueError, TypeError):
            return 0

    def _is_redundant(self, entry: MemoryEntry, by_title: Dict[str, List[MemoryEntry]]) -> bool:
        same_title = by_title.get(entry.title, [])
        if len(same_title) < 2:
            return False
        versions = sorted(same_title, key=lambda e: e.version, reverse=True)
        if versions[0].id != entry.id and entry.version < versions[0].version:
            return True
        if len(same_title) > 3 and entry.version == 1:
            return True
        return False

    def _create_summary(self, domain: str, entries: List[MemoryEntry]) -> Optional[MemoryEntry]:
        if len(entries) < 2:
            return None

        titles = [e.title for e in entries[:10]]
        sources = list(set(e.source for e in entries))
        content_parts = [
            f"Dominio: {domain}",
            f"Total de entradas consolidadas: {len(entries)}",
            f"Periodo: {entries[-1].created_at[:10]} a {entries[0].created_at[:10]}",
            "",
            "## Titulos consolidados",
        ]
        for t in titles:
            content_parts.append(f"- {t}")
        content_parts.extend([
            "",
            "## Fontes",
            f"- {', '.join(sources)}",
            "",
            "Esta entrada foi gerada automaticamente pelo motor de consolidacao.",
        ])

        return self.memory.create_entry(
            title=f"CONSOLIDATED | {domain} | {len(entries)} entradas",
            content="\n".join(content_parts),
            tags={
                "domain": "memory_consolidation",
                "priority": "normal",
                "freshness": "consolidated",
                "source_domain": domain,
                "entry_count": str(len(entries)),
            },
            source="consolidation_engine",
        )

    def _archive_entry(self, entry: MemoryEntry) -> bool:
        filename = self.memory._sanitize_filename(entry.title, entry.id)
        source = self.memory.vault_root / filename
        if not source.exists():
            return False
        dest = self._archive_root / filename
        try:
            source.rename(dest)
            return True
        except OSError:
            return False

    def consolidate(self, max_age_days: int = 30, prune_redundant: bool = True) -> ConsolidationReport:
        entries = self.memory.list_entries()
        by_title: Dict[str, List[MemoryEntry]] = defaultdict(list)
        by_domain: Dict[str, List[MemoryEntry]] = defaultdict(list)

        for e in entries:
            by_title[e.title].append(e)
            by_domain[self._get_domain(e)].append(e)

        archived_ids: List[str] = []
        pruned_ids: List[str] = []
        summary_ids: List[str] = []
        domain_stats: Dict[str, int] = {}

        if prune_redundant:
            for entry in entries:
                if self._is_redundant(entry, by_title):
                    if self._archive_entry(entry):
                        pruned_ids.append(entry.id)
                        logger.info("Entrada redundante arquivada: %s", entry.title)

        for domain, domain_entries in by_domain.items():
            old_entries = [e for e in domain_entries if self._get_age_days(e) > max_age_days]
            if len(old_entries) > 2:
                summary = self._create_summary(domain, old_entries)
                if summary:
                    summary_ids.append(summary.id)
                    for e in old_entries:
                        if e.id not in pruned_ids and self._archive_entry(e):
                            archived_ids.append(e.id)
                            logger.info("Entrada antiga arquivada: %s", e.title)

        remaining = self.memory.list_entries()
        for e in remaining:
            domain = self._get_domain(e)
            domain_stats[domain] = domain_stats.get(domain, 0) + 1

        report = ConsolidationReport(
            total_entries=len(entries),
            entries_archived=len(archived_ids),
            entries_pruned=len(pruned_ids),
            summaries_created=len(summary_ids),
            domain_stats=domain_stats,
            archived_ids=archived_ids,
            pruned_ids=pruned_ids,
            summary_ids=summary_ids,
        )

        logger.info(
            "Consolidacao concluida: %d total, %d arquivadas, %d removidas, %d resumos",
            report.total_entries, report.entries_archived, report.entries_pruned, report.summaries_created
        )

        return report

    def get_memory_health(self) -> Dict[str, object]:
        entries = self.memory.list_entries()
        by_domain: Dict[str, int] = defaultdict(int)
        by_age: Dict[str, int] = defaultdict(int)
        total_size = 0

        for e in entries:
            domain = self._get_domain(e)
            by_domain[domain] += 1
            total_size += len(e.content)
            age = self._get_age_days(e)
            if age < 7:
                by_age["ultimos_7_dias"] += 1
            elif age < 30:
                by_age["ultimos_30_dias"] += 1
            elif age < 90:
                by_age["ultimos_90_dias"] += 1
            else:
                by_age["mais_de_90_dias"] += 1

        return {
            "total_entries": len(entries),
            "total_size_chars": total_size,
            "domains": dict(by_domain),
            "age_distribution": dict(by_age),
            "avg_content_length": total_size // max(len(entries), 1),
        }
