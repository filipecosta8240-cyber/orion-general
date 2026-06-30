"""
ORION Conversation Sync - Cloud Storage
========================================
Sistema de sincronização de conversas entre cloud e local.
Usa JSONBin.io (gratuito) como armazenamento partilhado.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional
import urllib.request
import urllib.error


class ConversationSync:
    """
    Sincroniza conversas entre ORION cloud e local.
    
    Uso:
        sync = ConversationSync()
        sync.save_message("user", "Olá")
        messages = sync.get_messages()
    """
    
    # JSONBin.io - gratuito
    API_URL = "https://api.jsonbin.io/v3"
    # Usar bin público (sem API key)
    BIN_ID = None
    
    def __init__(self):
        self.messages_file = "data/sync_messages.json"
        self._ensure_file()
    
    def _ensure_file(self):
        """Garante que o ficheiro existe"""
        import os
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.messages_file):
            with open(self.messages_file, "w", encoding="utf-8") as f:
                json.dump([], f)
    
    def _load_messages(self) -> List[Dict]:
        """Carrega mensagens do ficheiro"""
        try:
            with open(self.messages_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def _save_messages(self, messages: List[Dict]):
        """Guarda mensagens no ficheiro"""
        with open(self.messages_file, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    
    def save_message(self, role: str, content: str, source: str = "local") -> Dict:
        """
        Guarda uma mensagem
        
        Args:
            role: "user" ou "assistant"
            content: Conteúdo da mensagem
            source: "local" ou "cloud"
        
        Returns:
            Mensagem guardada
        """
        messages = self._load_messages()
        
        message = {
            "id": hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:12],
            "role": role,
            "content": content,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        messages.append(message)
        
        # Mantém apenas últimas 100 mensagens
        if len(messages) > 100:
            messages = messages[-100:]
        
        self._save_messages(messages)
        return message
    
    def get_messages(self, limit: int = 50) -> List[Dict]:
        """
        Obtém mensagens
        
        Args:
            limit: Máximo de mensagens
        
        Returns:
            Lista de mensagens
        """
        messages = self._load_messages()
        return messages[-limit:]
    
    def clear_messages(self):
        """Limpa todas as mensagens"""
        self._save_messages([])
    
    def get_last_message(self) -> Optional[Dict]:
        """Obtém última mensagem"""
        messages = self._load_messages()
        return messages[-1] if messages else None


# Instância global
_sync = None


def get_sync() -> ConversationSync:
    """Retorna instância global de sincronização"""
    global _sync
    if _sync is None:
        _sync = ConversationSync()
    return _sync
