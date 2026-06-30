from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

class MCPResourceType(Enum):
    """Tipos de recursos disponíveis via MCP"""
    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"
    DATA = "data"

@dataclass
class MCPInputSchema:
    """Schema de inputs para uma ferramenta MCP"""
    type: str = "object"
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class MCPToolDefinition:
    """Definição de uma ferramenta exposta via MCP"""
    name: str
    description: str
    inputSchema: MCPInputSchema
    priority: str = "normal"
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.inputSchema.to_dict(),
            "priority": self.priority,
            "version": self.version,
            "tags": self.tags,
            "capabilities": self.capabilities,
        }

@dataclass
class MCPResource:
    """Recurso genérico exposto via MCP"""
    uri: str
    type: MCPResourceType
    name: str
    description: str
    mimeType: str = "application/json"
    contents: Dict[str, Any] = field(default_factory=dict)
    readable: bool = True
    writable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mimeType,
            "readable": self.readable,
            "writable": self.writable,
        }

class MCPServer:
    """Servidor MCP que expõe ferramentas e recursos do ORION"""
    
    def __init__(self, orion_daemon):
        self.orion = orion_daemon
        self.tools: Dict[str, MCPToolDefinition] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.prompts: Dict[str, Dict[str, Any]] = {}
        self._initialize_tools()
        self._initialize_resources()
        self._initialize_prompts()
    
    def _initialize_tools(self) -> None:
        """Inicializa ferramentas expondo o registry do ORION"""
        for tool_name, tool_class in self.orion.tool_registry.tools.items():
            tool_instance = tool_class(self.orion.memory)
            metadata = tool_instance.metadata()
            
            # Cria schema de inputs baseado na ferramenta
            input_schema = MCPInputSchema(
                properties={
                    input_name: {"type": "string", "description": f"Input {input_name}"}
                    for input_name in metadata.inputs
                },
                required=metadata.inputs
            )
            
            tool_def = MCPToolDefinition(
                name=metadata.name,
                description=metadata.description,
                inputSchema=input_schema,
                tags=["research", "validation", "evolution"],
                capabilities=["execute", "preview"]
            )
            
            self.tools[metadata.name] = tool_def
    
    def _initialize_resources(self) -> None:
        """Inicializa recursos como memória, histórico, etc"""
        # Recurso: Memory Index
        memory_index = self.orion.memory.list_entries()
        self.resources["orion://memory/index"] = MCPResource(
            uri="orion://memory/index",
            type=MCPResourceType.DATA,
            name="Memory Index",
            description="Índice completo de entradas de memória do ORION",
            contents={
                "total_entries": len(memory_index),
                "entries": [e.to_dict() for e in memory_index[:100]],  # Primeiras 100
            }
        )
        
        # Recurso: Tools Available
        self.resources["orion://tools/available"] = MCPResource(
            uri="orion://tools/available",
            type=MCPResourceType.DATA,
            name="Available Tools",
            description="Lista de ferramentas disponíveis no ORION",
            contents={
                "tools": [tool.to_dict() for tool in self.tools.values()]
            }
        )
        
        # Recurso: Proposals (evolução)
        proposals = self.orion.self_evolution.list_proposals()
        self.resources["orion://evolution/proposals"] = MCPResource(
            uri="orion://evolution/proposals",
            type=MCPResourceType.DATA,
            name="Evolution Proposals",
            description="Propostas de auto-evolução pendentes",
            contents={
                "total_proposals": len(proposals),
                "proposals": [p.to_dict() for p in proposals]
            }
        )
        
        # Recurso: Agent Status
        self.resources["orion://agents/status"] = MCPResource(
            uri="orion://agents/status",
            type=MCPResourceType.DATA,
            name="Agents Status",
            description="Status atual de todos os agentes",
            contents={
                "agents": [
                    {"name": self.orion.dragao.profile.name, "role": self.orion.dragao.profile.role},
                    {"name": self.orion.elias.profile.name, "role": self.orion.elias.profile.role},
                    {"name": self.orion.pesquisador.profile.name, "role": self.orion.pesquisador.profile.role},
                    {"name": self.orion.estratega.profile.name, "role": self.orion.estratega.profile.role},
                    {"name": self.orion.documentalista.profile.name, "role": self.orion.documentalista.profile.role},
                ]
            }
        )
    
    def _initialize_prompts(self) -> None:
        """Inicializa prompts estratégicos para agentes"""
        self.prompts["research-prompt"] = {
            "name": "Research Prompt",
            "description": "Template para pesquisa estruturada",
            "template": """
Realize uma pesquisa aprofundada sobre: {topic}
Contexto: {context}
Profundidade: {depth}

Estrutura esperada:
1. Resumo executivo
2. Contexto histórico
3. Achados principais
4. Gaps de conhecimento
5. Recomendações para ação
            """
        }
        
        self.prompts["validation-prompt"] = {
            "name": "Validation Prompt",
            "description": "Template para validação de afirmações",
            "template": """
Valide a seguinte afirmação: {claim}
Contexto: {context}

Passos de validação:
1. Verificar memória interna
2. Cross-reference com múltiplas fontes
3. Identificar gaps
4. Gerar confiança score
5. Recomendar ações
            """
        }
    
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Retorna lista de ferramentas disponíveis"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    def get_resources_list(self) -> List[Dict[str, Any]]:
        """Retorna lista de recursos disponíveis"""
        return [resource.to_dict() for resource in self.resources.values()]
    
    def get_prompts_list(self) -> List[Dict[str, Any]]:
        """Retorna lista de prompts disponíveis"""
        return [
            {
                "name": name,
                "description": prompt.get("description", ""),
                "template": prompt.get("template", "")
            }
            for name, prompt in self.prompts.items()
        ]
    
    def call_tool(self, tool_name: str, inputs: Dict[str, Any]) -> str:
        """Executa uma ferramenta MCP"""
        if tool_name not in self.orion.tool_registry.tools:
            return f"Erro: ferramenta '{tool_name}' não encontrada"
        
        try:
            tool_class = self.orion.tool_registry.tools[tool_name]
            tool_instance = tool_class(self.orion.memory)
            result = tool_instance.execute(**inputs)
            return result
        except Exception as e:
            return f"Erro ao executar ferramenta '{tool_name}': {str(e)}"
    
    def get_resource(self, uri: str) -> Optional[MCPResource]:
        """Recupera um recurso específico"""
        return self.resources.get(uri)
    
    def update_resource(self, uri: str, contents: Dict[str, Any]) -> bool:
        """Atualiza conteúdo de um recurso (se writable)"""
        resource = self.resources.get(uri)
        if not resource or not resource.writable:
            return False
        
        resource.contents = contents
        return True
    
    def to_mcp_capabilities(self) -> Dict[str, Any]:
        """Retorna capabilities do servidor MCP"""
        return {
            "tools": {
                "available": len(self.tools),
                "list": self.get_tools_list()
            },
            "resources": {
                "available": len(self.resources),
                "list": self.get_resources_list()
            },
            "prompts": {
                "available": len(self.prompts),
                "list": self.get_prompts_list()
            },
            "sampling": {
                "supported": True,
                "max_tokens": 8000
            }
        }
