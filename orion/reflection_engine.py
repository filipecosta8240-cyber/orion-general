from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .memory import ObsidianMemoryBridge

logger = logging.getLogger("orion.reflection")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
REFLECTION_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "REFLECTIONS"


@dataclass
class ReflectionEntry:
    id: str
    timestamp: str
    task: str
    outcome: str
    what_worked: List[str]
    what_failed: List[str]
    root_cause: str
    lesson_learned: str
    suggested_fix: str
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"# REFLEXAO | {self.task}",
            f"**Data:** {self.timestamp}",
            f"**Resultado:** {self.outcome}",
            "",
            "## O que funcionou",
        ]
        for w in self.what_worked:
            lines.append(f"- {w}")
        lines.extend(["", "## O que falhou"])
        for f in self.what_failed:
            lines.append(f"- {f}")
        lines.extend([
            "",
            f"## Causa raiz: {self.root_cause}",
            f"## Lição aprendida: {self.lesson_learned}",
            f"## Correção sugerida: {self.suggested_fix}",
            f"## Confiança: {self.confidence:.0%}",
        ])
        return "\n".join(lines)


@dataclass
class ReflectionReport:
    total_reflections: int
    patterns_found: List[str]
    improvement_areas: List[str]
    success_rate: float
    top_lessons: List[str]

    def to_markdown(self) -> str:
        lines = [
            "# RELATORIO DE REFLEXAO",
            f"**Data:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            f"**Taxa de sucesso:** {self.success_rate:.0%}",
            "",
            "## Padrões identificados",
        ]
        for p in self.patterns_found:
            lines.append(f"- {p}")
        lines.extend(["", "## Áreas de melhoria"])
        for a in self.improvement_areas:
            lines.append(f"- {a}")
        lines.extend(["", "## Principais lições"])
        for l in self.top_lessons:
            lines.append(f"- {l}")
        return "\n".join(lines)


class ReflectionEngine:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self._root = REFLECTION_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._reflections: Dict[str, ReflectionEntry] = {}
        self._load_reflections()

    def _load_reflections(self) -> None:
        index_file = self._root / "REFLECTIONS_INDEX.json"
        if index_file.exists():
            try:
                data = json.loads(index_file.read_text(encoding="utf-8"))
                for rid, rdata in data.items():
                    self._reflections[rid] = ReflectionEntry(**rdata)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_reflections(self) -> None:
        index_file = self._root / "REFLECTIONS_INDEX.json"
        data = {rid: r.to_dict() for rid, r in self._reflections.items()}
        index_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:20]

    def record_reflection(
        self,
        task: str,
        outcome: str,
        what_worked: List[str],
        what_failed: List[str],
        root_cause: str,
        lesson_learned: str,
        suggested_fix: str,
        confidence: float = 0.8,
    ) -> ReflectionEntry:
        rid = self._new_id()
        entry = ReflectionEntry(
            id=rid,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            task=task,
            outcome=outcome,
            what_worked=what_worked,
            what_failed=what_failed,
            root_cause=root_cause,
            lesson_learned=lesson_learned,
            suggested_fix=suggested_fix,
            confidence=confidence,
        )
        self._reflections[rid] = entry
        self._save_reflections()

        self.memory.create_entry(
            title=f"REFLECTION | {task}",
            content=entry.to_markdown(),
            tags={
                "domain": "reflection",
                "priority": "alto",
                "freshness": "today",
                "outcome": outcome,
            },
            source="reflection_engine",
        )

        logger.info("Reflexão registada: %s (%s)", task, outcome)
        return entry

    def reflect_on_evolution(self, tool_name: str, objective: str, success: bool, details: str) -> ReflectionEntry:
        if success:
            return self.record_reflection(
                task=f"Auto-evolução: {objective}",
                outcome="sucesso",
                what_worked=[f"Ferramenta {tool_name} executada", details],
                what_failed=[],
                root_cause="Processo executado conforme esperado",
                lesson_learned=f"{tool_name} é eficaz para {objective}",
                suggested_fix="Manter configuração atual",
            )
        else:
            return self.record_reflection(
                task=f"Auto-evolução: {objective}",
                outcome="falha",
                what_worked=[],
                what_failed=[f"Ferramenta {tool_name} falhou", details],
                root_cause="Possível configuração incorreta ou dados insuficientes",
                lesson_learned=f"{tool_name} precisa de ajustes para {objective}",
                suggested_fix="Verificar parâmetros e memória disponível",
            )

    def reflect_on_research(self, topic: str, findings: str, quality: str) -> ReflectionEntry:
        is_good = quality in ("bom", "excelente", "good", "excellent")
        return self.record_reflection(
            task=f"Pesquisa: {topic}",
            outcome="sucesso" if is_good else "parcial",
            what_worked=[f"Topico pesquisado: {topic}", findings[:200]] if is_good else [],
            what_failed=["Qualidade insuficiente"] if not is_good else [],
            root_cause="Pesquisa superficial" if not is_good else "Dados suficientes",
            lesson_learned=f"Profundidade {'adequada' if is_good else 'insuficiente'} para {topic}",
            suggested_fix="Aumentar profundidade" if not is_good else "Manter profundidade atual",
        )

    def get_patterns(self) -> Dict[str, object]:
        outcomes = defaultdict(int)
        tasks = defaultdict(int)
        lessons = []
        for r in self._reflections.values():
            outcomes[r.outcome] += 1
            domain = r.task.split(":")[0] if ":" in r.task else r.task
            tasks[domain] += 1
            if r.lesson_learned:
                lessons.append(r.lesson_learned)
        total = len(self._reflections)
        successes = outcomes.get("sucesso", 0)
        return {
            "total": total,
            "success_rate": successes / max(total, 1),
            "outcomes": dict(outcomes),
            "task_domains": dict(tasks),
            "lessons": lessons[-10:],
        }

    def generate_report(self) -> ReflectionReport:
        patterns = self.get_patterns()
        failure_tasks = [r.task for r in self._reflections.values() if r.outcome == "falha"]
        success_tasks = [r.task for r in self._reflections.values() if r.outcome == "sucesso"]
        improvement_areas = list(set(failure_tasks))[:5]
        top_lessons = [r.lesson_learned for r in self._reflections.values() if r.lesson_learned][-5:]
        patterns_found = [f"Domínio: {d} ({c} tarefas)" for d, c in patterns.get("task_domains", {}).items()]
        return ReflectionReport(
            total_reflections=patterns["total"],
            patterns_found=patterns_found,
            improvement_areas=improvement_areas,
            success_rate=patterns["success_rate"],
            top_lessons=top_lessons,
        )

    def list_reflections(self, limit: int = 20) -> List[ReflectionEntry]:
        sorted_refs = sorted(self._reflections.values(), key=lambda r: r.timestamp, reverse=True)
        return sorted_refs[:limit]

    def find_by_task(self, task_pattern: str) -> List[ReflectionEntry]:
        return [r for r in self._reflections.values() if task_pattern.lower() in r.task.lower()]
