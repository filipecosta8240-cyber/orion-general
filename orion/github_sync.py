"""
ORION GitHub Sync - Sincronização Automática
=============================================
Sistema de sincronização via GitHub API.
Cloud e local leem/escrevem no mesmo repositório.
Sem necessidade de ação do utilizador.
"""

import json
import base64
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional
import urllib.request
import urllib.error
import os


class GitHubSync:
    """
    Sincroniza conversas via GitHub.
    
    - Cloud: commit automático após cada mensagem
    - Local: lê do GitHub e sincroniza
    - Utilizador: não precisa de fazer nada
    """
    
    REPO = "filipecosta8240-cyber/orion-general"
    FILE_PATH = "data/conversations.json"
    BRANCH = "master"
    
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.base_url = f"https://api.github.com/repos/{self.REPO}/contents/{self.FILE_PATH}"
    
    def _request(self, method: str, url: str, data: dict = None) -> dict:
        """Faz request à API do GitHub"""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ORION-Sync",
        }
        
        body = json.dumps(data).encode() if data else None
        
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise
    
    def get_messages(self) -> List[Dict]:
        """Obtém mensagens do GitHub"""
        result = self._request("GET", self.base_url)
        
        if result and "content" in result:
            content = base64.b64decode(result["content"]).decode("utf-8")
            return json.loads(content)
        
        return []
    
    def save_messages(self, messages: List[Dict]) -> bool:
        """Guarda mensagens no GitHub"""
        # Limita a 200 mensagens
        if len(messages) > 200:
            messages = messages[-200:]
        
        content = json.dumps(messages, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content.encode()).decode()
        
        # Obtém SHA atual (necessário para atualizar)
        existing = self._request("GET", self.base_url)
        sha = existing["sha"] if existing else None
        
        data = {
            "message": f"ORION Sync: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": self.BRANCH,
        }
        
        if sha:
            data["sha"] = sha
        
        result = self._request("PUT", self.base_url, data)
        return result is not None
    
    def add_message(self, role: str, content: str, source: str = "local") -> Dict:
        """Adiciona uma mensagem e sincroniza"""
        messages = self.get_messages()
        
        message = {
            "id": hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:12],
            "role": role,
            "content": content,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        messages.append(message)
        
        if self.save_messages(messages):
            return message
        
        return None
    
    def get_last_messages(self, limit: int = 20) -> List[Dict]:
        """Obtém últimas mensagens"""
        messages = self.get_messages()
        return messages[-limit:]


# Instância global
_github_sync = None


def get_github_sync(token: str = None) -> GitHubSync:
    """Retorna instância global do GitHub sync"""
    global _github_sync
    if _github_sync is None:
        _github_sync = GitHubSync(token)
    return _github_sync
