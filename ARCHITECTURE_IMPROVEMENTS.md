# ORION System Architecture Improvements

## Overview
Este documento descreve as melhorias arquiteturais aplicadas ao sistema ORION em Junho 2026.

## Novos Componentes

### 1. **Event-Driven Architecture** (`events.py`)
Sistema de eventos centralized baseado em pub/sub que permite comunicação assíncrona entre componentes.

**Características:**
- `EventBus`: Pub/sub com subscribers/publishers
- `EventType`: Tipos de eventos pré-definidos (agent, memory, evolution, tool, system)
- `Event`: Estrutura padrão com payload, tags e prioridade
- `EventLogger`: Logging de eventos para memória
- `EventFilter`: Filtros para queries de eventos

**Uso:**
```python
# Publicar evento
event = Event(type=EventType.AGENT_ACTION_COMPLETED, source="DRAGÃO", payload={...})
event_bus.publish(event)

# Subscribe a eventos
event_bus.subscribe([EventType.EVOLUTION_SKILL_LEARNED], callback_function, subscriber_id="myid")
```

**Endpoints de API:**
- `/api/events/statistics` - Estatísticas do event bus
- `/api/events/history?limit=50` - Histórico de eventos

---

### 2. **MCP Server Integration** (`mcp_server.py`)
Model Context Protocol server que expõe tools, recursos e prompts de forma standardizada.

**Características:**
- `MCPToolDefinition`: Define ferramentas com schema de inputs
- `MCPResource`: Recursos genéricos (dados, endpoints)
- `MCPServer`: Servidor que expõe capabilities do ORION

**Recursos Disponíveis:**
- `orion://memory/index` - Índice de memória
- `orion://tools/available` - Ferramentas disponíveis
- `orion://evolution/proposals` - Propostas de evolução
- `orion://agents/status` - Status dos agentes

**Prompts Disponíveis:**
- `research-prompt` - Template para pesquisa estruturada
- `validation-prompt` - Template para validação

**Endpoints de API:**
- `/api/mcp/capabilities` - MCP capabilities completas

---

### 3. **Evolutionary Skills Engine** (`evolutionary_skills.py`)
Sistema que permite auto-melhoria contínua de skills através de feedback e evolução.

**Características:**
- `Skill`: Representação de skill com metrics
- `SkillLevel`: 6 níveis de proficiência (NOVICE → MASTER)
- `SkillMetrics`: Tracking de performance
- `SkillEvolutionProposal`: Propostas de evolução
- `EvolutionarySkillsEngine`: Motor de evolução

**Tipos de Evolução:**
- `enhancement`: Melhoria de skill existente (+20%)
- `generalization`: Aplicação a novos domínios (+50%)
- `specialization`: Foco profundo em domínio (+30%)
- `combination`: Composição de múltiplas skills (+80%)

**Endpoints de API:**
- `/api/skills/status` - Status e recomendações de skills

---

### 4. **Multi-Agent Orchestrator** (`orchestrator.py`)
Sistema de orquestração que coordena colaboração entre múltiplos agentes.

**Características:**
- `OrchestrationWorkflow`: Define workflows com dependências
- `WorkflowType`: SEQUENTIAL, PARALLEL, HIERARCHICAL, REACTIVE, COLLABORATIVE
- `AgentCapability`: Define capacidades de agentes
- `AgentState`: Estado atual e reliability score
- `MultiAgentOrchestrator`: Coordena execução

**Workflow Execution:**
1. Define tarefas com dependências
2. Orquestrador aloca a melhor agente
3. Executa em paralelo ou sequencial
4. Retorna resultados

**Endpoints de API:**
- `/api/orchestrator/status` - Status de agentes e workflows

---

### 5. **Advanced Memory Manager** (`memory_manager.py`)
Sistema de memória com caching, indexing e busca otimizada.

**Características:**
- `CacheEntry`: Cache com TTL automático
- `MemoryIndex`: Índices para retrieval rápido
- `AdvancedMemoryManager`: Cache + indexing + full-text search

**Índices:**
- Tag Index: By tags (agent, domain, etc)
- Domain Index: By domain specialization
- Agent Index: By source agent
- Source Index: By source (memory origin)
- Content Keywords: Full-text search

**Performance:**
- Cache LRU com TTL
- Índices multi-dimensional
- Full-text search por keywords
- Rebuild automático

**Endpoints de API:**
- `/api/memory/cache-stats` - Estatísticas do cache

---

## Integração no Daemon

### Inicialização
```python
# No __init__ do ORIONDaemon:
self.event_bus = EventBus()
self.event_logger = EventLogger(self.memory)
self.mcp_server = MCPServer(self)
self.skills_engine = EvolutionarySkillsEngine(self.memory, self.event_bus)
self.orchestrator = MultiAgentOrchestrator(self.event_bus, self.memory)
self.memory_manager = AdvancedMemoryManager(self.memory)
```

### Agentes Registrados
- **Dragão**: STRATEGIST - Critical analysis
- **Elias**: EXECUTOR - Deep research  
- **Pesquisador**: VALIDATOR - Source validation
- **Estratega**: COORDINATOR - Workflow coordination
- **Documentalista**: ANALYZER - Knowledge synthesis

---

## Endpoints de API Novos

### Events
- `GET /api/events/statistics` - Stats do event bus
- `GET /api/events/history?limit=50` - Histórico de eventos

### MCP
- `GET /api/mcp/capabilities` - MCP capabilities

### Skills
- `GET /api/skills/status` - Status de skills

### Orchestrator
- `GET /api/orchestrator/status` - Status de agentes e workflows

### Memory
- `GET /api/memory/cache-stats` - Estatísticas do cache

---

## Padrões de Uso

### 1. Publicar Evento
```python
from orion.events import Event, EventType

event = Event(
    type=EventType.AGENT_ACTION_COMPLETED,
    source="ELIAS",
    payload={"task": "research", "result": "..."},
    tags={"domain": "avicultura"}
)
daemon.event_bus.publish(event)
```

### 2. Propor Evolução de Skill
```python
proposal = daemon.skills_engine.propose_evolution(
    skill_name="research",
    evolution_type="generalization",
    description="Expandir para novos domínios",
    source_agent="ELIAS",
    reasoning="Sucesso em avicultura permite aplicação geral",
    confidence_score=0.85
)
```

### 3. Executar Workflow
```python
from orion.orchestrator import WorkflowType, WorkflowTask, OrchestrationWorkflow

tasks = [
    WorkflowTask(task_id="t1", description="Research topic", priority="high"),
    WorkflowTask(task_id="t2", description="Validate findings", dependencies=["t1"]),
    WorkflowTask(task_id="t3", description="Document results", dependencies=["t2"])
]

workflow = daemon.orchestrator.create_workflow(
    workflow_id="research_001",
    description="Pesquisa e validação",
    workflow_type=WorkflowType.SEQUENTIAL,
    tasks=tasks
)

# Atribui e executa
for task in workflow.get_pending_tasks():
    daemon.orchestrator.assign_task("research_001", task.task_id)
```

### 4. Buscar em Memória com Cache
```python
# Busca por domain (usa index)
entries = daemon.memory_manager.search_by_domain("avicultura")

# Full-text search
results = daemon.memory_manager.full_text_search("reprodução genética")

# Por tags
entries = daemon.memory_manager.search_by_tags({
    "domain": "avicultura",
    "priority": "critico"
})
```

---

## Benefícios das Melhorias

### 1. **Escalabilidade**
- Event-driven permite comunicação assíncrona
- Multi-agent orchestration distribui carga
- Caching reduz I/O

### 2. **Autonomia**
- Evolutionary skills engine permite auto-melhoria
- MCP expõe capabilities dinamicamente
- Agents negociam tarefas automaticamente

### 3. **Performance**
- Cache com TTL reduz latência
- Índices multi-dimensionais aceleram search
- Event-driven evita polling

### 4. **Observabilidade**
- Event log completo de todas as ações
- Métricas de performance por skill/agente
- Histórico de evolução rastreável

### 5. **Interoperabilidade**
- MCP permite integração com outros sistemas
- Standard protocol para tools e recursos
- Prompts estratégicos reutilizáveis

---

## Próximas Melhorias Sugeridas

1. **Distributed Event Storage**: Persistir eventos em DB
2. **Skill Versioning**: Versionamento e rollback de skills
3. **Agent Learning**: Reinforcement learning para otimização
4. **Resource Allocation**: Balanceamento dinâmico de recursos
5. **Temporal Patterns**: Análise de patterns temporais
6. **Knowledge Graph**: Grafo de relações entre entidades

---

## Compatibilidade

✅ Totalmente backward compatible com sistema existente
✅ Novos componentes são opcionais
✅ Sistema funciona sem depender de novas features
✅ Gradual adoption possível

---

## Referências

- Event System: `orion/events.py`
- MCP Server: `orion/mcp_server.py`
- Skills Engine: `orion/evolutionary_skills.py`
- Orchestrator: `orion/orchestrator.py`
- Memory Manager: `orion/memory_manager.py`
- Daemon Integration: `orion/daemon.py`
- Server API: `orion/server.py`
