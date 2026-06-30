#!/usr/bin/env python3
"""
Script de instalação do ORION para Claude Desktop
===================================================
Configura automaticamente o Claude Desktop para usar o ORION como MCP Server.
"""

import json
import os
import sys
from pathlib import Path

def get_claude_config_path():
    """Retorna o caminho do arquivo de configuração do Claude Desktop"""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

def main():
    """Função principal"""
    print("=" * 60)
    print("ORION - Configuração para Claude Desktop")
    print("=" * 60)
    print()
    
    # Caminho do projeto ORION
    project_path = Path(__file__).resolve().parent
    mcp_server_path = project_path / "orion_mcp_server.py"
    
    if not mcp_server_path.exists():
        print(f"ERRO: Arquivo não encontrado: {mcp_server_path}")
        return 1
    
    # Caminho da configuração do Claude Desktop
    config_path = get_claude_config_path()
    
    print(f"Projeto ORION: {project_path}")
    print(f"Servidor MCP: {mcp_server_path}")
    print(f"Config Claude: {config_path}")
    print()
    
    # Lê ou cria a configuração
    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            print("Configuração existente encontrada.")
        except json.JSONDecodeError:
            print("AVISO: Arquivo de configuração corrompido. Criando novo.")
    
    # Inicializa mcpServers se não existir
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Configura o ORION
    config["mcpServers"]["orion"] = {
        "command": sys.executable,
        "args": [str(mcp_server_path)],
        "env": {
            "PYTHONPATH": str(project_path)
        }
    }
    
    # Salva a configuração
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print()
        print("✓ Configuração salva com sucesso!")
        print()
    except Exception as e:
        print(f"ERRO ao salvar configuração: {e}")
        print()
        print("Crie manualmente o arquivo com o seguinte conteúdo:")
        print()
        print(json.dumps({"mcpServers": {"orion": config["mcpServers"]["orion"]}}, indent=2))
        return 1
    
    print("=" * 60)
    print("PRÓXIMOS PASSOS")
    print("=" * 60)
    print()
    print("1. Reinicie o Claude Desktop")
    print()
    print("2. No Claude Desktop, você verá o ícone de ferramentas (🔧)")
    print("   clique nele para ver as ferramentas do ORION")
    print()
    print("3. Experimente digitar:")
    print('   "Mostra o status dos agentes do ORION"')
    print('   "Busca na memória do ORION sobre machine learning"')
    print('   "Cria uma entrada na memória com título Teste"')
    print()
    print("Ferramentas disponíveis:")
    print("  - orion_memory_search/buscar na memória")
    print("  - orion_memory_create/criar entrada")
    print("  - orion_agents_status/status dos agentes")
    print("  - orion_knowledge_graph/grafo de conhecimento")
    print("  - orion_rag_search/busca semântica")
    print("  - orion_rag_add/adicionar documento")
    print("  - orion_execute_code/executar código")
    print("  - orion_web_search/busca web")
    print("  - orion_goals_list/objetivos")
    print("  - orion_health_check/verificação de saúde")
    print()
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
