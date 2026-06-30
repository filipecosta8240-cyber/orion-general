"""
ORION General Agent - Evolução Própria
=======================================
Sistema que permite ao General evoluir automaticamente.

Capacidades:
- Auto-avaliação de performance
- Identificação de fraquezas
- Geração de melhorias automáticas
- Evolução de prompts e estratégias
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class EvolutionProposal:
    """Proposta de evolução"""
    id: str
    evolution_type: str  # "prompt", "strategy", "response", "analysis"
    description: str
    current_behavior: str
    proposed_behavior: str
    estimated_improvement: float
    status: str  # "pending", "approved", "applied", "rejected"
    created_at: str
    applied_at: Optional[str] = None


@dataclass
class PerformanceMetric:
    """Métrica de performance"""
    metric_name: str
    value: float
    trend: str  # "improving", "declining", "stable"
    history: List[float]


@dataclass
class EvolutionLog:
    """Log de evolução"""
    log_id: str
    evolution_type: str
    description: str
    before: str
    after: str
    impact: float
    timestamp: str


class SelfEvolutionEngine:
    """
    Sistema de Evolução Própria do General
    =======================================
    
    Evolui automaticamente:
    1. Analisa a própria performance
    2. Identifica fraquezas
    3. Gera propostas de melhoria
    4. Aplica melhorias aprovadas
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data" / "general_evolution")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.proposals_file = self.data_dir / "evolution_proposals.json"
        self.metrics_file = self.data_dir / "performance_metrics.json"
        self.logs_file = self.data_dir / "evolution_logs.json"
        self.config_file = self.data_dir / "evolution_config.json"
        
        self.proposals: List[EvolutionProposal] = []
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.logs: List[EvolutionLog] = []
        self.config = {
            "auto_evolve": True,
            "evolution_threshold": 0.1,
            "max_evolutions_per_day": 5,
            "require_approval": True,
        }
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do disco"""
        if self.proposals_file.exists():
            with open(self.proposals_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.proposals = [EvolutionProposal(**p) for p in data]
        
        if self.metrics_file.exists():
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.metrics = {k: PerformanceMetric(**v) for k, v in data.items()}
        
        if self.logs_file.exists():
            with open(self.logs_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.logs = [EvolutionLog(**l) for l in data]
        
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)
    
    def _save_data(self):
        """Guarda dados no disco"""
        with open(self.proposals_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.proposals], f, ensure_ascii=False, indent=2)
        
        with open(self.metrics_file, "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.metrics.items()}, f, ensure_ascii=False, indent=2)
        
        with open(self.logs_file, "w", encoding="utf-8") as f:
            json.dump([asdict(l) for l in self.logs], f, ensure_ascii=False, indent=2)
        
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str) -> str:
        """Gera ID único"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def record_metric(self, metric_name: str, value: float):
        """
        Regista uma métrica de performance
        
        Args:
            metric_name: Nome da métrica
            value: Valor da métrica
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = PerformanceMetric(
                metric_name=metric_name,
                value=value,
                trend="stable",
                history=[value],
            )
        else:
            metric = self.metrics[metric_name]
            metric.history.append(value)
            
            # Mantém apenas últimos 100 valores
            if len(metric.history) > 100:
                metric.history = metric.history[-100:]
            
            # Calcula trend
            if len(metric.history) >= 5:
                recent = metric.history[-5:]
                older = metric.history[-10:-5] if len(metric.history) >= 10 else metric.history[:5]
                
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                
                if recent_avg > older_avg * 1.1:
                    metric.trend = "improving"
                elif recent_avg < older_avg * 0.9:
                    metric.trend = "declining"
                else:
                    metric.trend = "stable"
            
            metric.value = value
        
        self._save_data()
    
    def analyze_performance(self) -> Dict:
        """
        Analisa a própria performance
        
        Returns:
            Análise de performance
        """
        analysis = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }
        
        if not self.metrics:
            return analysis
        
        # Calcula score geral
        scores = []
        for name, metric in self.metrics.items():
            if metric.trend == "improving":
                scores.append(1.0)
            elif metric.trend == "stable":
                scores.append(0.5)
            else:
                scores.append(0.0)
            
            # Identifica fraquezas
            if metric.trend == "declining":
                analysis["weaknesses"].append({
                    "metric": name,
                    "current_value": metric.value,
                    "trend": metric.trend,
                })
            
            # Identifica forças
            if metric.trend == "improving":
                analysis["strengths"].append({
                    "metric": name,
                    "current_value": metric.value,
                    "trend": metric.trend,
                })
        
        if scores:
            analysis["overall_score"] = sum(scores) / len(scores)
        
        # Gera recomendações
        for weakness in analysis["weaknesses"]:
            analysis["recommendations"].append({
                "type": "improvement",
                "target": weakness["metric"],
                "suggestion": f"Melhorar {weakness['metric']} - trend está a descer",
            })
        
        return analysis
    
    def create_proposal(
        self,
        evolution_type: str,
        description: str,
        current_behavior: str,
        proposed_behavior: str,
        estimated_improvement: float = 0.1
    ) -> EvolutionProposal:
        """
        Cria uma proposta de evolução
        
        Args:
            evolution_type: Tipo de evolução
            description: Descrição da evolução
            current_behavior: Comportamento atual
            proposed_behavior: Comportamento proposto
            estimated_improvement: Melhoria estimada (0-1)
        
        Returns:
            Proposta criada
        """
        proposal = EvolutionProposal(
            id=self._generate_id(f"{evolution_type}{description}{datetime.now()}"),
            evolution_type=evolution_type,
            description=description,
            current_behavior=current_behavior,
            proposed_behavior=proposed_behavior,
            estimated_improvement=estimated_improvement,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        
        self.proposals.append(proposal)
        self._save_data()
        
        return proposal
    
    def approve_proposal(self, proposal_id: str) -> Optional[EvolutionProposal]:
        """
        Aprova uma proposta de evolução
        
        Args:
            proposal_id: ID da proposta
        
        Returns:
            Proposta aprovada ou None
        """
        for proposal in self.proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                proposal.status = "approved"
                self._save_data()
                return proposal
        return None
    
    def apply_proposal(self, proposal_id: str) -> Optional[EvolutionLog]:
        """
        Aplica uma proposta aprovada
        
        Args:
            proposal_id: ID da proposta
        
        Returns:
            Log de evolução ou None
        """
        for proposal in self.proposals:
            if proposal.id == proposal_id and proposal.status == "approved":
                # Aplica a evolução
                proposal.status = "applied"
                proposal.applied_at = datetime.now(timezone.utc).isoformat()
                
                # Cria log
                log = EvolutionLog(
                    log_id=self._generate_id(f"evolution_{proposal_id}"),
                    evolution_type=proposal.evolution_type,
                    description=proposal.description,
                    before=proposal.current_behavior,
                    after=proposal.proposed_behavior,
                    impact=proposal.estimated_improvement,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                
                self.logs.append(log)
                self._save_data()
                
                return log
        
        return None
    
    def auto_evolve(self) -> List[EvolutionProposal]:
        """
        Evolução automática baseada em performance
        
        Returns:
            Propostas geradas
        """
        if not self.config["auto_evolve"]:
            return []
        
        # Verifica limite diário
        today = datetime.now(timezone.utc).date().isoformat()
        today_proposals = [
            p for p in self.proposals
            if p.created_at.startswith(today)
        ]
        
        if len(today_proposals) >= self.config["max_evolutions_per_day"]:
            return []
        
        # Analisa performance
        analysis = self.analyze_performance()
        
        proposals = []
        
        # Gera propostas para fraquezas
        for weakness in analysis["weaknesses"]:
            proposal = self.create_proposal(
                evolution_type="strategy",
                description=f"Melhorar {weakness['metric']} - trend descendente",
                current_behavior=f"Métrica {weakness['metric']} está a descer: {weakness['current_value']}",
                proposed_behavior=f"Focar em melhorar {weakness['metric']} com estratégias específicas",
                estimated_improvement=0.15,
            )
            proposals.append(proposal)
        
        return proposals
    
    def get_evolution_history(self) -> List[Dict]:
        """Retorna histórico de evoluções"""
        return [asdict(log) for log in self.logs]
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de evolução"""
        return {
            "total_proposals": len(self.proposals),
            "pending_proposals": len([p for p in self.proposals if p.status == "pending"]),
            "approved_proposals": len([p for p in self.proposals if p.status == "approved"]),
            "applied_proposals": len([p for p in self.proposals if p.status == "applied"]),
            "total_evolutions": len(self.logs),
            "metrics_tracked": len(self.metrics),
            "auto_evolve_enabled": self.config["auto_evolve"],
        }
    
    def get_evolution_summary(self) -> str:
        """Retorna resumo de evolução"""
        stats = self.get_stats()
        
        summary = f"""
🧬 **RESUMO DE EVOLUÇÃO - GENERAL AGENT**

**Propostas Totais:** {stats['total_proposals']}
**Pendentes:** {stats['pending_proposals']}
**Aprovadas:** {stats['approved_proposals']}
**Aplicadas:** {stats['applied_proposals']}

**Evoluções Realizadas:** {stats['total_evolutions']}
**Métricas Rastreadas:** {stats['metrics_tracked']}

**Evolução Automática:** {"✅ Ativada" if stats['auto_evolve_enabled'] else "❌ Desativada"}

**Últimas Evoluções:**
"""
        
        for log in self.logs[-3:]:
            summary += f"- [{log.evolution_type}] {log.description} (Impacto: {log.impact*100:.0f}%)\n"
        
        return summary


# Instância global
_evolution_engine = None


def get_evolution_engine(data_dir: str = None) -> SelfEvolutionEngine:
    """Retorna instância global do engine de evolução"""
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = SelfEvolutionEngine(data_dir)
    return _evolution_engine
