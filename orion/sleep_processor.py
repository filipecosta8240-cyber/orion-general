from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .memory import ObsidianMemoryBridge
from .memory_consolidation import MemoryConsolidationEngine, ConsolidationReport
from .skill_crystallizer import SkillCrystallizer, CrystallizationReport

logger = logging.getLogger("orion.sleep_processor")


@dataclass
class SleepReport:
    timestamp: str
    consolidation: Optional[ConsolidationReport] = None
    crystallization: Optional[CrystallizationReport] = None
    memory_health: Dict[str, object] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_markdown(self) -> str:
        lines = [
            "# RELATORIO DE PROCESSAMENTO NOTURNO",
            f"**Data:** {self.timestamp}",
            f"**Duracao:** {self.duration_seconds:.1f}s",
            "",
        ]
        if self.errors:
            lines.append("## Erros")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")

        if self.consolidation:
            c = self.consolidation
            lines.extend([
                "## Consolidacao de Memoria",
                f"- Total: {c.total_entries} entradas",
                f"- Arquivadas: {c.entries_archived}",
                f"- Removidas: {c.entries_pruned}",
                f"- Resumos: {c.summaries_created}",
                "",
            ])

        if self.crystallization:
            s = self.crystallization
            lines.extend([
                "## Cristalizacao de Skills",
                f"- Criadas: {s.skills_created}",
                f"- Atualizadas: {s.skills_updated}",
                f"- Total: {s.total_skills}",
                "",
            ])

        if self.memory_health:
            h = self.memory_health
            lines.extend([
                "## Saude da Memoria",
                f"- Total entradas: {h.get('total_entries', 0)}",
                f"- Tamanho total: {h.get('total_size_chars', 0)} chars",
                f"- Media por entrada: {h.get('avg_content_length', 0)} chars",
                "",
            ])
            age = h.get("age_distribution", {})
            if age:
                lines.append("### Distribuicao por idade")
                for label, count in age.items():
                    lines.append(f"- {label}: {count}")
                lines.append("")

            domains = h.get("domains", {})
            if domains:
                lines.append("### Dominios ativos")
                for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:10]:
                    lines.append(f"- {domain}: {count}")

        return "\n".join(lines)


class SleepTimeProcessor:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self.consolidation = MemoryConsolidationEngine(memory)
        self.crystallizer = SkillCrystallizer(memory)
        self._last_report: Optional[SleepReport] = None

    def run_cycle(self, max_age_days: int = 30) -> SleepReport:
        start = datetime.now(timezone.utc)
        report = SleepReport(
            timestamp=start.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )

        try:
            report.consolidation = self.consolidation.consolidate(max_age_days=max_age_days)
            logger.info("Consolidacao concluida: %d arquivadas", report.consolidation.entries_archived)
        except Exception as e:
            report.errors.append(f"Consolidacao: {e}")
            logger.error("Erro na consolidacao: %s", e)

        try:
            report.crystallization = self.crystallizer.crystallize_from_memory()
            logger.info("Cristalizacao concluida: %d skills", report.crystallization.skills_created)
        except Exception as e:
            report.errors.append(f"Cristalizacao: {e}")
            logger.error("Erro na cristalizacao: %s", e)

        try:
            report.memory_health = self.consolidation.get_memory_health()
        except Exception as e:
            report.errors.append(f"Health check: {e}")
            logger.error("Erro no health check: %s", e)

        end = datetime.now(timezone.utc)
        report.duration_seconds = (end - start).total_seconds()

        self._last_report = report
        return report

    def get_last_report(self) -> Optional[SleepReport]:
        return self._last_report

    def get_memory_health(self) -> Dict[str, object]:
        return self.consolidation.get_memory_health()

    def get_skills_summary(self) -> Dict[str, object]:
        skills = self.crystallizer.list_skills()
        return {
            "total_skills": len(skills),
            "domains": list(set(s.domain for s in skills)),
            "top_skills": [s.name for s in sorted(skills, key=lambda s: -s.success_count)[:5]],
        }
