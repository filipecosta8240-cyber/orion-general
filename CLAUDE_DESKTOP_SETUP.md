# Como usar o ORION com Claude Desktop

## Pré-requisitos

1. **Claude Desktop** instalado (download em https://claude.ai)
2. **Python 3.8+** instalado

## Configuração

### Passo 1: Localizar a pasta de configuração do Claude Desktop

A pasta de configuração depende do seu sistema operativo:

- **Windows**: `%APPDATA%\Claude\`
- **macOS**: `~/Library/Application Support/Claude/`
- **Linux**: `~/.config/Claude/`

### Passo 2: Editar o arquivo `claude_desktop_config.json`

Abra o arquivo `claude_desktop_config.json` na pasta de configuração e adicione a seguinte configuração:

```json
{
  "mcpServers": {
    "orion": {
      "command": "python",
      "args": ["C:\\Users\\BIG_P\\OneDrive\\Área de Trabalho\\Ai\\Jogo\\orion_mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\BIG_P\\OneDrive\\Área de Trabalho\\Ai\\Jogo"
      }
    }
  }
}
```

**IMPORTANTE**: Ajuste o caminho conforme a localização do seu projeto ORION.

### Passo 3: Reiniciar o Claude Desktop

Após salvar as alterações, reinicie o Claude Desktop.

## Ferramentas Disponíveis

O ORION expõe as seguintes ferramentas para o Claude:

### Memória
- `orion_memory_search` - Busca na memória do ORION
- `orion_memory_create` - Cria novas entradas na memória

### Agentes
- `orion_agents_status` - Status de todos os agentes

### Conhecimento
- `orion_knowledge_graph` - Consulta o grafo de conhecimento
- `orion_rag_search` - Busca semântica nos documentos
- `orion_rag_add` - Adiciona documentos ao RAG

### Automação
- `orion_execute_code` - Executa código Python de forma segura
- `orion_web_search` - Busca conteúdo na web

### Planeamento
- `orion_goals_list` - Lista objetivos e tarefas
- `orion_health_check` - Verificação de saúde do sistema

## Exemplos de Uso

### Criar uma entrada na memória
```
Cria uma entrada na memória do ORION com o título "Pesquisa IA" e conteúdo "Pesquisa sobre inteligência artificial realizada hoje"
```

### Buscar na memória
```
Busca na memória do ORION tudo sobre "machine learning"
```

### Consultar o grafo de conhecimento
```
Mostra todos os conceitos no grafo de conhecimento do ORION
```

### Executar código Python
```
Executa este código no ORION:
import math
print(math.pi)
```

### Adicionar documento ao RAG
```
Adiciona este documento ao sistema RAG do ORION: [cole o documento aqui]
```

## Recursos Disponíveis

- `orion://memory` - Acesso à memória
- `orion://agents` - Status dos agentes
- `orion://knowledge-graph` - Grafo de conhecimento
- `orion://goals` - Objetivos e tarefas

## Prompts Disponíveis

- `orion_research` - Prompt para pesquisa aprofundada
- `orion_analyze` - Prompt para análise de dados

## Solução de Problemas

### O Claude Desktop não连接a ao ORION

1. Verifique se o Python está no PATH
2. Verifique se o caminho no `claude_desktop_config.json` está correto
3. Reinicie o Claude Desktop
4. Verifique os logs em `~/.claude/logs/`

### Erro de importação

1. Certifique-se de que está no diretório correto
2. Verifique se todas as dependências estão instaladas

### O servidor não inicia

1. Execute manualmente: `python orion_mcp_server.py`
2. Verifique se há erros no terminal

## Mais Informações

- [Documentação MCP](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai)
- [ORION GitHub](https://github.com/seu-usuario/orion)
