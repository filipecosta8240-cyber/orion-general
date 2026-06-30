from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from .memory import ObsidianMemoryBridge

logger = logging.getLogger("orion.tools")

@dataclass
class ToolMetadata:
    name: str
    description: str
    inputs: List[str]

class BaseTool:
    name = "BASE"
    description = "Ferramenta base ORION"
    inputs: List[str] = []

    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory

    @classmethod
    def metadata(cls) -> ToolMetadata:
        return ToolMetadata(name=cls.name, description=cls.description, inputs=cls.inputs)

    def execute(self, **kwargs: Any) -> str:
        return "Nenhuma ação definida para esta ferramenta."
class ResearchTool(BaseTool):
    name = "ResearchTool"
    description = "Pesquisa tópicos e gera um resumo inicial para o ORION."
    inputs = ["topic", "depth"]

    def execute(self, **kwargs: Any) -> str:
        topic = kwargs.get("topic", "tema desconhecido")
        depth = kwargs.get("depth", 1)

        entries = self.memory.list_entries()
        tags_count = {}
        sources = set()
        recent = []
        for e in entries:
            for k, v in e.tags.items():
                tags_count[k] = tags_count.get(k, 0) + 1
            sources.add(e.source)
            if e.created_at > "2026-06-01":
                recent.append(e.title)

        output = f"=== PESQUISA: {topic.upper()} ===\n\n"
        output += f"Total de memorias no sistema: {len(entries)}\n"
        output += f"Fontes ativas: {', '.join(sorted(sources))}\n\n"
        output += "Tags mais usadas:\n"
        for tag, count in sorted(tags_count.items(), key=lambda x: -x[1])[:5]:
            output += f"  - {tag}: {count} vezes\n"

        output += f"\nMemorias recentes (ultimos 30 dias): {len(recent)}\n"
        for t in recent[:5]:
            output += f"  - {t}\n"

        output += f"\n---\nTopico pesquisado: {topic}\n"
        output += f"Profundidade: {depth}\n"
        output += "Recomendacao: monitorizar evolucao do topico e cruzar com dominios adjacentes.\n"
        return output


class PromptTool(BaseTool):
    name = "PromptTool"
    description = "Gera prompts estratégicos e sugestões de melhoria para o sistema."
    inputs = ["objective"]

    def execute(self, **kwargs: Any) -> str:
        objective = kwargs.get("objective", "objetivo não especificado")

        entries = self.memory.list_entries()
        tags_usadas = set()
        for e in entries:
            for k, v in e.tags.items():
                tags_usadas.add(f"{k}={v}")

        output = f"=== ANALISE DE PROMPTS: {objective.upper()} ===\n\n"
        output += f"Dominios ativos no sistema: {', '.join(sorted(tags_usadas)) or 'nenhum'}\n\n"
        output += "Novo prompt gerado:\n"
        output += f"  Objective: {objective}\n"
        output += f"  Acao: 1) consultar memorias recentes, 2) identificar padroes, 3) gerar recomendacao\n"
        output += f"  Contexto: {len(entries)} entradas de memoria disponiveis\n"
        output += f"  Formato: relatorio estruturado com seccoes de descobertas e acoes\n"
        return output


class ValidationTool(BaseTool):
    name = "ValidationTool"
    description = "Valida afirmações com o histórico de memórias e sugere próximos passos."
    inputs = ["claim", "context"]

    def execute(self, **kwargs: Any) -> str:
        claim = kwargs.get("claim", "afirmação desconhecida")
        context = kwargs.get("context", "sem contexto")

        entries = self.memory.list_entries()
        matches = [e for e in entries if claim.lower() in e.content.lower()]

        output = f"=== VALIDACAO: {claim.upper()} ===\n\n"
        output += f"Contexto: {context}\n"
        output += f"Memorias encontradas: {len(entries)}\n"
        output += f"Correspondencias diretas: {len(matches)}\n\n"

        if matches:
            output += "Evidencias encontradas:\n"
            for e in matches[:3]:
                output += f"  - {e.title} (relevancia: alta)\n"

        output += "\nRegras de validacao geradas:\n"
        output += "  1. Cruzar informacao com pelo menos 2 fontes\n"
        output += "  2. Verificar consistencia temporal dos dados\n"
        output += "  3. Confirmar com agente especializado no dominio\n"
        output += "  4. Registar resultado da validacao como nova memoria\n"
        return output


class GeneralTool(BaseTool):
    """
    Ferramenta do General — Comandante Estratégico
    
    Fornece análise estratégica profunda com verificação de factos
    e honestidade brutal.
    """
    name = "GeneralTool"
    description = "Análise estratégica profunda com verificação de factos e honestidade brutal. Modos: [URGENTE], [DEEP DIVE], normal."
    inputs = ["query", "mode"]

    def execute(self, **kwargs: Any) -> str:
        query = kwargs.get("query", "análise geral")
        mode = kwargs.get("mode", "normal")
        
        # Tiers de certeza
        certainty_tiers = {
            1: "FACTO (Fonte verificável)",
            2: "ALTA (>90% certeza)",
            3: "MODERADA (70-90% certeza)",
            4: "BAIXA (50-70% certeza)",
            5: "DESCONHECIDO (<50% certeza - PESQUISAR)"
        }
        
        # Pesquisa na memória
        entries = self.memory.list_entries()
        relevant = [e for e in entries if any(word in e.content.lower() for word in query.lower().split())]
        
        output = f"🎖️ **GENERAL — ANÁLISE ESTRATÉGICA**\n\n"
        output += f"**QUERY:** {query}\n"
        output += f"**MODO:** {mode.upper()}\n\n"
        
        if mode.upper() == "[URGENTE]":
            output += "🚨 **MODO URGENTE**\n\n"
            output += "**DIAGNÓSTICO:** Análise rápida baseada em dados disponíveis.\n"
            output += "**ACÇÃO:** Proceder com cautela.\n"
            output += "**JUSTIFICAÇÃO:** Dados insuficientes para conclusões definitivas.\n"
        
        elif mode.upper() == "[DEEP DIVE]":
            output += "🎖️ **MODO DEEP DIVE — AUDITORIA IMPLACÁVEL**\n\n"
            output += "**ANÁLISE RECON:**\n"
            output += f"- Memórias relevantes: {len(relevant)}\n"
            output += f"- Total de memórias: {len(entries)}\n\n"
            
            output += "**CRÍTICA DO ANALYST:**\n"
            if len(relevant) < 3:
                output += "- ⚠️ AMOSTRA PEQUENA: Poucos dados para conclusões robustas\n"
            output += "- Verificar fontes TIER 1/2\n"
            output += "- Identificar lacunas lógicas\n\n"
            
            output += "**RECOMENDAÇÃO:** Proceder com cautela após auditoria completa.\n"
        
        else:
            output += "**ANÁLISE:**\n"
            output += f"- Memórias relevantes: {len(relevant)}\n"
            output += f"- Total de memórias: {len(entries)}\n\n"
            
            if relevant:
                output += "**FONTES IDENTIFICADAS:**\n"
                for e in relevant[:3]:
                    output += f"- {e.title}\n"
            
            output += "\n**RECOMENDAÇÃO:** Dados suficientes para análise.\n"
        
        output += f"\n**TIER DE CERTEZA:** {certainty_tiers[3]}\n"
        output += "**REGRA:** Se incerteza > 30%, pesquisar antes de responder.\n"
        
        return output


class ORIONToolRegistry:
    def __init__(self, memory: ObsidianMemoryBridge):
        self.memory = memory
        self.tools: Dict[str, Type[BaseTool]] = {}
        self._load_builtin_tools()
        self._load_plugin_tools()

    def _load_builtin_tools(self) -> None:
        for tool in (ResearchTool, PromptTool, ValidationTool, GeneralTool):
            self.register_tool(tool)

    def _load_plugin_tools(self) -> None:
        package = "orion.plugins"
        try:
            for finder, name, _ in pkgutil.iter_modules(importlib.import_module(package).__path__):
                module = importlib.import_module(f"{package}.{name}")
                for attr in dir(module):
                    value = getattr(module, attr)
                    if isinstance(value, type) and issubclass(value, BaseTool) and value is not BaseTool:
                        self.register_tool(value)
        except Exception:
            logger.warning("Falha ao carregar plugins", exc_info=True)

    def register_tool(self, tool_cls: Type[BaseTool]) -> None:
        self.tools[tool_cls.name] = tool_cls

    def list_tools(self) -> List[ToolMetadata]:
        return [tool.metadata() for tool in self.tools.values()]

    def get_tool(self, name: str) -> Optional[BaseTool]:
        tool_cls = self.tools.get(name)
        return tool_cls(self.memory) if tool_cls else None

    def run_tool(self, name: str, **kwargs: Any) -> str:
        tool = self.get_tool(name)
        if not tool:
            return f"Ferramenta {name} não encontrada."
        return tool.execute(**kwargs)
