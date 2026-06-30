"""
ORION General Agent - Aprendizagem Autónoma
============================================
Sistema que permite ao General aprender das interações automaticamente.

Capacidades:
- Armazena interações e resultados
- Extrai padrões e insights
- Melhora respostas futuras baseado em experiência
- Aprendizagem por reforço (feedback do utilizador)
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib


@dataclass
class Interaction:
    """Uma interação armazenada"""
    id: str
    query: str
    response: str
    mode_used: str
    confidence: float
    feedback: Optional[str]  # "positive", "negative", None
    tags: List[str]
    timestamp: str
    context: Optional[Dict] = None


@dataclass
class Pattern:
    """Um padrão aprendido"""
    pattern_id: str
    description: str
    trigger_conditions: List[str]
    response_template: str
    success_rate: float
    usage_count: int
    last_used: str


@dataclass
class LearningInsight:
    """Um insight aprendido"""
    insight_id: str
    category: str
    content: str
    confidence: float
    source_interactions: List[str]
    created_at: str


class AutonomousLearner:
    """
    Sistema de Aprendizagem Autónoma do General
    ===========================================
    
    Aprende de cada interação:
    1. Armazena a interação
    2. Analisa o resultado
    3. Extrai padrões
    4. Melhora respostas futuras
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data" / "general_learning")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.interactions_file = self.data_dir / "interactions.json"
        self.patterns_file = self.data_dir / "patterns.json"
        self.insights_file = self.data_dir / "insights.json"
        self.stats_file = self.data_dir / "learning_stats.json"
        
        self.interactions: List[Interaction] = []
        self.patterns: List[Pattern] = []
        self.insights: List[LearningInsight] = []
        self.stats = {
            "total_interactions": 0,
            "positive_feedback": 0,
            "negative_feedback": 0,
            "patterns_discovered": 0,
            "insights_generated": 0,
            "learning_rate": 0.0,
        }
        
        self._load_data()
    
    def _load_data(self):
        """Carrega dados do disco"""
        if self.interactions_file.exists():
            with open(self.interactions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.interactions = [Interaction(**i) for i in data]
        
        if self.patterns_file.exists():
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.patterns = [Pattern(**p) for p in data]
        
        if self.insights_file.exists():
            with open(self.insights_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.insights = [LearningInsight(**i) for i in data]
        
        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                self.stats = json.load(f)
    
    def _save_data(self):
        """Guarda dados no disco"""
        with open(self.interactions_file, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in self.interactions], f, ensure_ascii=False, indent=2)
        
        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.patterns], f, ensure_ascii=False, indent=2)
        
        with open(self.insights_file, "w", encoding="utf-8") as f:
            json.dump([asdict(i) for i in self.insights], f, ensure_ascii=False, indent=2)
        
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str) -> str:
        """Gera ID único baseado no conteúdo"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def record_interaction(
        self,
        query: str,
        response: str,
        mode_used: str,
        confidence: float,
        tags: List[str] = None,
        context: Dict = None
    ) -> Interaction:
        """
        Regista uma interação para aprendizagem
        
        Args:
            query: Pergunta do utilizador
            response: Resposta dada
            mode_used: Modo utilizado (DEEP DIVE, ANALISAR, etc.)
            confidence: Nível de confiança da resposta
            tags: Tags para categorização
            context: Contexto adicional
        
        Returns:
            Interaction registada
        """
        interaction = Interaction(
            id=self._generate_id(f"{query}{datetime.now()}"),
            query=query,
            response=response,
            mode_used=mode_used,
            confidence=confidence,
            feedback=None,
            tags=tags or [],
            timestamp=datetime.now(timezone.utc).isoformat(),
            context=context,
        )
        
        self.interactions.append(interaction)
        self.stats["total_interactions"] += 1
        
        # Analisa padrões após cada interação
        if len(self.interactions) % 5 == 0:  # A cada 5 interações
            self._analyze_patterns()
            self._generate_insights()
        
        self._save_data()
        return interaction
    
    def record_feedback(self, interaction_id: str, feedback: str) -> bool:
        """
        Regista feedback do utilizador
        
        Args:
            interaction_id: ID da interação
            feedback: "positive" ou "negative"
        
        Returns:
            True se registado com sucesso
        """
        for interaction in self.interactions:
            if interaction.id == interaction_id:
                interaction.feedback = feedback
                
                if feedback == "positive":
                    self.stats["positive_feedback"] += 1
                elif feedback == "negative":
                    self.stats["negative_feedback"] += 1
                
                # Atualiza taxa de aprendizagem
                total = self.stats["positive_feedback"] + self.stats["negative_feedback"]
                if total > 0:
                    self.stats["learning_rate"] = self.stats["positive_feedback"] / total
                
                self._save_data()
                return True
        return False
    
    def _analyze_patterns(self):
        """Analisa interações para descobrir padrões"""
        # Agrupa por modo utilizado
        mode_groups = {}
        for interaction in self.interactions:
            mode = interaction.mode_used
            if mode not in mode_groups:
                mode_groups[mode] = []
            mode_groups[mode].append(interaction)
        
        # Para cada modo, identifica padrões
        for mode, interactions in mode_groups.items():
            if len(interactions) < 3:
                continue
            
            # Identifica palavras-chave comuns nas queries
            word_freq = {}
            for interaction in interactions:
                words = interaction.query.lower().split()
                for word in words:
                    if len(word) > 3:  # Ignora palavras curtas
                        word_freq[word] = word_freq.get(word, 0) + 1
            
            # Palavras mais frequentes são o padrão
            if word_freq:
                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                pattern_desc = f"Modo {mode} frequentemente usado com: {', '.join([w[0] for w in top_words])}"
                
                # Verifica se já existe padrão similar
                existing = any(
                    mode in p.description for p in self.patterns
                )
                
                if not existing:
                    pattern = Pattern(
                        pattern_id=self._generate_id(pattern_desc),
                        description=pattern_desc,
                        trigger_conditions=[w[0] for w in top_words],
                        response_template=f"Usar modo {mode} quando detectar: {', '.join([w[0] for w in top_words])}",
                        success_rate=self._calculate_mode_success_rate(mode),
                        usage_count=len(interactions),
                        last_used=datetime.now(timezone.utc).isoformat(),
                    )
                    self.patterns.append(pattern)
                    self.stats["patterns_discovered"] += 1
    
    def _calculate_mode_success_rate(self, mode: str) -> float:
        """Calcula taxa de sucesso de um modo"""
        mode_interactions = [
            i for i in self.interactions
            if i.mode_used == mode and i.feedback is not None
        ]
        
        if not mode_interactions:
            return 0.5  # Default
        
        positive = sum(1 for i in mode_interactions if i.feedback == "positive")
        return positive / len(mode_interactions)
    
    def _generate_insights(self):
        """Gera insights baseados nas interações"""
        # Insight 1: Modos mais bem-sucedidos
        mode_stats = {}
        for interaction in self.interactions:
            if interaction.feedback:
                mode = interaction.mode_used
                if mode not in mode_stats:
                    mode_stats[mode] = {"positive": 0, "negative": 0}
                
                if interaction.feedback == "positive":
                    mode_stats[mode]["positive"] += 1
                else:
                    mode_stats[mode]["negative"] += 1
        
        if mode_stats:
            best_mode = max(
                mode_stats.items(),
                key=lambda x: x[1]["positive"] / max(x[1]["positive"] + x[1]["negative"], 1)
            )
            
            insight = LearningInsight(
                insight_id=self._generate_id(f"best_mode_{best_mode[0]}"),
                category="performance",
                content=f"O modo '{best_mode[0]}' tem a maior taxa de sucesso",
                confidence=0.8,
                source_interactions=[i.id for i in self.interactions[-10:]],
                created_at=datetime.now(timezone.utc).isoformat(),
            )
            
            # Verifica se já existe insight similar
            existing = any(
                i.category == "performance" and "modo" in i.content
                for i in self.insights
            )
            
            if not existing:
                self.insights.append(insight)
                self.stats["insights_generated"] += 1
    
    def get_recommendations(self, query: str) -> Dict:
        """
        Recomendações baseadas em aprendizagem
        
        Args:
            query: Pergunta do utilizador
        
        Returns:
            Recomendações
        """
        query_lower = query.lower()
        
        # Procura padrões relevantes
        relevant_patterns = []
        for pattern in self.patterns:
            for condition in pattern.trigger_conditions:
                if condition in query_lower:
                    relevant_patterns.append(pattern)
                    break
        
        # Procura insights relevantes
        relevant_insights = []
        for insight in self.insights:
            if any(word in query_lower for word in insight.content.split()):
                relevant_insights.append(insight)
        
        # Recomendação de modo
        recommended_mode = None
        if relevant_patterns:
            # Usa o padrão com maior taxa de sucesso
            best_pattern = max(relevant_patterns, key=lambda p: p.success_rate)
            recommended_mode = best_pattern.response_template
        
        return {
            "recommended_mode": recommended_mode,
            "relevant_patterns": [p.description for p in relevant_patterns[:3]],
            "relevant_insights": [i.content for i in relevant_insights[:3]],
            "learning_rate": self.stats["learning_rate"],
            "total_interactions": self.stats["total_interactions"],
        }
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de aprendizagem"""
        return {
            **self.stats,
            "patterns_count": len(self.patterns),
            "insights_count": len(self.insights),
            "interactions_count": len(self.interactions),
        }
    
    def get_learning_summary(self) -> str:
        """Retorna resumo da aprendizagem"""
        stats = self.get_stats()
        
        summary = f"""
📊 **RESUMO DE APRENDIZAGEM - GENERAL AGENT**

**Interações Totais:** {stats['total_interactions']}
**Feedback Positivo:** {stats['positive_feedback']}
**Feedback Negativo:** {stats['negative_feedback']}
**Taxa de Aprendizagem:** {stats['learning_rate']*100:.1f}%

**Padrões Descobertos:** {stats['patterns_count']}
**Insights Gerados:** {stats['insights_count']}

**Melhores Modos:**
"""
        
        # Adiciona info sobre modos
        mode_stats = {}
        for interaction in self.interactions:
            if interaction.feedback:
                mode = interaction.mode_used
                if mode not in mode_stats:
                    mode_stats[mode] = {"positive": 0, "total": 0}
                mode_stats[mode]["total"] += 1
                if interaction.feedback == "positive":
                    mode_stats[mode]["positive"] += 1
        
        for mode, stats in sorted(mode_stats.items(), key=lambda x: x[1]["positive"]/max(x[1]["total"], 1), reverse=True)[:3]:
            success_rate = stats["positive"] / max(stats["total"], 1) * 100
            summary += f"- {mode}: {success_rate:.0f}% sucesso\n"
        
        return summary


# Instância global
_learner = None


def get_learner(data_dir: str = None) -> AutonomousLearner:
    """Retorna instância global do learner"""
    global _learner
    if _learner is None:
        _learner = AutonomousLearner(data_dir)
    return _learner
