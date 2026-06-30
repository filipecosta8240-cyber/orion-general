# Jogo de Leitura + ORION

Este workspace contém um jogo de leitura interativo para crianças com dislexia e um núcleo ORION autónomo de memória e rotina.

## Jogo de leitura

O jogo permite que a criança leia um texto em voz alta, veja as palavras a ficarem verdes e receba uma pontuação. Ele também armazena o histórico de resultados localmente.

### Como usar o jogo

1. Abra `index.html` no navegador (Chrome ou Edge recomendado).
2. Clique em `Iniciar leitura` e leia o texto em voz alta.
3. O jogo destaca as palavras lidas corretamente.
4. Clique em `Parar` quando terminar ou use `Ler automaticamente` se o reconhecimento de voz não estiver disponível.
5. Veja o histórico de pontuação na tabela.
6. Use a seção "Memória ORION" para ver entradas gravadas e sugestões de texto personalizadas.

## ORION — Núcleo Autónomo Cognitivo

O ORION agora tem um protótipo de hardware lógico em Python.

### Recursos implementados

- Memória persistente em `ORION_SYSTEM/MEMORIA`
- Índice automático de entradas em `MEMORY_INDEX.json`
- Subagentes:
  - `DRAGÃO` — crítico estratégico
  - `ELIAS` — pesquisador profundo
  - `PESQUISADOR` — validador de fontes
  - `ESTRATEGA` — orquestrador
  - `DOCUMENTALISTA` — arquivista de memória
- Scheduler local para jobs de saúde e pesquisa
- Self-evolution proposal generator

### Como executar ORION

1. Abra um terminal no diretório do projeto.
2. Execute o daemon ORION:

```powershell
python start_orion.py
```

3. Para usar o jogo integrado com memória, execute o servidor web ORION:

```powershell
python orion/server.py
```

4. Abra `http://127.0.0.1:8000` no navegador.
5. O jogo irá gravar resultados em `ORION_SYSTEM/MEMORIA` e exibirá entradas de memória diretamente na interface.
6. Para parar, pressione `CTRL+C`.

### Estrutura de arquivos ORION

- `orion/memory.py` — ponte de memória Obsidian-style.
- `orion/agents.py` — definições e comportamentos de agentes.
- `orion/scheduler.py` — agendamento de jobs periódicos.
- `orion/daemon.py` — inicialização e rotinas do daemon.
- `start_orion.py` — ponto de entrada.
- `.gitignore` — ignora a pasta de memória gerada.
- `orion/tools.py` — sistema de ferramentas ORION e registry.
- `orion/self_evolution.py` — engine de auto-evolução e propostas aprováveis.
- `orion/plugins/` — pasta de plugins para novas ferramentas.

### Sistemas Avançados (2026)

- `orion/events.py` — Arquitetura event-driven (pub/sub)
- `orion/mcp_server.py` — Integração Model Context Protocol
- `orion/evolutionary_skills.py` — Auto-melhoria de skills
- `orion/orchestrator.py` — Orquestração multi-agent
- `orion/memory_manager.py` — Memória avançada com cache
- `orion/agent_state_machine.py` — Máquinas de estados de agentes
- `orion/agent_reputation.py` — Sistema de reputação
- `orion/agent_health_monitor.py` — Monitorização de saúde
- `orion/consensus_engine.py` — Motor de consenso
- `orion/conflict_resolution.py` — Resolução de conflitos
- `orion/negotiation_protocol.py` — Protocolo de negociação
- `orion/social_dynamics.py` — Dinâmica social
- `orion/swarm_intelligence.py` — Inteligência de enxame
- `orion/knowledge_graph.py` — Grafo de conhecimento
- `orion/reflection_engine.py` — Motor de reflexão
- `orion/goal_planner.py` — Planeador de objetivos
- `orion/memory_salience.py` — Saliência de memória
- `orion/backup_system.py` — Sistema de backup
- `orion/episodic_memory.py` — Memória episódica
- `orion/prospective_memory.py` — Memória prospectiva
- `orion/memory_guard.py` — Guarda de memória
- `orion/idle_processor.py` — Processador de inatividade
- `orion/audit_trail.py` — Registo de auditoria
- `orion/performance_metrics.py` — Métricas de performance
- `orion/data_retention.py` — Gestão de retenção de dados
- `orion/a2a_protocol.py` — Protocolo Agent-to-Agent
- `orion/checkpointing.py` — Sistema de checkpoints
- `orion/cost_engineering.py` — Gestão de custos e tokens
- `orion/observability.py` — Tracing e observabilidade
- `orion/rag_system.py` — RAG para recuperação de documentos
- `orion/web_scraping.py` — Web scraping e automação
- `orion/code_execution.py` — Execução segura de código
- `orion/streaming.py` — Streaming de respostas
- `orion/webhooks.py` — Sistema de webhooks

## Requisitos

- Python 3.8 ou superior
- Nenhuma dependência externa necessária para execução básica

## Próximos passos recomendados

1. Expandir ORION com integração real de API de pesquisa.
2. Adicionar interface web de consulta de memória.
3. Incluir análise de texto em `ORION_SYSTEM/MEMORIA`.
4. Vincular jogo e ORION para um agente que sugira textos personalizados.
5. Desenvolver plugins ORION em `orion/plugins/` para ferramentas extras.
