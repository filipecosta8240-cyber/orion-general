from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .memory import ObsidianMemoryBridge

logger = logging.getLogger("orion.skill_crystallizer")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "SKILLS"


@dataclass
class CrystallizedSkill:
    id: str
    name: str
    domain: str
    description: str
    trigger_keywords: List[str]
    procedure: List[str]
    source_report_ids: List[str]
    created_at: str
    version: int = 1
    success_count: int = 0
    fail_count: int = 0

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_skill_md(self) -> str:
        lines = [
            "---",
            f"name: {self.name}",
            f"description: {self.description}",
            f"domain: {self.domain}",
            f"version: {self.version}",
            f"created_at: {self.created_at}",
            f"trigger_keywords: {', '.join(self.trigger_keywords)}",
            f"success_count: {self.success_count}",
            f"fail_count: {self.fail_count}",
            "---",
            "",
            f"# {self.name}",
            "",
            f"**Dominio:** {self.domain}",
            f"**Descricao:** {self.description}",
            "",
            "## Gatilhos",
            "",
        ]
        for kw in self.trigger_keywords:
            lines.append(f"- `{kw}`")
        lines.extend(["", "## Procedimento", ""])
        for i, step in enumerate(self.procedure, 1):
            lines.append(f"{i}. {step}")
        lines.extend([
            "",
            "## Fonte",
            "",
        ])
        for rid in self.source_report_ids:
            lines.append(f"- Relatorio: `{rid}`")
        lines.append("")
        lines.append("---")
        lines.append("*Gerado automaticamente pelo SkillCrystallizer do ORION*")
        return "\n".join(lines)


@dataclass
class CrystallizationReport:
    skills_created: int
    skills_updated: int
    total_skills: int
    skill_names: List[str]

    def to_markdown(self) -> str:
        lines = [
            "# RELATORIO DE CRISTALIZACAO DE SKILLS",
            f"**Data:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
            "",
            f"- Skills criadas: {self.skills_created}",
            f"- Skills atualizadas: {self.skills_updated}",
            f"- Total no repositorio: {self.total_skills}",
            "",
            "## Skills",
        ]
        for name in self.skill_names:
            lines.append(f"- {name}")
        return "\n".join(lines)


class SkillCrystallizer:
    def __init__(self, memory: ObsidianMemoryBridge, skills_root: Optional[Path] = None):
        self.memory = memory
        self.skills_root = skills_root or SKILLS_ROOT
        self.skills_root.mkdir(parents=True, exist_ok=True)
        self._index_file = self.skills_root / "SKILLS_INDEX.json"
        self._index = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, object]]:
        if self._index_file.exists():
            try:
                return json.loads(self._index_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_index(self) -> None:
        self._index_file.write_text(
            json.dumps(self._index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def _extract_keywords(self, text: str) -> List[str]:
        words = re.findall(r"\b\w{4,}\b", text.lower())
        keywords = list(dict.fromkeys(words))
        return keywords[:8]

    def _extract_procedure(self, content: str) -> List[str]:
        procedure = []
        for line in content.split("\n"):
            line = line.strip()
            if re.match(r"^\d+[\.\)]\s", line):
                step = re.sub(r"^\d+[\.\)]\s*", "", line)
                if step:
                    procedure.append(step)
            elif line.startswith("- ") and len(line) > 5:
                procedure.append(line[2:])
        if not procedure:
            sentences = [s.strip() for s in re.split(r"[.!]", content) if len(s.strip()) > 15]
            procedure = sentences[:5]
        return procedure[:10]

    def _extract_domain(self, content: str, tags: Dict[str, str]) -> str:
        if "source_domain" in tags:
            return tags["source_domain"]
        if "domain" in tags and tags["domain"] != "self_evolution":
            return tags["domain"]
        keywords = {
            "seguranca": ["seguranca", "security", "protecao", "firewall"],
            "optimizacao": ["otimizacao", "optimization", "performance", "eficiencia"],
            "dados": ["dados", "data", "validacao", "validacao"],
            "agentes": ["agente", "agent", "multi-agent", "orquestracao"],
            "memoria": ["memoria", "memory", "consolidacao", "resumo"],
        }
        content_lower = content.lower()
        scores = {}
        for domain, words in keywords.items():
            scores[domain] = sum(1 for w in words if w in content_lower)
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        return "geral"

    def _find_existing_skill(self, name: str) -> Optional[str]:
        for skill_id, data in self._index.items():
            if data.get("name") == name:
                return skill_id
        return None

    def crystallize_from_report(self, report: Dict[str, object]) -> Optional[CrystallizedSkill]:
        tool_name = report.get("tool_name", "unknown")
        subject = report.get("subject", "unknown")
        findings = report.get("findings", [])
        actions = report.get("actions_taken", [])
        skill_name = f"{tool_name}_{subject.replace(' ', '_').lower()[:30]}"

        existing_id = self._find_existing_skill(skill_name)
        if existing_id:
            skill_data = self._index[existing_id]
            skill = CrystallizedSkill(**skill_data)
            skill.version += 1
            skill.success_count += 1
            self._index[existing_id] = skill.to_dict()
            self._save_index()
            skill_path = self.skills_root / f"{existing_id}.md"
            skill_path.write_text(skill.to_skill_md(), encoding="utf-8")
            logger.info("Skill atualizada: %s (v%d)", skill_name, skill.version)
            return skill

        combined_text = " ".join(findings + actions)
        keywords = self._extract_keywords(combined_text)
        procedure = self._extract_procedure(combined_text)
        domain = self._extract_domain(combined_text, {})

        if not procedure:
            procedure = [
                f"Analisar objetivo: {subject}",
                f"Consultar ferramenta {tool_name} para dados",
                "Cruzar com memorias existentes",
                "Gerar relatorio estruturado",
                "Registar resultado na memoria",
            ]

        skill_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:20]
        skill = CrystallizedSkill(
            id=skill_id,
            name=skill_name,
            domain=domain,
            description=f"Skill gerada a partir de auto-evolucao: {subject}",
            trigger_keywords=keywords,
            procedure=procedure,
            source_report_ids=[report.get("proposal_id", "unknown")],
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            version=1,
            success_count=1,
            fail_count=0,
        )

        self._index[skill_id] = skill.to_dict()
        self._save_index()
        skill_path = self.skills_root / f"{skill_id}.md"
        skill_path.write_text(skill.to_skill_md(), encoding="utf-8")

        self.memory.create_entry(
            title=f"SKILL_CRYSTALLIZED | {skill_name}",
            content=skill.to_skill_md(),
            tags={
                "domain": "skill_crystallization",
                "priority": "normal",
                "freshness": "today",
                "skill_domain": domain,
            },
            source="skill_crystallizer",
        )

        logger.info("Skill cristalizada: %s (id=%s)", skill_name, skill_id)
        return skill

    def crystallize_from_memory(self, title_pattern: str = "AUTO_EVOLUTION_REPORT") -> CrystallizationReport:
        entries = self.memory.search({"domain": "self_evolution"})
        reports = [e for e in entries if title_pattern in e.title]

        skills_created = 0
        skills_updated = 0
        skill_names = []

        for entry in reports:
            skill = self.crystallize_from_report({
                "tool_name": entry.tags.get("tool_name", "unknown"),
                "subject": entry.title.split("|")[-1].strip() if "|" in entry.title else entry.title,
                "findings": [],
                "actions_taken": [entry.content[:200]],
                "proposal_id": entry.id,
            })
            if skill:
                if skill.version == 1:
                    skills_created += 1
                else:
                    skills_updated += 1
                skill_names.append(skill.name)

        return CrystallizationReport(
            skills_created=skills_created,
            skills_updated=skills_updated,
            total_skills=len(self._index),
            skill_names=skill_names,
        )

    def list_skills(self) -> List[CrystallizedSkill]:
        return [CrystallizedSkill(**data) for data in self._index.values()]

    def get_skill(self, skill_id: str) -> Optional[CrystallizedSkill]:
        data = self._index.get(skill_id)
        return CrystallizedSkill(**data) if data else None

    def find_skill_by_keyword(self, keyword: str) -> List[CrystallizedSkill]:
        results = []
        for data in self._index.values():
            if keyword.lower() in [kw.lower() for kw in data.get("trigger_keywords", [])]:
                results.append(CrystallizedSkill(**data))
        return results
