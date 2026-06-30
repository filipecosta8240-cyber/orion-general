# ORION 2.0 - Quick Start Guide

## 🚀 Começar Rápido

### 1. Iniciar o Daemon
```bash
python start_orion.py
```

O daemon agora inicializa com:
- ✅ Event Bus (sistema pub/sub)
- ✅ MCP Server (Model Context Protocol)
- ✅ Evolutionary Skills Engine
- ✅ Multi-Agent Orchestrator
- ✅ Advanced Memory Manager

### 2. Verificar Status via API

**Health Check:**
```bash
curl http://localhost:8000/api/status
```

**Novos Endpoints:**
```bash
# Event system
curl http://localhost:8000/api/events/statistics
curl "http://localhost:8000/api/events/history?limit=20"

# MCP capabilities
curl http://localhost:8000/api/mcp/capabilities

# Skills status
curl http://localhost:8000/api/skills/status

# Orchestrator status
curl http://localhost:8000/api/orchestrator/status

# Memory cache stats
curl http://localhost:8000/api/memory/cache-stats
```

---

## 💡 Exemplos de Uso

### Exemplo 1: Publicar um Evento

```python
from orion.daemon import ORIONDaemon
from orion.events import Event, EventType
import json

# Iniciar daemon
daemon = ORIONDaemon()

# Criar evento
event = Event(
    type=EventType.AGENT_ACTION_COMPLETED,
    source="ELIAS",
    payload={"topic": "Avicultura", "result": "Research complete"},
    tags={"domain": "avicultura", "priority": "high"}
)

# Publicar
daemon.event_bus.publish(event)

# Verificar estatísticas
stats = daemon.event_bus.get_statistics()
print(json.dumps(stats, indent=2))
```

### Exemplo 2: Propor Evolução de Skill

```python
from orion.daemon import ORIONDaemon

daemon = ORIONDaemon()

# Propor evolução
proposal = daemon.skills_engine.propose_evolution(
    skill_name="research",
    evolution_type="generalization",
    description="Expand research capabilities to all domains",
    source_agent="ELIAS",
    reasoning="Success rate is 95% in avicultura, ready to generalize",
    confidence_score=0.9
)

print(f"Proposta criada: {proposal.id}")
print(f"Tipo: {proposal.evolution_type}")
print(f"Melhoria estimada: +{proposal.estimated_improvement:.1f}%")

# Listar skills com recomendações
recommendations = daemon.skills_engine.get_skill_recommendations()
for rec in recommendations:
    print(f"Skill {rec['skill_name']}: {rec['recommendation']}")
```

### Exemplo 3: Executar Workflow

```python
from orion.daemon import ORIONDaemon
from orion.orchestrator import WorkflowType, WorkflowTask

daemon = ORIONDaemon()

# Definir tarefas
tasks = [
    WorkflowTask(
        task_id="research",
        description="Research avicultura genetics",
        priority="high"
    ),
    WorkflowTask(
        task_id="validate",
        description="Validate research findings",
        dependencies=["research"],
        priority="high"
    ),
    WorkflowTask(
        task_id="document",
        description="Document final results",
        dependencies=["validate"],
        priority="normal"
    )
]

# Criar workflow
workflow = daemon.orchestrator.create_workflow(
    workflow_id="avicultura_research_001",
    description="Complete avicultura research and validation",
    workflow_type=WorkflowType.SEQUENTIAL,
    tasks=tasks
)

# Executar
for pending_task in workflow.get_pending_tasks():
    assigned = daemon.orchestrator.assign_task(
        "avicultura_research_001",
        pending_task.task_id
    )
    if assigned:
        print(f"✓ Tarefa {pending_task.task_id} atribuída")
        # Simula completação
        daemon.orchestrator.complete_task(
            "avicultura_research_001",
            pending_task.task_id,
            result=f"Results for {pending_task.task_id}"
        )

# Verificar status
status = daemon.orchestrator.get_workflow_status("avicultura_research_001")
print(f"Workflow progress: {status['progress']*100:.0f}%")
print(f"Completed: {status['completed']}/{status['total_tasks']}")
```

### Exemplo 4: Usar Advanced Memory Search

```python
from orion.daemon import ORIONDaemon

daemon = ORIONDaemon()
mm = daemon.memory_manager

# Busca por domain (usa índice)
avicultura_entries = mm.search_by_domain("avicultura")
print(f"Encontradas {len(avicultura_entries)} entradas sobre avicultura")

# Full-text search (busca por keywords)
genetics_results = mm.full_text_search("reprodução genética", limit=10)
print(f"Encontrados {len(genetics_results)} resultados sobre genética")

# Busca por tags múltiplas
critical_high = mm.search_by_tags({
    "priority": "critico",
    "domain": "epidemiologia"
})
print(f"Entradas críticas sobre epidemiologia: {len(critical_high)}")

# Obter entradas recentes
recent = mm.get_recent_entries(domain="avicultura", limit=5)
print(f"5 últimas entradas sobre avicultura:")
for entry in recent:
    print(f"  - {entry.title}")

# Cache statistics
stats = mm.get_cache_statistics()
print(f"Cache: {stats['cache_size']}/{stats['max_cache_size']} (hit rate: {stats['avg_hits_per_entry']:.1f})")
```

### Exemplo 5: MCP Capabilities

```python
from orion.daemon import ORIONDaemon
import json

daemon = ORIONDaemon()

# Ver MCP capabilities
capabilities = daemon.mcp_server.to_mcp_capabilities()
print(json.dumps(capabilities, indent=2))

# Listar ferramentas disponíveis
tools = daemon.mcp_server.get_tools_list()
print(f"Ferramentas disponíveis: {len(tools)}")
for tool in tools:
    print(f"  - {tool['name']}: {tool['description']}")

# Chamar uma ferramenta via MCP
result = daemon.mcp_server.call_tool("ResearchTool", {
    "topic": "Avicultura",
    "depth": 2
})
print(f"Resultado: {result}")
```

---

## 📊 Monitorar Sistema

### 1. Event Stream em Tempo Real
```python
from orion.daemon import ORIONDaemon
from orion.events import EventType, EventFilter
import time

daemon = ORIONDaemon()

# Subscribe a eventos críticos
def log_critical_event(event):
    print(f"⚠️  {event.source}: {event.type.value}")

daemon.event_bus.subscribe(
    [EventType.EVOLUTION_PROPOSAL_CREATED, EventType.SYSTEM_ERROR],
    log_critical_event,
    subscriber_id="monitor"
)

# Correr monitor por 60 segundos
start = time.time()
while time.time() - start < 60:
    time.sleep(1)
```

### 2. Verificar Saúde dos Agentes
```python
from orion.daemon import ORIONDaemon

daemon = ORIONDaemon()

# Obter status de todos os agentes
agents_status = daemon.orchestrator.get_all_agents_status()
for agent in agents_status:
    print(f"{agent['name']:15} | Status: {agent['status']:6} | Reliability: {agent['reliability']}")
```

### 3. Análise de Skills
```python
from orion.daemon import ORIONDaemon

daemon = ORIONDaemon()

# Ver grafo de skills
skill_graph = daemon.skills_engine.get_skill_graph()
print(f"Total skills: {len(skill_graph['skills'])}")
print("Recomendações:")
for rec in skill_graph['recommendations']:
    print(f"  - {rec['skill_name']}: {rec['recommendation']}")
```

---

## 🔧 Configuração Avançada

### Ajustar tamanho do cache
```python
# No __init__ do ORIONDaemon
self.memory_manager = AdvancedMemoryManager(self.memory, max_cache_size=5000)
```

### Adicionar novos tipos de eventos
```python
from orion.events import EventType

# Extend EventType com novos eventos
class CustomEventType(EventType):
    CUSTOM_EVENT = "custom.event"
```

### Registar handlers de eventos
```python
daemon.event_bus.subscribe(
    [EventType.MEMORY_ENTRY_CREATED],
    my_handler_function,
    subscriber_id="my_handler"
)
```

---

## ⚡ Performance Tips

1. **Use Memory Manager** em vez de direct access:
   ```python
   # ✅ Bom - usa cache e índices
   results = daemon.memory_manager.search_by_domain("avicultura")
   
   # ❌ Lento - sem cache
   results = daemon.memory.search({"domain": "avicultura"})
   ```

2. **Batch operations** quando possível:
   ```python
   # ✅ Bom - uma operação
   entries = mm.get_recent_entries(limit=100)
   
   # ❌ Lento - 100 operações individuais
   for i in range(100):
       entry = memory.read_entry(entry_id)
   ```

3. **Use full-text search** em vez de filtering:
   ```python
   # ✅ Rápido - indexed keywords
   results = mm.full_text_search("genética", limit=20)
   
   # ❌ Lento - sem índices
   results = [e for e in all_entries if "genética" in e.content]
   ```

---

## 🐛 Troubleshooting

### Problema: ImportError ao iniciar
**Solução:**
```bash
# Verificar imports
python -c "from orion import events, mcp_server, evolutionary_skills, orchestrator, memory_manager"

# Se erro, executar:
cd orion
python -m py_compile *.py
```

### Problema: Cache cheio
**Solução:**
```python
stats = daemon.memory_manager.optimize_storage()
print(f"Cleared: {stats['cache_cleared']} entries")
```

### Problema: Eventos não processados
**Solução:**
```python
# Verificar subscribers
stats = daemon.event_bus.get_statistics()
print(f"Subscribers: {stats['subscribers_count']}")

# Verificar histórico
history = daemon.event_bus.get_history(limit=20)
for event in history:
    print(event.to_dict())
```

---

## 📚 Referências Rápidas

| Operação | Código |
|---|---|
| Publicar evento | `daemon.event_bus.publish(event)` |
| Subscribe a evento | `daemon.event_bus.subscribe([EventType.X], callback)` |
| Propor evolução | `daemon.skills_engine.propose_evolution(...)` |
| Criar workflow | `daemon.orchestrator.create_workflow(...)` |
| Buscar em cache | `daemon.memory_manager.search_by_domain(...)` |
| Get MCP capabilities | `daemon.mcp_server.to_mcp_capabilities()` |

---

## 🎓 Próximas Lições

1. **Entender Event System**: Lê `ARCHITECTURE_IMPROVEMENTS.md` seção "Event-Driven Architecture"
2. **Explorar Skills**: Testa as 4 tipos de evolução (enhancement, generalization, specialization, combination)
3. **Workflows Avançados**: Tenta PARALLEL e HIERARCHICAL workflows
4. **Memory Optimization**: Experimenta rebuild de índices e cache tuning

---

**Última atualização**: Junho 10, 2026
**Versão**: Orion 2.0 Quick Start
