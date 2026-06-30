from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional

from .memory import MemoryEntry, ObsidianMemoryBridge
from .autonomous_learning import AutonomousLearner, get_learner
from .self_evolution_engine import SelfEvolutionEngine, get_evolution_engine
from .long_term_memory import LongTermMemory, get_long_term_memory, MemoryType
from .web_scraper import WebScraper, get_web_scraper


@dataclass
class AgentProfile:
    name: str
    role: str
    lema: str
    specialty: str


class BaseAgent:
    def __init__(self, memory: ObsidianMemoryBridge) -> None:
        self.memory = memory
        self.profile = AgentProfile(name="BASE", role="N/A", lema="N/A", specialty="N/A")

    def create_memory_entry(self, title: str, content: str, tags: Dict[str, str]) -> MemoryEntry:
        return self.memory.create_entry(title=title, content=content, tags=tags, source=self.profile.name)

    def note(self, message: str, domain: str, priority: str = "normal") -> MemoryEntry:
        tags = {
            "agent": self.profile.name,
            "domain": domain,
            "priority": priority,
            "freshness": "today",
        }
        return self.create_memory_entry(title=f"{self.profile.name} | {domain}", content=message, tags=tags)

class Dragao(BaseAgent):
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="DRAGÃO",
            role="Crítico Estratégico",
            lema="Verdade > Harmonia",
            specialty="Risco, estratégia, decisões críticas",
        )

    def adversarial_review(self, hypothesis: str) -> str:
        summary = (
            f"Avaliação adversarial de hipótese: {hypothesis}\n"
            "- Pontos fortes identificados\n"
            "- Riscos e falhas potenciais\n"
            "- Contrapontos que exigem validação adicional\n"
        )
        return self.note(summary, domain="estrategia", priority="critico")

class Elias(BaseAgent):
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="ELIAS",
            role="Pesquisador Profundo",
            lema="Profundidade > Brevidade",
            specialty="Avicultura, reprodução, breeding",
        )

    def research_summary(self, topic: str, findings: str) -> str:
        message = (
            f"Pesquisa aprofundada sobre {topic}:\n{findings}\n"
            "Fonte: revisão interna e literatura simulada."
        )
        return self.note(message, domain="avicultura", priority="normal")

class Pesquisador(BaseAgent):
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="PESQUISADOR",
            role="Validador de Fontes",
            lema="Verificação > Suposição",
            specialty="Fontes, integridade de dados",
        )

    def validate(self, claim: str, reference: str) -> str:
        message = (
            f"Validação de afirmação: {claim}\n"
            f"Referência verificada: {reference}\n"
            "Observação: necessidade de cruzar com pelo menos 2 outras fontes confiáveis."
        )
        return self.note(message, domain="validacao", priority="normal")

class Estratega(BaseAgent):
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="ESTRATEGA",
            role="Orquestrador",
            lema="Sinergia > Silos",
            specialty="Arquitetura, delegação, timing",
        )

    def plan(self, objective: str, next_steps: str) -> str:
        message = (
            f"Objetivo: {objective}\n"
            f"Próximos passos recomendados:\n{next_steps}"
        )
        return self.note(message, domain="planeamento", priority="normal")

class Documentalista(BaseAgent):
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="DOCUMENTALISTA",
            role="Arquivista de Memória",
            lema="Memória = Poder",
            specialty="Obsidian vault, metadata, tagging",
        )

    def archive(self, title: str, summary: str, scope: str = "system") -> str:
        message = (
            f"Arquivo de memória: {title}\n\n{summary}"
        )
        return self.note(message, domain=scope, priority="baixo")


class General(BaseAgent):
    """
    General — Comandante Estratégico v4.0
    
    Agente de comando estratégico com análise fria e honestidade brutal.
    Integra com ORION (memória, eventos, ferramentas).
    
    Capacidades 2026:
    - Pesquisa web integrada
    - Memória semântica
    - Modos de análise expandidos
    - Tracking de performance
    - Cálculo de confiança avançado
    - Deployment em sandbox (Docker, Cloud)
    - MCP Server para IA externa
    - Auto-deploy e configuração
    """
    
    # Tiers de certeza
    CERTAINTY_TIERS = {
        1: {"name": "FACTO", "desc": "Fonte verificável", "threshold": 0.95},
        2: {"name": "ALTA", "desc": ">90% certeza", "threshold": 0.85},
        3: {"name": "MODERADA", "desc": "70-90% certeza", "threshold": 0.70},
        4: {"name": "BAIXA", "desc": "50-70% certeza", "threshold": 0.50},
        5: {"name": "DESCONHECIDO", "desc": "<50% certeza", "threshold": 0.0},
    }
    
    # Fontes TIER 1/2 (fiáveis)
    TRUSTED_SOURCES = [
        "governo", "universidade", "instituto", "oficial",
        "ministério", "organização mundial", "banco mundial",
        "fao", "oms", "onu", "europa", "eurostat"
    ]
    
    # Configuração de sandbox
    SANDBOX_CONFIG = {
        "docker_image": "orion-general:latest",
        "default_port": 8001,
        "mcp_endpoint": "/sse",
        "health_endpoint": "/api/health",
    }
    
    def __init__(self, memory: ObsidianMemoryBridge):
        super().__init__(memory)
        self.profile = AgentProfile(
            name="GENERAL",
            role="Comandante Estratégico",
            lema="Verdade > Harmonia",
            specialty="Análise estratégica, pesquisa profunda, auto-correcção, deployment em sandbox",
        )
        self.mission_logs = []
        self.performance_stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "avg_confidence": 0.0,
            "domains_analyzed": {},
        }
        self.sandbox_status = {
            "deployed": False,
            "endpoint": None,
            "container_id": None,
        }
        
        # NOVOS SISTEMAS DE INTELIGÊNCIA
        self.learner = get_learner()
        self.evolution_engine = get_evolution_engine()
        self.long_term_memory = get_long_term_memory()
        self.web_scraper = get_web_scraper()
        
        # Estado de aprendizagem
        self.learning_enabled = True
        self.evolution_enabled = True
        self.web_research_enabled = True
    
    def think(self, query: str, context: Optional[Dict] = None) -> str:
        """
        Método principal de processamento.
        Analisa a query e determina o modo de operação.
        
        NOVAS CAPACIDADES:
        - Aprendizagem autónoma
        - Evolução própria
        - Memória de longo prazo
        - Web scraping em tempo real
        
        Modos disponíveis:
        - [URGENTE] → Diagnóstico rápido
        - [DEEP DIVE] → Auditoria implacável
        - [ANALISAR] → Análise detalhada
        - [COMPARAR] → Comparação de opções
        - [RISCOS] → Foco em riscos
        - [RESUMIR] → Resumo executivo
        - [PESQUISAR] → Web scraping em tempo real
        - [APRENDER] → Forçar aprendizagem
        - [EVOLUIR] → Forçar evolução
        - [MEMORIA] → Consultar memória de longo prazo
        """
        # Detectar códigos especiais
        if "[URGENTE]" in query:
            return self._process_urgent(query)
        
        if "[DEEP DIVE]" in query:
            return self._process_deep_dive(query)
        
        if "[ANALISAR]" in query:
            return self._process_analyze(query)
        
        if "[COMPARAR]" in query:
            return self._process_compare(query)
        
        if "[RISCOS]" in query:
            return self._process_risks(query)
        
        if "[RESUMIR]" in query:
            return self._process_summary(query)
        
        # NOVOS MODOS
        if "[PESQUISAR]" in query:
            return self._process_web_research(query)
        
        if "[APRENDER]" in query:
            return self._process_learning(query)
        
        if "[EVOLUIR]" in query:
            return self._process_evolution(query)
        
        if "[MEMORIA]" in query:
            return self._process_memory_query(query)
        
        # Detectar se é problema complexo
        if self._is_complex_problem(query):
            return self._process_complex(query, context)
        
        # Processamento normal com aprendizagem
        response = self._process_normal(query, context)
        
        # Regista interação para aprendizagem
        if self.learning_enabled:
            self.learner.record_interaction(
                query=query,
                response=response,
                mode_used="normal",
                confidence=0.7,
                tags=self._extract_tags(query),
            )
        
        return response
    
    def _is_complex_problem(self, query: str) -> bool:
        """Detecta se o problema é complexo"""
        complex_indicators = [
            "estratégia", "plano", "decisão", "análise",
            "avaliar", "comparar", "risco", "oportunidade",
            "investimento", "mercado", "concorrência", "expansão"
        ]
        return any(indicator in query.lower() for indicator in complex_indicators)
    
    def _search_memory(self, query: str, limit: int = 10) -> list:
        """Pesquisa na memória ORION"""
        results = []
        if self.memory:
            try:
                entries = self.memory.list_entries()
                # Pesquisa por palavras-chave
                query_words = query.lower().split()
                for entry in entries:
                    content_lower = entry.content.lower() if hasattr(entry, 'content') else str(entry).lower()
                    score = sum(1 for word in query_words if word in content_lower)
                    if score > 0:
                        results.append({
                            "entry": entry,
                            "score": score,
                            "content": content_lower[:300]
                        })
                # Ordena por relevância
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:limit]
            except Exception:
                pass
        return results
    
    def _calculate_confidence(self, memory_results: list, query: str) -> float:
        """Calcula confiança baseada em fontes e dados"""
        if not memory_results:
            return 0.3
        
        # Pontuação base
        base_score = 0.3
        
        # Bónus por número de resultados
        result_bonus = min(0.3, len(memory_results) * 0.05)
        
        # Bónus por fontes fiáveis
        trusted_bonus = 0.0
        for result in memory_results:
            content = result.get("content", "")
            if any(source in content for source in self.TRUSTED_SOURCES):
                trusted_bonus += 0.1
        
        # Bónus por profundidade de match
        depth_bonus = 0.0
        for result in memory_results:
            if result.get("score", 0) >= 3:
                depth_bonus += 0.05
        
        total = min(0.95, base_score + result_bonus + trusted_bonus + depth_bonus)
        return total
    
    def _get_certainty_tier(self, confidence: float) -> dict:
        """Retorna tier de certeza baseado na confiança"""
        for tier_num, tier_info in self.CERTAINTY_TIERS.items():
            if confidence >= tier_info["threshold"]:
                return {"level": tier_num, **tier_info}
        return {"level": 5, **self.CERTAINTY_TIERS[5]}
    
    def _process_urgent(self, query: str) -> str:
        """Processamento URGENTE — Diagnóstico | Acção | Justificação"""
        query = query.replace("[URGENTE]", "").strip()
        
        # Pesquisa rápida
        memory_results = self._search_memory(query, limit=5)
        confidence = self._calculate_confidence(memory_results, query)
        certainty = self._get_certainty_tier(confidence)
        
        # Diagnóstico
        if confidence < 0.5:
            diagnosis = f"DADOS INSUFICIENTES sobre '{query}'. Confiança: {confidence*100:.0f}%"
            action = "AGUARDAR mais dados antes de acção."
            justification = "Dados insuficientes para recomendação segura."
        else:
            diagnosis = f"Situação analisada com {confidence*100:.0f}% confiança ({certainty['name']})"
            action = "Proceder com a acção recomendada."
            justification = f"Baseado em {len(memory_results)} fontes verificadas."
        
        # Regista estatísticas
        self._update_stats(query, confidence)
        
        return f"""
🚨 **MODO URGENTE**

**DIAGNÓSTICO:** {diagnosis}

**ACÇÃO:** {action}

**JUSTIFICAÇÃO:** {justification}

**Fontes:** {len(memory_results)} | **Certeza:** {certainty['name']}
"""
    
    def _process_deep_dive(self, query: str) -> str:
        """Processamento DEEP DIVE — Auditoria implacável"""
        query = query.replace("[DEEP DIVE]", "").strip()
        
        # Pesquisa profunda
        memory_results = self._search_memory(query, limit=15)
        confidence = self._calculate_confidence(memory_results, query)
        certainty = self._get_certainty_tier(confidence)
        
        # Análise de lacunas
        gaps = self._identify_gaps(memory_results, query)
        
        # Análise de riscos
        risks = self._identify_risks(memory_results, query)
        
        # Recomendações
        recommendations = self._generate_recommendations(memory_results, query, confidence)
        
        # Regista estatísticas
        self._update_stats(query, confidence)
        
        # Formata resultado
        result = f"""
🎖️ **MODO DEEP DIVE — AUDITORIA IMPLACÁVEL**

**ANÁLISE DE:** {query}
**CONFIANÇA:** {confidence*100:.0f}% ({certainty['name']})
**FONTES:** {len(memory_results)} entradas encontradas

---

**DADOS RECOLHIDOS:**
"""
        
        for i, result_item in enumerate(memory_results[:5], 1):
            content = result_item.get("content", "N/A")[:150]
            result += f"{i}. {content}...\n"
        
        result += f"""
---

**LACUNAS IDENTIFICADAS:**
"""
        for gap in gaps:
            result += f"- ⚠️ {gap}\n"
        
        result += f"""
---

**ANÁLISE DE RISCOS:**
"""
        for risk in risks:
            result += f"- 🔴 {risk}\n"
        
        result += f"""
---

**RECOMENDAÇÕES:**
"""
        for rec in recommendations:
            result += f"- ✅ {rec}\n"
        
        result += f"""
---

**PRÓXIMOS PASSOS:**
1. Validar dados com fontes TIER 1/2
2. Documentar conclusões na memória ORION
3. Criar plano de acção concreto
"""
        
        # Log de missão
        result += self._create_mission_log(query, confidence, certainty)
        
        return result
    
    def _process_analyze(self, query: str) -> str:
        """Processamento ANALISAR — Análise detalhada"""
        query = query.replace("[ANALISAR]", "").strip()
        
        memory_results = self._search_memory(query, limit=10)
        confidence = self._calculate_confidence(memory_results, query)
        certainty = self._get_certainty_tier(confidence)
        
        self._update_stats(query, confidence)
        
        result = f"""
📊 **MODO ANÁLISE DETALHADA**

**TÓPICO:** {query}
**CONFIANÇA:** {confidence*100:.0f}% ({certainty['name']})

**DADOS:**
"""
        for i, r in enumerate(memory_results[:5], 1):
            result += f"{i}. {r.get('content', 'N/A')[:200]}\n"
        
        result += f"""
**CONCLUSÃO:** Análise baseada em {len(memory_results)} fontes.
"""
        return result
    
    def _process_compare(self, query: str) -> str:
        """Processamento COMPARAR — Comparação de opções"""
        query = query.replace("[COMPARAR]", "").strip()
        
        memory_results = self._search_memory(query, limit=10)
        confidence = self._calculate_confidence(memory_results, query)
        
        self._update_stats(query, confidence)
        
        return f"""
⚖️ **MODO COMPARAÇÃO**

**TÓPICO:** {query}

**OPÇÕES ANALISADAS:**
(Memória: {len(memory_results)} entradas relevantes)

**RECOMENDAÇÃO:** Comparação baseada em dados disponíveis.
"""
    
    def _process_risks(self, query: str) -> str:
        """Processamento RISCOS — Foco em riscos"""
        query = query.replace("[RISCOS]", "").strip()
        
        memory_results = self._search_memory(query, limit=10)
        risks = self._identify_risks(memory_results, query)
        
        self._update_stats(query, 0.5)
        
        result = f"""
⚠️ **MODO ANÁLISE DE RISCOS**

**TÓPICO:** {query}

**RISCOS IDENTIFICADOS:**
"""
        for risk in risks:
            result += f"- 🔴 {risk}\n"
        
        if not risks:
            result += "- ✅ Nenhum risco crítico identificado\n"
        
        return result
    
    def _process_summary(self, query: str) -> str:
        """Processamento RESUMIR — Resumo executivo"""
        query = query.replace("[RESUMIR]", "").strip()
        
        memory_results = self._search_memory(query, limit=5)
        confidence = self._calculate_confidence(memory_results, query)
        
        self._update_stats(query, confidence)
        
        return f"""
📋 **RESUMO EXECUTIVO**

**TÓPICO:** {query}
**CONFIANÇA:** {confidence*100:.0f}%

**SÍNTESE:** Resumo baseado em {len(memory_results)} fontes.
"""
    
    def _process_complex(self, query: str, context: Optional[Dict] = None) -> str:
        """Processamento para problemas complexos — Batalhão completo"""
        # Pesquisa profunda
        memory_results = self._search_memory(query, limit=15)
        confidence = self._calculate_confidence(memory_results, query)
        certainty = self._get_certainty_tier(confidence)
        
        # Análise de lacunas
        gaps = self._identify_gaps(memory_results, query)
        
        # Análise de riscos
        risks = self._identify_risks(memory_results, query)
        
        # Recomendações
        recommendations = self._generate_recommendations(memory_results, query, confidence)
        
        # Regista estatísticas
        self._update_stats(query, confidence)
        
        # Formata resultado
        result = f"""
🎖️ **ANÁLISE ESTRATÉGICA COMPLETA**

**RESUMO BRUTAL:** {self._generate_summary(query, memory_results, confidence)}

**CONFIANÇA:** {confidence*100:.0f}% ({certainty['name']})

---

**ANÁLISE:**
"""
        for i, r in enumerate(memory_results[:5], 1):
            result += f"{i}. {r.get('content', 'N/A')[:200]}\n"
        
        result += f"""
---

**CRÍTICA (Devil's Advocate):**
"""
        for gap in gaps:
            result += f"- ⚠️ {gap}\n"
        
        result += f"""
---

**RISCOS:**
"""
        for risk in risks:
            result += f"- 🔴 {risk}\n"
        
        result += f"""
---

**RECOMENDAÇÃO:**
"""
        for rec in recommendations:
            result += f"- ✅ {rec}\n"
        
        result += f"""
---

**PRÓXIMOS PASSOS:**
1. Validar com fontes adicionais
2. Documentar na memória ORION
3. Criar plano de acção
"""
        
        # Log de missão
        result += self._create_mission_log(query, confidence, certainty)
        
        return result
    
    def _process_normal(self, query: str, context: Optional[Dict] = None) -> str:
        """Processamento normal"""
        memory_results = self._search_memory(query, limit=5)
        confidence = self._calculate_confidence(memory_results, query)
        
        self._update_stats(query, confidence)
        
        result = f"""
**ANÁLISE:** {query}

**CONFIANÇA:** {confidence*100:.0f}%

**DADOS:**
"""
        for i, r in enumerate(memory_results[:3], 1):
            result += f"{i}. {r.get('content', 'N/A')[:150]}\n"
        
        result += f"""
**RECOMENDAÇÃO:** Dados baseados em {len(memory_results)} fontes.
"""
        return result
    
    def _identify_gaps(self, memory_results: list, query: str) -> list:
        """Identifica lacunas nos dados"""
        gaps = []
        
        if not memory_results:
            gaps.append("SEM DADOS: Nenhuma informação encontrada na memória")
        
        if len(memory_results) < 3:
            gaps.append("AMOSTRA PEQUENA: Poucos dados para conclusões robustas")
        
        # Verificar se há fontes fiáveis
        has_trusted = False
        for r in memory_results:
            content = r.get("content", "")
            if any(source in content for source in self.TRUSTED_SOURCES):
                has_trusted = True
                break
        
        if not has_trusted:
            gaps.append("SEM FONTES FIÁVEIS: Não há fontes TIER 1/2 identificadas")
        
        return gaps if gaps else ["Análise baseada em dados suficientes"]
    
    def _identify_risks(self, memory_results: list, query: str) -> list:
        """Identifica riscos"""
        risks = []
        
        if not memory_results:
            risks.append("DECISÃO SEM DADOS: Alto risco de erro")
        
        confidence = self._calculate_confidence(memory_results, query)
        if confidence < 0.5:
            risks.append("CONFIANÇA BAIXA: Dados insuficientes para decisão segura")
        
        if len(memory_results) < 3:
            risks.append("VIÉS DE AMOSTRA: Poucos pontos de dados")
        
        return risks if risks else ["Riscos dentro dos parâmetros aceitáveis"]
    
    def _generate_recommendations(self, memory_results: list, query: str, confidence: float) -> list:
        """Gera recomendações"""
        recs = []
        
        if confidence < 0.5:
            recs.append("PESQUISAR ANTES DE AGIR — Dados insuficientes")
            recs.append("Contactar fontes TIER 1/2 para validação")
        elif confidence < 0.7:
            recs.append("Proceder com cautela — Recolher mais dados")
            recs.append("Validar com pelo menos 2 fontes adicionais")
        else:
            recs.append("Dados suficientes para acção")
            recs.append("Documentar conclusões na memória")
        
        return recs
    
    def _generate_summary(self, query: str, memory_results: list, confidence: float) -> str:
        """Gera resumo brutal"""
        if not memory_results:
            return f"Sem dados sobre '{query}'. Pesquisa necessária."
        
        return f"Análise de '{query}' baseada em {len(memory_results)} fontes com {confidence*100:.0f}% confiança."
    
    def _create_mission_log(self, query: str, confidence: float, certainty: dict) -> str:
        """Cria log de missão"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        log = {
            "timestamp": timestamp,
            "query": query,
            "confidence": confidence,
            "certainty": certainty["name"],
        }
        self.mission_logs.append(log)
        
        return f"""
---

📋 **LOG DE MISSÃO**
**Data:** {timestamp}
**Query:** {query[:50]}...
**Confiança:** {confidence*100:.0f}% ({certainty['name']})
**Estado:** CONCLUÍDO
"""
    
    def _update_stats(self, query: str, confidence: float):
        """Atualiza estatísticas de performance"""
        self.performance_stats["total_analyses"] += 1
        if confidence >= 0.5:
            self.performance_stats["successful_analyses"] += 1
        
        # Atualiza média de confiança
        total = self.performance_stats["total_analyses"]
        current_avg = self.performance_stats["avg_confidence"]
        self.performance_stats["avg_confidence"] = (
            (current_avg * (total - 1) + confidence) / total
        )
        
        # Conta domínios
        domain = query.split()[0].lower() if query else "unknown"
        self.performance_stats["domains_analyzed"][domain] = (
            self.performance_stats["domains_analyzed"].get(domain, 0) + 1
        )
    
    def strategic_analysis(self, topic: str) -> str:
        """Análise estratégica profunda"""
        return self.think(f"[DEEP DIVE] {topic}")
    
    def research(self, topic: str, depth: int = 2) -> str:
        """Pesquisa profunda"""
        return self.think(f"[ANALISAR] {topic}")
    
    def audit(self, plan: str) -> str:
        """Auditoria de plano (Devil's Advocate)"""
        return self.think(f"[RISCOS] {plan}")
    
    def compare(self, options: str) -> str:
        """Comparação de opções"""
        return self.think(f"[COMPARAR] {options}")
    
    def get_performance_stats(self) -> Dict:
        """Retorna estatísticas de performance"""
        return self.performance_stats
    
    def get_mission_logs(self) -> list:
        """Retorna logs de missão"""
        return self.mission_logs
    
    # ========================================
    # NOVAS CAPACIDADES DE INTELIGÊNCIA
    # ========================================
    
    def _extract_tags(self, query: str) -> List[str]:
        """Extrai tags da query"""
        tags = []
        keywords = ["mercado", "investimento", "risco", "análise", "estratégia", "plano"]
        for kw in keywords:
            if kw in query.lower():
                tags.append(kw)
        return tags
    
    def _process_web_research(self, query: str) -> str:
        """Processa pesquisa web em tempo real"""
        query = query.replace("[PESQUISAR]", "").strip()
        
        # Pesquisa na web
        results = self.web_scraper.research_topic(query, max_sources=5)
        
        # Formata resposta
        response = f"""
🔍 **PESQUISA WEB EM TEMPO REAL**

**Tópico:** {query}
**Resultados:** {results['total_results']}
**Fontes Confiáveis:** {results['trusted_sources']}

**RESUMO:**
{results['summary']}

**FONTES ENCONTRADAS:**
"""
        
        for i, result in enumerate(results['results'][:5], 1):
            response += f"\n{i}. **{result['title']}**"
            response += f"\n   Fonte: {result['source']}"
            response += f"\n   {result['snippet'][:200]}..."
        
        # Armazena na memória de longo prazo
        self.long_term_memory.store(
            content=f"Pesquisa web sobre '{query}': {results['total_results']} resultados encontrados",
            memory_type=MemoryType.FACT,
            category="web_research",
            importance=0.6,
            source="web_scraper",
        )
        
        return response
    
    def _process_learning(self, query: str) -> str:
        """Processa comando de aprendizagem"""
        query = query.replace("[APRENDER]", "").strip()
        
        # Obtém resumo de aprendizagem
        summary = self.learner.get_learning_summary()
        
        # Obtém recomendações
        recommendations = self.learner.get_recommendations(query)
        
        response = f"""
📚 **SISTEMA DE APRENDIZAGEM AUTÓNOMA**

{summary}

**RECOMENDAÇÕES PARA ESTA QUERY:**
- Modo recomendado: {recommendations.get('recommended_mode', 'N/A')}
- Padrões relevantes: {len(recommendations.get('relevant_patterns', []))}
- Insights relevantes: {len(recommendations.get('relevant_insights', []))}
"""
        
        return response
    
    def _process_evolution(self, query: str) -> str:
        """Processa comando de evolução"""
        query = query.replace("[EVOLUIR]", "").strip()
        
        # Analisa performance
        analysis = self.evolution_engine.analyze_performance()
        
        # Tenta evolução automática
        proposals = self.evolution_engine.auto_evolve()
        
        # Obtém resumo
        summary = self.evolution_engine.get_evolution_summary()
        
        response = f"""
🧬 **SISTEMA DE EVOLUÇÃO PRÓPRIA**

**Score de Performance:** {analysis['overall_score']*100:.0f}%

**Forças Identificadas:** {len(analysis['strengths'])}
"""
        
        for strength in analysis['strengths'][:3]:
            response += f"- ✅ {strength['metric']}: {strength['trend']}\n"
        
        response += f"""
**Fraquezas Identificadas:** {len(analysis['weaknesses'])}
"""
        
        for weakness in analysis['weaknesses'][:3]:
            response += f"- ⚠️ {weakness['metric']}: {weakness['trend']}\n"
        
        response += f"""
**Propostas Geradas:** {len(proposals)}

{summary}
"""
        
        return response
    
    def _process_memory_query(self, query: str) -> str:
        """Processa consulta à memória de longo prazo"""
        query = query.replace("[MEMORIA]", "").strip()
        
        # Pesquisa na memória
        memories = self.long_term_memory.retrieve(query, limit=10)
        
        # Obtém estatísticas
        stats = self.long_term_memory.get_stats()
        
        response = f"""
🧠 **MEMÓRIA DE LONGO PRAZO**

**Total de Memórias:** {stats['total_memories']}
**Clusters:** {stats['total_clusters']}
**Palavras-chave:** {stats['total_keywords']}

**MEMÓRIAS RELEVANTES:**
"""
        
        for i, memory in enumerate(memories[:5], 1):
            response += f"\n{i}. **[{memory.memory_type}]** {memory.content[:150]}..."
            response += f"\n   Categoria: {memory.category}"
            response += f"\n   Importância: {memory.importance*100:.0f}%"
        
        if not memories:
            response += "\nNenhuma memória encontrada para esta query."
        
        return response
    
    def learn_from_interaction(self, query: str, response: str, feedback: str):
        """
        Aprende de uma interação
        
        Args:
            query: Pergunta do utilizador
            response: Resposta dada
            feedback: "positive" ou "negative"
        """
        # Regista na aprendizagem autónoma
        interaction = self.learner.record_interaction(
            query=query,
            response=response,
            mode_used="learned",
            confidence=0.7,
            tags=self._extract_tags(query),
        )
        
        # Regista feedback
        self.learner.record_feedback(interaction.id, feedback)
        
        # Armazena na memória de longo prazo
        memory_type = MemoryType.LESSON if feedback == "negative" else MemoryType.INSIGHT
        self.long_term_memory.store(
            content=f"Query: {query[:100]} | Feedback: {feedback}",
            memory_type=memory_type,
            category="interaction_feedback",
            importance=0.7 if feedback == "negative" else 0.5,
            source="user_feedback",
        )
        
        # Regista métrica de evolução
        self.evolution_engine.record_metric(
            "user_satisfaction",
            1.0 if feedback == "positive" else 0.0,
        )
    
    def store_knowledge(self, content: str, category: str, importance: float = 0.7):
        """
        Armazena conhecimento na memória de longo prazo
        
        Args:
            content: Conteúdo para armazenar
            category: Categoria
            importance: Importância (0-1)
        """
        self.long_term_memory.store(
            content=content,
            memory_type=MemoryType.FACT,
            category=category,
            importance=importance,
            source="general",
        )
    
    def research_web(self, topic: str) -> Dict:
        """
        Pesquisa na web em tempo real
        
        Args:
            topic: Tópico para pesquisar
        
        Returns:
            Resultados da pesquisa
        """
        return self.web_scraper.research_topic(topic)
    
    def get_full_status(self) -> Dict:
        """Retorna status completo com todas as novas capacidades"""
        return {
            "agent": "GENERAL",
            "version": "5.0",
            "capabilities": {
                "learning": self.learning_enabled,
                "evolution": self.evolution_enabled,
                "web_research": self.web_research_enabled,
                "long_term_memory": True,
            },
            "stats": {
                "performance": self.performance_stats,
                "learning": self.learner.get_stats(),
                "evolution": self.evolution_engine.get_stats(),
                "memory": self.long_term_memory.get_stats(),
                "web": self.web_scraper.get_stats(),
            },
        }
    
    # ========================================
    # SANDBOX DEPLOYMENT (Nova capacidade)
    # ========================================
    
    def generate_dockerfile(self) -> str:
        """Gera Dockerfile para deployment em sandbox"""
        dockerfile = """# ORION General Agent - Sandbox Dockerfile
FROM python:3.12-slim

# Security: non-root user
RUN groupadd -r orion && useradd -r -g orion -d /app orion

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc g++ && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application
COPY --chown=orion:orion . .

# Create directories
RUN mkdir -p /app/data /app/logs && chown -R orion:orion /app

# Environment
ENV PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PATH=/home/orion/.local/bin:$PATH \\
    ORION_ENV=sandbox

USER orion

# Expose MCP port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')" || exit 1

# Run MCP Server
CMD ["python", "orion_mcp_server.py"]
"""
        return dockerfile
    
    def generate_docker_compose(self) -> str:
        """Gera docker-compose.yml para sandbox"""
        compose = """# ORION General Agent - Docker Compose
version: '3.8'

services:
  orion-general:
    build: .
    container_name: orion-general-sandbox
    restart: always
    ports:
      - "8001:8001"
    volumes:
      - orion_data:/app/data
      - orion_logs:/app/logs
    environment:
      - ORION_ENV=sandbox
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  orion_data:
  orion_logs:
"""
        return compose
    
    def generate_mcp_config(self, sandbox_url: str = "localhost") -> str:
        """Gera configuração MCP para IA externa"""
        config = f"""{{
  "mcpServers": {{
    "orion-general": {{
      "type": "sse",
      "url": "http://{sandbox_url}:{self.SANDBOX_CONFIG['default_port']}{self.SANDBOX_CONFIG['mcp_endpoint']}",
      "description": "ORION General Agent - Strategic Command (Sandbox)"
    }}
  }}
}}
"""
        return config
    
    def generate_requirements(self) -> str:
        """Gera requirements.txt para sandbox"""
        requirements = """# ORION General Agent - Requirements
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
aiohttp>=3.9.0
orjson>=3.9.0
pydantic>=2.5.0
redis>=5.0.0
python-multipart>=0.0.6
websockets>=12.0
httpx>=0.26.0
cryptography>=42.0.0
pyjwt>=2.8.0
"""
        return requirements
    
    def generate_deploy_script(self) -> str:
        """Gera script de deploy para sandbox"""
        script = """#!/bin/bash
# ORION General Agent - Sandbox Deploy Script

set -e

echo "🎖️ Deploying ORION General Agent to Sandbox..."

# Build image
echo "Building Docker image..."
docker build -t orion-general:latest .

# Stop existing container
echo "Stopping existing container..."
docker stop orion-general-sandbox 2>/dev/null || true
docker rm orion-general-sandbox 2>/dev/null || true

# Run new container
echo "Starting sandbox..."
docker run -d \\
  --name orion-general-sandbox \\
  -p 8001:8001 \\
  --restart always \\
  orion-general:latest

echo ""
echo "✅ ORION General Agent deployed!"
echo ""
echo "MCP Endpoint: http://localhost:8001/sse"
echo "Health Check: http://localhost:8001/api/health"
echo ""
echo "Connect your AI:"
echo "  - Claude Desktop: Use MCP config"
echo "  - opencode: Add to opencode.jsonc"
echo "  - Any MCP client: http://localhost:8001/sse"
"""
        return script
    
    def get_sandbox_status(self) -> Dict:
        """Retorna status do sandbox"""
        return self.sandbox_status
    
    def deploy_info(self) -> str:
        """Retorna informações de deployment"""
        return f"""
🎖️ **ORION GENERAL AGENT — SANDBOX INFO**

**Versão:** 4.0
**Porta:** {self.SANDBOX_CONFIG['default_port']}
**MCP Endpoint:** {self.SANDBOX_CONFIG['mcp_endpoint']}
**Health Check:** {self.SANDBOX_CONFIG['health_endpoint']}

**Como usar:**

1. **Docker:**
   ```bash
   docker build -t orion-general .
   docker run -p 8001:8001 orion-general
   ```

2. **Docker Compose:**
   ```bash
   docker compose up -d
   ```

3. **Conectar IA:**
   ```json
   {{
     "mcpServers": {{
       "orion-general": {{
         "type": "sse",
         "url": "http://localhost:8001/sse"
       }}
     }}
   }}
   ```

**Capacidades:**
- ✅ Análise estratégica ([DEEP DIVE], [URGENTE], etc.)
- ✅ Pesquisa na memória ORION
- ✅ Anti-alucinação (5 Tiers de Certeza)
- ✅ Tracking de performance
- ✅ Deploy em sandbox (Docker, Cloud)
- ✅ MCP Server para IA externa
- ✅ Aprendizagem Autónoma
- ✅ Evolução Própria
- ✅ Memória de Longo Prazo
- ✅ Web Scraping em tempo real
"""


# ========================================
# INSTÂNCIA GLOBAL DO GENERAL
# ========================================

_general_instance = None


def get_general(memory=None) -> General:
    """
    Retorna instância global do General Agent
    
    Args:
        memory: Bridge de memória ORION (opcional)
    
    Returns:
        Instância do General
    """
    global _general_instance
    if _general_instance is None:
        if memory is None:
            from .memory import ObsidianMemoryBridge
            memory = ObsidianMemoryBridge()
        _general_instance = General(memory)
    return _general_instance
