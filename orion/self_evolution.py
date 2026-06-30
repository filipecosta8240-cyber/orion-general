from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .memory import MemoryEntry, ObsidianMemoryBridge
from .tools import ORIONToolRegistry


@dataclass
class SelfEvolutionProposal:
    id: str
    subject: str
    summary: str
    recommendation: str
    status: str
    created_at: str
    tool_name: Optional[str] = None
    tool_output: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class EvolutionReport:
    """Relatorio completo de uma auto-evolucao instalada."""
    proposal_id: str
    tool_name: str
    subject: str
    installed_at: str
    findings: List[str]
    actions_taken: List[str]
    new_skills: List[str]
    status: str = "INSTALLED"

    def to_markdown(self) -> str:
        lines = [
            "# AUTO-EVOLUCAO INSTALADA",
            "",
            f"**Ferramenta:** {self.tool_name}",
            f"**Objetivo:** {self.subject}",
            f"**Instalado em:** {self.installed_at}",
            f"**Status:** {self.status}",
            "",
            "## O que foi encontrado",
        ]
        for f in self.findings:
            lines.append(f"- {f}")
        lines.extend(["", "## O que foi instalado / alterado"])
        for a in self.actions_taken:
            lines.append(f"- {a}")
        if self.new_skills:
            lines.extend(["", "## Novos conhecimentos registados"])
            for s in self.new_skills:
                lines.append(f"- {s}")
        lines.append("")
        lines.append("---")
        lines.append("*Gerado automaticamente pelo ORION Self-Evolution Engine*")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class SelfEvolutionEngine:
    def __init__(self, memory: ObsidianMemoryBridge, tool_registry: ORIONToolRegistry):
        self.memory = memory
        self.tool_registry = tool_registry
        self.proposals: Dict[str, SelfEvolutionProposal] = {}
        self.reports: List[EvolutionReport] = []

    def _new_id(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")

    def create_proposal(self, subject: str, summary: str, recommendation: str, tool_name: Optional[str] = None, tool_output: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> SelfEvolutionProposal:
        proposal_id = self._new_id()
        proposal = SelfEvolutionProposal(
            id=proposal_id,
            subject=subject,
            summary=summary,
            recommendation=recommendation,
            status="AWAITING_USER_APPROVAL",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            tool_name=tool_name,
            tool_output=tool_output,
            tags=tags or {"domain": "self_evolution", "priority": "normal", "freshness": "today"},
        )
        self.proposals[proposal.id] = proposal
        self.memory.create_entry(
            title=f"SELF_EVOLUTION | {subject}",
            content=self._proposal_content(proposal),
            tags=proposal.tags,
            source="SELF_EVOLUTION",
        )
        return proposal

    def _proposal_content(self, proposal: SelfEvolutionProposal) -> str:
        output = proposal.tool_output or ""
        return (
            f"Assunto: {proposal.subject}\n"
            f"Resumo: {proposal.summary}\n"
            f"Recomendacao: {proposal.recommendation}\n"
            f"Status: {proposal.status}\n"
            f"Ferramenta: {proposal.tool_name or 'nenhuma'}\n"
            f"Saida da ferramenta:\n{output}\n"
        )

    def list_proposals(self, status: Optional[str] = None) -> List[SelfEvolutionProposal]:
        if status:
            return [proposal for proposal in self.proposals.values() if proposal.status == status]
        return list(self.proposals.values())

    def approve_proposal(self, proposal_id: str) -> Optional[SelfEvolutionProposal]:
        proposal = self.proposals.get(proposal_id)
        if proposal:
            proposal.status = "APPROVED"
            self.memory.create_entry(
                title=f"SELF_EVOLUTION_APPROVED | {proposal.subject}",
                content=self._proposal_content(proposal),
                tags={"domain": "self_evolution", "priority": "critico", "freshness": "today"},
                source="SELF_EVOLUTION",
            )
        return proposal

    def decline_proposal(self, proposal_id: str) -> Optional[SelfEvolutionProposal]:
        proposal = self.proposals.get(proposal_id)
        if proposal:
            proposal.status = "DECLINED"
            self.memory.create_entry(
                title=f"SELF_EVOLUTION_DECLINED | {proposal.subject}",
                content=self._proposal_content(proposal),
                tags={"domain": "self_evolution", "priority": "baixo", "freshness": "today"},
                source="SELF_EVOLUTION",
            )
        return proposal

    def _install_output(self, tool_name: str, output: str, objective: str) -> EvolutionReport:
        """Analisa o output da ferramenta e gera um relatorio de instalacao."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        lines = output.strip().split("\n")

        findings = []
        actions = []
        for line in lines:
            line = line.strip()
            if line.startswith("- "):
                item = line[2:]
                if any(kw in item.lower() for kw in ["encontrada", "memoria", "correspondencia", "evidencia", "relacionado"]):
                    findings.append(item)
                else:
                    actions.append(item)
            elif ":" in line and len(line) < 80:
                key, val = line.split(":", 1)
                if any(kw in key.lower() for kw in ["dominio", "contexto", "formato", "encontrada"]):
                    findings.append(f"{key.strip()}: {val.strip()}")

        if not findings:
            findings.append(f"Output analisado da ferramenta {tool_name}")
        if not actions:
            actions.append(f"Relatorio de {tool_name} registado na memoria")

        report = EvolutionReport(
            proposal_id=self._new_id(),
            tool_name=tool_name,
            subject=objective,
            installed_at=now,
            findings=findings[:10],
            actions_taken=actions[:10],
            new_skills=[f"{tool_name}: {objective}"],
        )

        self.reports.append(report)
        return report

    def generate_proposal_from_tool(self, tool_name: str, objective: str, context: Optional[str] = None) -> EvolutionReport:
        """Gera uma proposta e instala automaticamente, retornando o relatorio."""
        if tool_name == "ResearchTool":
            output = self.tool_registry.run_tool(tool_name, topic=objective, depth=2)
        elif tool_name == "PromptTool":
            output = self.tool_registry.run_tool(tool_name, objective=objective)
        elif tool_name == "ValidationTool":
            output = self.tool_registry.run_tool(tool_name, claim=objective, context=context or "")
        else:
            output = self.tool_registry.run_tool(tool_name, objective=objective, context=context or "")

        summary = f"Auto-evolucao gerada com base na ferramenta {tool_name}."

        proposal = self.create_proposal(
            subject=objective,
            summary=summary,
            recommendation=f"Instalado automaticamente: {objective}.",
            tool_name=tool_name,
            tool_output=output,
        )

        self.approve_proposal(proposal.id)
        proposal.status = "INSTALLED"

        report = self._install_output(tool_name, output, objective)

        self.memory.create_entry(
            title=f"AUTO_EVOLUTION_REPORT | {objective}",
            content=report.to_markdown(),
            tags={
                "domain": "self_evolution",
                "priority": "alto",
                "freshness": "today",
                "status": "installed",
            },
            source="SELF_EVOLUTION",
        )

        return report
