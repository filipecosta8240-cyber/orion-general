from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

class SkillLevel(Enum):
    """Níveis de proficiência em skills"""
    NOVICE = 1
    BEGINNER = 2
    INTERMEDIATE = 3
    ADVANCED = 4
    EXPERT = 5
    MASTER = 6

@dataclass
class SkillMetrics:
    """Métricas de performance de uma skill"""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    average_execution_time: float = 0.0
    improvement_trend: float = 0.0  # % de melhoria
    last_used: Optional[str] = None
    feedback_score: float = 0.0  # 0-1
    
    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Skill:
    """Representação de uma skill evoluível do sistema"""
    name: str
    description: str
    category: str
    version: str = "1.0"
    level: SkillLevel = SkillLevel.NOVICE
    metrics: SkillMetrics = field(default_factory=SkillMetrics)
    dependencies: List[str] = field(default_factory=list)  # Outras skills necessárias
    tags: List[str] = field(default_factory=list)
    source_agent: str = "system"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    last_evolution: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "version": self.version,
            "level": self.level.name,
            "metrics": self.metrics.to_dict(),
            "dependencies": self.dependencies,
            "tags": self.tags,
            "source_agent": self.source_agent,
            "created_at": self.created_at,
            "last_evolution": self.last_evolution,
        }

@dataclass
class SkillEvolutionProposal:
    """Proposta para evolução de uma skill"""
    skill_name: str
    evolution_type: str  # "enhancement", "generalization", "specialization", "combination"
    description: str
    confidence_score: float  # 0-1
    source_agent: str
    reasoning: str
    implementation_hint: Optional[str] = None
    estimated_improvement: float = 0.0  # % de melhoria esperada
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
    status: str = "PROPOSED"

class EvolutionarySkillsEngine:
    """Motor de evolução de skills com aprendizado contínuo"""
    
    def __init__(self, memory_bridge, event_bus=None):
        self.memory = memory_bridge
        self.event_bus = event_bus
        self.skills: Dict[str, Skill] = {}
        self.evolution_history: List[SkillEvolutionProposal] = []
        self.skill_chains: Dict[str, List[str]] = {}  # Combinações de skills
        
        # Carrega skills iniciais
        self._load_initial_skills()
    
    def _load_initial_skills(self) -> None:
        """Carrega skills iniciais do sistema"""
        initial_skills = [
            Skill(
                name="research",
                description="Pesquisa aprofundada de tópicos",
                category="analysis",
                level=SkillLevel.INTERMEDIATE,
                tags=["research", "analysis"],
                source_agent="ELIAS"
            ),
            Skill(
                name="validation",
                description="Validação de afirmações com fontes",
                category="verification",
                level=SkillLevel.INTERMEDIATE,
                tags=["verification", "quality"],
                source_agent="PESQUISADOR"
            ),
            Skill(
                name="critical_thinking",
                description="Análise crítica e identificação de riscos",
                category="reasoning",
                level=SkillLevel.ADVANCED,
                tags=["strategy", "reasoning"],
                source_agent="DRAGÃO"
            ),
            Skill(
                name="pattern_recognition",
                description="Identificação de padrões em dados",
                category="analysis",
                level=SkillLevel.BEGINNER,
                tags=["analysis", "learning"],
                source_agent="DOCUMENTALISTA"
            ),
            Skill(
                name="synthesis",
                description="Síntese de informação de múltiplas fontes",
                category="analysis",
                level=SkillLevel.INTERMEDIATE,
                tags=["analysis", "synthesis"],
                source_agent="ESTRATEGA"
            ),
        ]
        
        for skill in initial_skills:
            self.skills[skill.name] = skill
    
    def register_skill(self, skill: Skill) -> str:
        """Registra uma nova skill no sistema"""
        self.skills[skill.name] = skill
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.EVOLUTION_SKILL_LEARNED,
                source="EvolutionarySkillsEngine",
                payload={"skill_name": skill.name, "level": skill.level.name}
            )
            self.event_bus.publish(event)
        
        return skill.name
    
    def record_skill_usage(
        self,
        skill_name: str,
        success: bool,
        execution_time: float,
        feedback_score: float = 0.5
    ) -> None:
        """Registra uso de uma skill para aprendizado"""
        if skill_name not in self.skills:
            return
        
        skill = self.skills[skill_name]
        metrics = skill.metrics
        
        metrics.total_attempts += 1
        metrics.last_used = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        metrics.feedback_score = (metrics.feedback_score + feedback_score) / 2
        
        if success:
            metrics.successful_attempts += 1
        else:
            metrics.failed_attempts += 1
        
        # Atualiza tempo médio
        old_avg = metrics.average_execution_time
        metrics.average_execution_time = (
            (old_avg * (metrics.total_attempts - 1) + execution_time) /
            metrics.total_attempts
        )
        
        # Calcula trend de melhoria
        if metrics.total_attempts > 5:
            recent_success = metrics.successful_attempts / metrics.total_attempts
            if recent_success > 0.7:
                metrics.improvement_trend = min(100, metrics.improvement_trend + 5)
            else:
                metrics.improvement_trend = max(0, metrics.improvement_trend - 2)
    
    def propose_evolution(
        self,
        skill_name: str,
        evolution_type: str,
        description: str,
        source_agent: str,
        reasoning: str,
        confidence_score: float = 0.5
    ) -> Optional[SkillEvolutionProposal]:
        """Cria proposta de evolução de skill"""
        
        if skill_name not in self.skills:
            return None
        
        skill = self.skills[skill_name]
        
        # Calcula melhoria estimada baseada em metrics
        estimated_improvement = self._estimate_improvement(skill, evolution_type)
        
        proposal = SkillEvolutionProposal(
            skill_name=skill_name,
            evolution_type=evolution_type,
            description=description,
            source_agent=source_agent,
            reasoning=reasoning,
            confidence_score=confidence_score,
            estimated_improvement=estimated_improvement
        )
        
        self.evolution_history.append(proposal)
        
        # Salva em memória
        self.memory.create_entry(
            title=f"SKILL_EVOLUTION | {skill_name}",
            content=self._evolution_proposal_content(proposal),
            tags={
                "domain": "skill_evolution",
                "skill": skill_name,
                "type": evolution_type,
                "priority": "normal"
            },
            source="EvolutionarySkillsEngine"
        )
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.EVOLUTION_PROPOSAL_CREATED,
                source="EvolutionarySkillsEngine",
                payload={
                    "skill_name": skill_name,
                    "evolution_type": evolution_type,
                    "confidence": confidence_score
                }
            )
            self.event_bus.publish(event)
        
        return proposal
    
    def _estimate_improvement(self, skill: Skill, evolution_type: str) -> float:
        """Estima percentagem de melhoria baseada no tipo de evolução"""
        base = skill.metrics.success_rate * 100
        
        evolution_multipliers = {
            "enhancement": 1.2,      # +20%
            "generalization": 1.5,   # +50%
            "specialization": 1.3,   # +30%
            "combination": 1.8,      # +80%
        }
        
        multiplier = evolution_multipliers.get(evolution_type, 1.1)
        
        # Quanto maior o level, mais difícil evoluir
        level_factor = 1.0 / (1 + skill.level.value * 0.2)
        
        return (base * multiplier * level_factor) - base
    
    def _evolution_proposal_content(self, proposal: SkillEvolutionProposal) -> str:
        """Formata proposta para salvaguarda em memória"""
        return f"""
Proposta de Evolução de Skill: {proposal.skill_name}
Tipo: {proposal.evolution_type}
Descrição: {proposal.description}

Fonte: {proposal.source_agent}
Confiança: {proposal.confidence_score:.1%}
Melhoria Estimada: +{proposal.estimated_improvement:.1f}%

Raciocínio:
{proposal.reasoning}

Status: {proposal.status}
Criado: {proposal.created_at}
        """.strip()
    
    def apply_evolution(self, skill_name: str, evolution_proposal: SkillEvolutionProposal) -> None:
        """Aplica evolução aprovada a uma skill"""
        if skill_name not in self.skills:
            return
        
        skill = self.skills[skill_name]
        
        # Atualiza versão
        version_parts = skill.version.split(".")
        version_parts[1] = str(int(version_parts[1]) + 1)
        skill.version = ".".join(version_parts)
        
        # Avança nível se aplicável
        if evolution_proposal.estimated_improvement > 15:
            current_level = skill.level.value
            if current_level < SkillLevel.MASTER.value:
                skill.level = SkillLevel(min(current_level + 1, SkillLevel.MASTER.value))
        
        # Reseta alguns metrics
        skill.metrics.improvement_trend = 0
        skill.last_evolution = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        
        evolution_proposal.status = "APPLIED"
        
        if self.event_bus:
            from .events import Event, EventType
            event = Event(
                type=EventType.EVOLUTION_PROPOSAL_APPROVED,
                source="EvolutionarySkillsEngine",
                payload={"skill_name": skill_name, "new_level": skill.level.name}
            )
            self.event_bus.publish(event)
    
    def get_skill_recommendations(self) -> List[Dict[str, Any]]:
        """Retorna recomendações de skills para evolução"""
        recommendations = []
        
        for skill in self.skills.values():
            # Skills com high success rate são candidatos a evolução
            if skill.metrics.success_rate > 0.8 and skill.level != SkillLevel.MASTER:
                recommendations.append({
                    "skill_name": skill.name,
                    "recommendation": "Candidate for advancement",
                    "reason": f"Success rate: {skill.metrics.success_rate:.1%}",
                    "priority": "high"
                })
            
            # Skills com low success rate precisam remediation
            if skill.metrics.success_rate < 0.5 and skill.metrics.total_attempts > 10:
                recommendations.append({
                    "skill_name": skill.name,
                    "recommendation": "Needs focused improvement",
                    "reason": f"Success rate: {skill.metrics.success_rate:.1%}",
                    "priority": "critical"
                })
        
        return recommendations
    
    def list_skills(self, category: Optional[str] = None, level: Optional[SkillLevel] = None) -> List[Skill]:
        """Lista skills com filtros opcionais"""
        filtered = list(self.skills.values())
        
        if category:
            filtered = [s for s in filtered if s.category == category]
        if level:
            filtered = [s for s in filtered if s.level == level]
        
        return filtered
    
    def get_skill_graph(self) -> Dict[str, Any]:
        """Retorna grafo de dependências e combinações de skills"""
        return {
            "skills": [s.to_dict() for s in self.skills.values()],
            "chains": self.skill_chains,
            "recommendations": self.get_skill_recommendations()
        }
