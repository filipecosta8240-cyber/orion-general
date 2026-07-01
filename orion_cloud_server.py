"""
ORION General Agent - Cloud Server v6.0
========================================
Servidor completo para Railway com:
- FastAPI + Uvicorn
- Integracao com pacote orion/ (General Agent, WebScraper, Memoria)
- Chat com IA via Pollinations/HuggingFace
- Pesquisa web em tempo real (DuckDuckGo)
- Memoria persistente (curto e longo prazo)
- Streaming SSE
- UI estilo Claude Desktop
"""

import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# SSL config
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

PORT = int(os.environ.get("PORT", 8080))
PROJECT_ROOT = Path(__file__).resolve().parent
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# --- Rate limiting & Caching ---
_last_ai_call = 0
_ai_call_lock = __import__("threading").Lock()
_ai_cache = {}
_ai_cache_max = 50
_WIKI_CACHE = {}

# --- Tenta importar do pacote orion/ ---
try:
    from orion.agents import General, get_general
    from orion.web_scraper import WebScraper, get_web_scraper
    from orion.long_term_memory import LongTermMemory, get_long_term_memory, MemoryType
    from orion.memory import ObsidianMemoryBridge
    from orion.autonomous_learning import AutonomousLearner, get_learner
    from orion.self_evolution_engine import SelfEvolutionEngine, get_evolution_engine
    ORION_IMPORTED = True
except ImportError as e:
    ORION_IMPORTED = False
    print(f"[ORION] Aviso: pacote orion/ nao importado ({e}). Usando modo standalone.")


# =====================================================
# ORION BRAIN - Motor de inteligencia unificado
# =====================================================

class OrionBrain:
    def __init__(self):
        self.general: Optional[General] = None
        self.scraper: Optional[WebScraper] = None
        self.ltm: Optional[LongTermMemory] = None
        self.memory: Optional[ObsidianMemoryBridge] = None
        self.learner: Optional[AutonomousLearner] = None
        self.evolution_engine: Optional[SelfEvolutionEngine] = None
        self.conversation_history: List[Dict] = []
        self.max_history = 50

        if ORION_IMPORTED:
            try:
                self.memory = ObsidianMemoryBridge()
                self.general = get_general(self.memory)
                self.scraper = get_web_scraper()
                self.ltm = get_long_term_memory()
                self.learner = get_learner()
                self.evolution_engine = get_evolution_engine()
                print("[ORION] Brain inicializado com pacote orion/ completo")
            except Exception as e:
                print(f"[ORION] Erro ao inicializar pacote orion/: {e}")

    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def get_context(self, max_messages: int = 10) -> str:
        recent = self.conversation_history[-max_messages:] if len(self.conversation_history) > max_messages else self.conversation_history
        lines = []
        for msg in recent:
            prefix = "Utilizador" if msg["role"] == "user" else "ORION"
            lines.append(f"{prefix}: {msg['content'][:500]}")
        return "\n".join(lines)

    def save_to_github(self, role: str, content: str, source: str = "cloud"):
        if not GITHUB_TOKEN:
            return
        try:
            import base64
            import hashlib

            repo = "filipecosta8240-cyber/orion-general"
            file_path = "data/conversations.json"
            url = f"https://api.github.com/repos/{repo}/contents/{file_path}"

            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "ORION-Sync",
            }

            messages = []
            sha = None
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, context=SSL_CTX) as resp:
                    result = json.loads(resp.read().decode())
                    if "content" in result:
                        messages = json.loads(base64.b64decode(result["content"]).decode())
                        sha = result["sha"]
            except Exception:
                pass

            messages.append({
                "id": hashlib.md5(f"{content}{datetime.now()}".encode()).hexdigest()[:12],
                "role": role,
                "content": content,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            if len(messages) > 200:
                messages = messages[-200:]

            new_content = json.dumps(messages, ensure_ascii=False, indent=2)
            data = {
                "message": f"ORION Sync: {datetime.now(timezone.utc).strftime('%H:%M:%S')}",
                "content": base64.b64encode(new_content.encode()).decode(),
                "branch": "master",
            }
            if sha:
                data["sha"] = sha

            req = urllib.request.Request(
                url, data=json.dumps(data).encode(), headers=headers, method="PUT"
            )
            urllib.request.urlopen(req, context=SSL_CTX)
        except Exception as e:
            print(f"[ORION] GitHub sync error: {e}")

    def call_ai(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        global _last_ai_call, _ai_cache
        cache_key = f"{system_prompt}:{prompt}"[:200]

        # Check cache first
        if cache_key in _ai_cache:
            cached = _ai_cache[cache_key]
            if time.time() - cached["time"] < 300:  # 5 min cache
                return cached["response"]

        with _ai_call_lock:
            elapsed = time.time() - _last_ai_call
            wait = max(0, 8 - elapsed)  # 8s min between AI calls
            if wait > 0:
                time.sleep(wait)
            _last_ai_call = time.time()

        if system_prompt:
            full_prompt = f"{system_prompt}\nPergunta: {prompt}\nResposta:"
        else:
            full_prompt = prompt
        full_prompt = full_prompt[:2000]

        # 1. Pollinations AI (gratis, sem API key)
        for attempt in range(2):
            try:
                prompt_encoded = urllib.parse.quote(full_prompt.encode("utf-8"))
                url = "https://text.pollinations.ai/" + prompt_encoded
                req = urllib.request.Request(url, headers={"User-Agent": "ORION/6.0"})
                with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as resp:
                    text = resp.read().decode("utf-8").strip()
                    if text and len(text) > 5 and "429" not in text:
                        # Cache it
                        _ai_cache[cache_key] = {"response": text, "time": time.time()}
                        if len(_ai_cache) > _ai_cache_max:
                            oldest = min(_ai_cache.keys(), key=lambda k: _ai_cache[k]["time"])
                            _ai_cache.pop(oldest, None)
                        return text
            except Exception as e:
                print(f"[ORION] Pollinations attempt {attempt+1}: {e}")
                time.sleep(3)

        # 2. Fallback: HuggingFace Mistral 7B (gratis, sem API key)
        try:
            hf_payload = json.dumps({
                "inputs": f"<s>[INST] {full_prompt[:800]} [/INST]",
                "parameters": {"max_new_tokens": 300, "temperature": 0.7}
            }).encode()
            req = urllib.request.Request(
                "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                data=hf_payload,
                headers={"Content-Type": "application/json", "User-Agent": "ORION/6.0"},
            )
            with urllib.request.urlopen(req, timeout=25, context=SSL_CTX) as resp:
                result = json.loads(resp.read().decode())
                if isinstance(result, list) and len(result) > 0:
                    text = result[0].get("generated_text", "")
                    if text and len(text) > 20:
                        # Extract response after [/INST]
                        if "[/INST]" in text:
                            text = text.split("[/INST]")[-1].strip()
                        _ai_cache[cache_key] = {"response": text, "time": time.time()}
                        return text
        except Exception as e:
            print(f"[ORION] HuggingFace fallback: {e}")

        return None

    def wikipedia_search(self, query: str) -> Optional[str]:
        global _WIKI_CACHE
        if query in _WIKI_CACHE:
            return _WIKI_CACHE[query]
        try:
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit=3"
            req = urllib.request.Request(url, headers={"User-Agent": "ORION/6.0"})
            with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                data = json.loads(resp.read().decode())
            results = data.get("query", {}).get("search", [])
            if results:
                parts = [f"**Wikipedia:** {r['title']}"]
                for r in results:
                    page_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&titles={urllib.parse.quote(r['title'])}&format=json"
                    req2 = urllib.request.Request(page_url, headers={"User-Agent": "ORION/6.0"})
                    with urllib.request.urlopen(req2, timeout=10, context=SSL_CTX) as resp2:
                        page_data = json.loads(resp2.read().decode())
                    pages = page_data.get("query", {}).get("pages", {})
                    for _, page in pages.items():
                        extract = page.get("extract", "")
                        if extract:
                            parts.append(extract[:1000])
                            break
                result = "\n\n".join(parts)
                _WIKI_CACHE[query] = result
                return result
        except Exception as e:
            print(f"[ORION] Wikipedia error: {e}")
        return None

    def web_search(self, query: str, max_results: int = 6, fetch_pages: bool = True) -> Optional[str]:
        if self.scraper:
            try:
                results = self.scraper.search(query, max_results=max_results)
                if results:
                    lines = []
                    for i, r in enumerate(results, 1):
                        lines.append(f"**{i}. {r.title}**")
                        lines.append(f"   URL: {r.url}")
                        lines.append(f"   Fonte: {r.source}")
                        if r.snippet:
                            lines.append(f"   {r.snippet}")
                        lines.append("")
                    # Fetch full content from top results
                    if fetch_pages and results:
                        for r in results[:2]:
                            try:
                                page = self.scraper.fetch_page(r.url, max_chars=3000)
                                if page and page.word_count > 50:
                                    lines.append(f"--- Conteudo de: {r.title} ---")
                                    lines.append(page.content[:2000])
                                    lines.append("")
                            except Exception:
                                pass
                    return "\n".join(lines)
            except Exception as e:
                print(f"[ORION] Web search error: {e}")
        return None

    def fetch_url(self, url: str) -> Optional[str]:
        """Faz fetch do conteudo de qualquer URL"""
        if self.scraper:
            try:
                page = self.scraper.fetch_page(url, max_chars=10000)
                if page:
                    return f"**Titulo:** {page.title}\n**URL:** {url}\n**Palavras:** {page.word_count}\n\n{page.content}"
            except Exception as e:
                print(f"[ORION] Fetch error: {e}")
        return None

    def _requires_web_search(self, message: str) -> bool:
        """Decide se a mensagem precisa de pesquisa web com base no conteudo."""
        msg = message.lower().strip()

        # Se o usuario pediu expressamente pesquisa
        if any(m in message for m in ("[PESQUISAR]", "[DEEP DIVE]", "[ANALISAR]", "[FETCH]")):
            return True

        # Palavras-chave que indicam necessidade de informacao atual
        need_search_keywords = [
            "noticias", "ultimas", "atual", "hoje", "2025", "2026", "2027",
            "cotacao", "cotação", "quanto custa",
            "ganhou", "venceu", "campeao", "campeão", "resultado",
            "eleicao", "eleição", "presidente", "governo",
            "previsao", "previsão", "temperatura",
            "lancamento", "lançamento",
            "bitcoin", "ethereum", "dolar", "dólar", "euro",
            "como funciona", "tutorial", "guia",
            "morreu", "faleceu", "morte",
            "guerra", "conflito",
            "estatisticas", "estatísticas", "dados", "numeros", "números",
            "ranking", "top", "melhor", "pior", "recorde",
        ]
        return any(kw in msg for kw in need_search_keywords)

    def think(self, message: str) -> str:
        msg_lower = message.lower().strip()
        self.add_to_history("user", message)

        # === DETECTA MODOS ESPECIAIS ===
        if "[DEEP DIVE]" in message:
            return self._mode_deep_dive(message)
        if "[URGENTE]" in message:
            return self._mode_urgent(message)
        if "[ANALISAR]" in message:
            return self._mode_analyze(message)
        if "[COMPARAR]" in message:
            return self._mode_compare(message)
        if "[RISCOS]" in message:
            return self._mode_risks(message)
        if "[RESUMIR]" in message:
            return self._mode_summary(message)
        if "[PESQUISAR]" in message:
            return self._mode_web_research(message)
        if "[FETCH]" in message:
            return self._mode_fetch_url(message)
        if "[MEMORIA]" in message:
            return self._mode_memory(message)

        # === DECISAO AUTONOMA DE PESQUISAR ===
        # Se a query parece precisar de informacao atual, pesquisa primeiro
        should_search = self._requires_web_search(message)
        web_context = None
        if should_search:
            web_context = self.web_search(message, fetch_pages=True)
            print(f"[ORION] Pesquisa autonoma ativada para: {message[:60]}...")

        if web_context:
            # Alimenta a IA com o contexto da web (concatenado para caber no limite)
            system = ("ORION General v6.0 - Responde com base nos resultados da web abaixo. "
                      "Citra as fontes. Responde em portugues de Portugal.")
            context_summary = web_context[:1500]
            prompt = f"Pergunta: {message}\n\nContexto web:\n{context_summary}"
            ai_response = self.call_ai(prompt, system)
            if ai_response and len(ai_response) > 15:
                enriched = f"{ai_response}\n\n---\n🔍 *Pesquisa web autonoma*"
                self.add_to_history("assistant", enriched)
                self.save_to_github("assistant", enriched, "ai+web")
                self._record_learning(message, enriched, "ai+web")
                return enriched
            # Se IA falhou com contexto, usa os resultados diretamente
            result = f"**{message}**\n\n{web_context}"
            self.add_to_history("assistant", result)
            self.save_to_github("assistant", result, "web")
            self._record_learning(message, result, "web")
            return result

        # === Tenta AI real primeiro (como Claude) ===
        system = ("ORION General v6.0 - Assistente IA em portugues de Portugal. "
                  "Responde de forma natural, util e honesta. "
                  "Usa markdown quando apropriado. Se nao souberes algo, diz 'NAO SEI'.")

        ai_response = self.call_ai(message, system)
        if ai_response and len(ai_response) > 10:
            # Detecta se a IA nao sabe a resposta -> pesquisa web automaticamente
            unsure_patterns = [
                "nao tenho acesso", "nao sei", "nao consigo", "nao posso",
                "i don't have", "i'm sorry", "i cannot", "i don't know",
                "not have access", "can't provide", "desculpa",
                "não tenho acesso", "não sei", "não consigo", "não posso",
            ]
            is_unsure = any(p in ai_response.lower() for p in unsure_patterns)

            if is_unsure:
                web_results = self.web_search(message, fetch_pages=True)
                if web_results:
                    system2 = ("ORION General v6.0 - Responde com base nos resultados da web. Citra fontes.")
                    prompt2 = f"Pergunta: {message}\n\nContexto:\n{web_results[:1500]}"
                    enriched_ai = self.call_ai(prompt2, system2)
                    if enriched_ai and len(enriched_ai) > 15:
                        enriched = f"{enriched_ai}\n\n---\n🔍 *Pesquisa automatica*"
                    else:
                        enriched = f"**{message}**\n\n{web_results}"
                    self.add_to_history("assistant", enriched)
                    self.save_to_github("assistant", enriched, "web_enriched")
                    self._record_learning(message, enriched, "web_enriched")
                    return enriched

            self.add_to_history("assistant", ai_response)
            self.save_to_github("assistant", ai_response, "ai")
            self._record_learning(message, ai_response, "ai")
            return ai_response

        # === Se IA falhou, pesquisa web diretamente ===
        web = self.web_search(message, fetch_pages=True)
        if web:
            result = f"**Pesquisa Web:** {message}\n\n{web}"
            self.add_to_history("assistant", result)
            self.save_to_github("assistant", result, "web")
            self._record_learning(message, result, "web")
            return result

        # === Fallback: Wikipedia ===
        wiki = self.wikipedia_search(message)
        if wiki:
            result = f"**Wikipedia:** {message}\n\n{wiki}"
            self.add_to_history("assistant", result)
            self.save_to_github("assistant", result, "wiki")
            self._record_learning(message, result, "wiki")
            return result

        # === Fallback final ===
        return self._fallback_response(message)

    def _mode_deep_dive(self, message: str) -> str:
        query = message.replace("[DEEP DIVE]", "").strip()
        web_info = self.web_search(query)
        ai = self.call_ai(f"Faz uma auditoria DEEP DIVE completa sobre: {query}", "ORION General v6 - Modo DEEP DIVE. Analise exaustiva.")
        parts = [f"🎖️ **DEEP DIVE AUDITORIA**\n\n**Tópico:** {query}\n"]
        if ai:
            parts.append(ai)
        if web_info and not ai:
            parts.append(f"**Dados Web:**\n{web_info[:2000]}")
        elif web_info:
            parts.append(f"\n\n**Fontes Adicionais:**\n{web_info[:1000]}")
        result = "\n".join(parts)
        self.add_to_history("assistant", result)
        self.save_to_github("assistant", result, "deep_dive")
        return result

    def _mode_urgent(self, message: str) -> str:
        query = message.replace("[URGENTE]", "").strip()
        ai = self.call_ai(f"[URGENTE] {query}", "ORION General v6 - Modo URGENTE. Resposta rapida e direta.")
        if not ai:
            web = self.web_search(query)
            ai = web or f"Sem dados especificos sobre '{query}'."
        result = f"🚨 **MODO URGENTE**\n\n**{query}**\n\n{ai}"
        self.add_to_history("assistant", result)
        return result

    def _mode_analyze(self, message: str) -> str:
        query = message.replace("[ANALISAR]", "").strip()
        web = self.web_search(query)
        ai = self.call_ai(f"Analisa detalhadamente: {query}", "ORION General v6 - Modo ANALISE. Detalhado e estruturado.")
        parts = [f"📊 **ANÁLISE DETALHADA**\n\n**Tópico:** {query}\n"]
        if ai:
            parts.append(ai)
        elif web:
            parts.append(web[:2000])
        else:
            parts.append(f"Sem dados suficientes sobre '{query}'.")
        result = "\n".join(parts)
        self.add_to_history("assistant", result)
        return result

    def _mode_compare(self, message: str) -> str:
        query = message.replace("[COMPARAR]", "").strip()
        ai = self.call_ai(f"Compara as opcoes: {query}", "ORION General v6 - Modo COMPARACAO. Tabela comparativa.")
        if not ai:
            web = self.web_search(query)
            ai = web or f"Sem dados para comparar sobre '{query}'."
        result = f"⚖️ **COMPARAÇÃO**\n\n**{query}**\n\n{ai}"
        self.add_to_history("assistant", result)
        return result

    def _mode_risks(self, message: str) -> str:
        query = message.replace("[RISCOS]", "").strip()
        ai = self.call_ai(f"Analisa os riscos de: {query}", "ORION General v6 - Modo RISCOS. Foco em ameacas e mitigacao.")
        if not ai:
            web = self.web_search(query)
            ai = web or f"Sem dados para analisar riscos sobre '{query}'."
        result = f"⚠️ **ANÁLISE DE RISCOS**\n\n**{query}**\n\n{ai}"
        self.add_to_history("assistant", result)
        return result

    def _mode_summary(self, message: str) -> str:
        query = message.replace("[RESUMIR]", "").strip()
        ai = self.call_ai(f"Faz um resumo executivo sobre: {query}", "ORION General v6 - Modo RESUMO. Conciso e direto ao ponto.")
        if not ai:
            web = self.web_search(query)
            ai = web or f"Sem dados para resumir sobre '{query}'."
        result = f"📋 **RESUMO EXECUTIVO**\n\n**{query}**\n\n{ai}"
        self.add_to_history("assistant", result)
        return result

    def _mode_web_research(self, message: str) -> str:
        query = message.replace("[PESQUISAR]", "").strip()
        web = self.web_search(query, max_results=8, fetch_pages=True)
        if web:
            result = f"🔍 **PESQUISA WEB**\n\n**Tópico:** {query}\n\n{web}"
        else:
            ai = self.call_ai(f"Pesquisa sobre: {query}", "ORION General v6 - Pesquisa web com dados atualizados.")
            result = f"🔍 **PESQUISA**\n\n**{query}**\n\n{ai or 'Sem resultados na web.'}"
        self.add_to_history("assistant", result)
        return result

    def _mode_fetch_url(self, message: str) -> str:
        url = message.replace("[FETCH]", "").strip()
        if not url.startswith("http"):
            result = "URL invalida. Usa: `[FETCH] https://exemplo.com`"
        else:
            content = self.fetch_url(url)
            if content:
                result = f"📄 **CONTEUDO FETCHED**\n\n{content}"
            else:
                result = f"Nao foi possivel aceder a: {url}"
        self.add_to_history("assistant", result)
        return result

    def _mode_memory(self, message: str) -> str:
        query = message.replace("[MEMORIA]", "").strip()
        memories = []
        if self.ltm:
            try:
                memories = self.ltm.retrieve(query, limit=5)
            except Exception:
                pass

        if not memories:
            context_lines = self.conversation_history[-6:-1] if len(self.conversation_history) > 1 else []
            parts = [f"🧠 **MEMÓRIA**\n\n**Consulta:** {query}\n"]
            if context_lines:
                parts.append("**Contexto recente:**")
                for m in context_lines[-3:]:
                    role = "Tu" if m["role"] == "user" else "ORION"
                    parts.append(f"- {role}: {m['content'][:100]}...")
            else:
                parts.append("Nenhuma memória encontrada.")
            result = "\n".join(parts)
        else:
            parts = [f"🧠 **MEMÓRIA DE LONGO PRAZO**\n\n**Consulta:** {query}\n"]
            for i, m in enumerate(memories[:5], 1):
                parts.append(f"{i}. **[{m.memory_type}]** {m.content[:200]}...")
            result = "\n".join(parts)

        self.add_to_history("assistant", result)
        return result

    def _fallback_response(self, message: str) -> str:
        return (f"Nao consegui processar: '{message}'\n\n"
                "Sugestoes:\n"
                "- [PESQUISAR] para pesquisa web\n"
                "- [RESUMIR] para resumo\n"
                "- [DEEP DIVE] para analise profunda\n"
                "- Ou reformula a pergunta.")


    def _record_learning(self, query: str, response: str, mode: str):
        """Regista interacao no sistema de aprendizagem"""
        if self.learner:
            try:
                self.learner.record_interaction(
                    query=query,
                    response=response,
                    mode_used=mode,
                    confidence=0.7,
                    tags=[],
                )
            except Exception as e:
                print(f"[ORION] Learning record error: {e}")

        if self.evolution_engine:
            try:
                self.evolution_engine.record_metric("interaction", 1.0)
            except Exception:
                pass

    def record_feedback(self, query: str, response: str, feedback: str):
        """Regista feedback positivo/negativo para aprendizado"""
        if self.learner:
            try:
                self.learner.record_feedback(query, feedback)
                if feedback == "positive":
                    self.learner.record_feedback(query, "positive")
                if self.ltm:
                    self.ltm.store(
                        content=f"Feedback {feedback}: {query[:100]}",
                        memory_type=MemoryType.LESSON if feedback == "negative" else MemoryType.INSIGHT,
                        category="user_feedback",
                        importance=0.7,
                        source="user",
                    )
            except Exception as e:
                print(f"[ORION] Feedback error: {e}")

        if self.evolution_engine:
            try:
                self.evolution_engine.record_metric(
                    "user_satisfaction",
                    1.0 if feedback == "positive" else 0.0,
                )
            except Exception:
                pass

    def get_learning_stats(self) -> Dict:
        """Retorna estatisticas de aprendizagem"""
        stats = {}
        if self.learner:
            try:
                stats["learning"] = self.learner.get_stats()
                stats["summary"] = self.learner.get_learning_summary()
            except Exception:
                pass
        if self.evolution_engine:
            try:
                stats["evolution"] = self.evolution_engine.get_stats()
            except Exception:
                pass
        return stats or {"status": "learning not available"}


# =====================================================
# FASTAPI APP (se disponivel)
# =====================================================

if FASTAPI_AVAILABLE:
    brain = OrionBrain()
    WEB_ROOT = PROJECT_ROOT / "ORION_SYSTEM" / "web_ui"

    class ChatRequest(BaseModel):
        message: str

    class ChatResponse(BaseModel):
        response: str
        mode: str = "general"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print(f"[ORION] Server v6.0 starting on port {PORT}")
        print(f"[ORION] Web UI: {WEB_ROOT}")
        print(f"[ORION] orion/ package: {'IMPORTED' if ORION_IMPORTED else 'NOT AVAILABLE'}")
        yield
        print("[ORION] Server shutting down")

    app = FastAPI(title="ORION General v6.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if WEB_ROOT.exists():
        app.mount("/static", StaticFiles(directory=str(WEB_ROOT)), name="static")

    @app.get("/api/health")
    async def health():
        return {
            "status": "healthy",
            "version": "6.0",
            "orion_package": ORION_IMPORTED,
            "conversations": len(brain.conversation_history),
            "uptime": time.time(),
        }

    @app.post("/api/chat")
    async def chat(req: ChatRequest):
        if not req.message.strip():
            return ChatResponse(response="Por favor, escreve uma mensagem.")

        response_text = brain.think(req.message)
        return ChatResponse(response=response_text)

    @app.post("/api/chat/stream")
    async def chat_stream(req: ChatRequest):
        if not req.message.strip():
            return JSONResponse({"error": "Mensagem vazia"})

        async def generate():
            response_text = brain.think(req.message)
            words = response_text.split(" ")
            for i, word in enumerate(words):
                yield f"data: {word} "
                if i % 3 == 0:
                    yield "\n\n"
                import asyncio
                await asyncio.sleep(0.02)
            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    @app.get("/api/memory")
    async def get_memory(q: str = "", limit: int = 10):
        if brain.ltm and q:
            results = brain.ltm.retrieve(q, limit=limit)
            return {"memories": [{"type": m.memory_type, "content": m.content[:300], "category": m.category} for m in results]}
        return {"memories": [], "total_conversations": len(brain.conversation_history)}

    @app.post("/api/web/search")
    async def web_search_endpoint(req: ChatRequest):
        result = brain.web_search(req.message, fetch_pages=True)
        return {"query": req.message, "results": result or "Sem resultados"}

    class FetchRequest(BaseModel):
        url: str

    @app.post("/api/web/fetch")
    async def fetch_url_endpoint(req: FetchRequest):
        result = brain.fetch_url(req.url)
        return {"url": req.url, "content": result or "Nao foi possivel aceder"}

    @app.get("/api/conversation/history")
    async def conversation_history(limit: int = 20):
        recent = brain.conversation_history[-limit:] if brain.conversation_history else []
        return {"history": recent}

    @app.post("/api/conversation/clear")
    async def clear_conversation():
        brain.conversation_history = []
        return {"status": "cleared"}

    class FeedbackRequest(BaseModel):
        query: str = ""
        response: str = ""
        feedback: str  # "positive" or "negative"

    @app.post("/api/feedback")
    async def feedback(req: FeedbackRequest):
        brain.record_feedback(req.query, req.response, req.feedback)
        return {"status": "ok", "feedback": req.feedback}

    @app.get("/api/learning/stats")
    async def learning_stats():
        return brain.get_learning_stats()

    @app.get("/api/learning/patterns")
    async def learning_patterns():
        if brain.learner:
            try:
                patterns = brain.learner.get_recommendations("")
                return {"patterns": patterns}
            except Exception:
                pass
        return {"patterns": []}

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if not full_path or full_path == "/":
            full_path = "index.html"

        static_file = WEB_ROOT / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))

        # Fallback para index.html (SPA)
        index = WEB_ROOT / "index.html"
        if index.exists():
            return FileResponse(str(index))

        return JSONResponse({"error": "Not found", "path": full_path}, status_code=404)

    def main():
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

else:
    # =====================================================
    # FALLBACK: http.server (sem FastAPI)
    # =====================================================

    from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

    brain = OrionBrain()

    HTML_PAGE = """<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ORION General v6.0</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e; color: #e0e0e0;
            min-height: 100vh; display: flex; flex-direction: column;
        }
        .header {
            background: rgba(0,0,0,0.3); padding: 12px 20px;
            display: flex; align-items: center; justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .header h1 { font-size: 1rem; color: #4ade80; }
        .header .status { font-size: 0.75rem; padding: 4px 10px; border-radius: 12px; }
        .status.online { background: rgba(74,222,128,0.2); color: #4ade80; }
        .status.offline { background: rgba(248,113,113,0.2); color: #f87171; }
        .chat-container {
            flex: 1; overflow-y: auto; padding: 15px 20px;
            display: flex; flex-direction: column; gap: 12px;
        }
        .message {
            max-width: 88%; padding: 12px 16px; border-radius: 12px;
            line-height: 1.5; font-size: 0.9rem;
            animation: fadeIn 0.3s ease;
        }
        .message p { margin: 4px 0; }
        .message pre { background: #0d1117; padding: 12px; border-radius: 8px; overflow-x: auto; margin: 8px 0; }
        .message code { font-size: 0.85rem; }
        .message pre code { background: none; padding: 0; }
        .message ul, .message ol { padding-left: 20px; margin: 4px 0; }
        .message a { color: #4ade80; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .message.user {
            align-self: flex-end; background: #4ade80; color: #000;
            border-bottom-right-radius: 4px;
        }
        .message.user code { background: rgba(0,0,0,0.1); color: #000; }
        .message.user a { color: #1a1a2e; }
        .message.bot {
            align-self: flex-start; background: rgba(255,255,255,0.08);
            border-bottom-left-radius: 4px;
        }
        .message.bot.loading { color: #888; font-style: italic; }
        .input-container {
            padding: 12px 20px; background: rgba(0,0,0,0.3);
            border-top: 1px solid rgba(255,255,255,0.1);
            display: flex; gap: 8px; align-items: center;
        }
        .input-container input {
            flex: 1; padding: 10px 16px; border: 1px solid rgba(255,255,255,0.15);
            border-radius: 20px; background: rgba(255,255,255,0.06);
            color: #fff; font-size: 0.9rem; outline: none;
        }
        .input-container input:focus { border-color: #4ade80; }
        .input-container button {
            padding: 10px 20px; border: none; border-radius: 20px;
            background: #4ade80; color: #000; font-weight: 600; cursor: pointer;
        }
        .input-container button:active { transform: scale(0.95); }
        .quick-actions {
            display: flex; gap: 6px; padding: 8px 20px;
            overflow-x: auto; flex-wrap: wrap;
        }
        .quick-actions button {
            flex-shrink: 0; padding: 6px 12px; border: 1px solid rgba(255,255,255,0.15);
            border-radius: 14px; background: transparent; color: #4ade80;
            font-size: 0.75rem; cursor: pointer;
        }
        .quick-actions button:hover { background: rgba(74,222,128,0.1); }
        .typing-indicator {
            align-self: flex-start; background: rgba(255,255,255,0.08);
            padding: 12px 20px; border-radius: 12px;
            border-bottom-left-radius: 4px;
        }
        .typing-indicator span {
            display: inline-block; width: 8px; height: 8px;
            border-radius: 50%; background: #4ade80;
            margin: 0 2px; animation: typing 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
            30% { opacity: 1; transform: translateY(-4px); }
        }
        .file-upload {
            padding: 8px; border: 1px dashed rgba(255,255,255,0.2);
            border-radius: 12px; cursor: pointer; color: #888;
            font-size: 0.8rem; text-align: center;
        }
        .file-upload:hover { border-color: #4ade80; color: #4ade80; }
        @media (max-width: 600px) {
            .message { max-width: 95%; font-size: 0.85rem; }
            .quick-actions button { font-size: 0.7rem; padding: 5px 10px; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>ORION GENERAL v6.0</h1>
        <span class="status offline" id="status">Desconectado</span>
    </div>
    <div class="chat-container" id="chat">
        <div class="message bot">
            <p>General operacional. <strong>Versao 6.0</strong></p>
            <p>Modos disponiveis:</p>
            <ul>
                <li><code>[DEEP DIVE]</code> Auditoria completa</li>
                <li><code>[URGENTE]</code> Resposta rapida</li>
                <li><code>[ANALISAR]</code> Analise detalhada</li>
                <li><code>[COMPARAR]</code> Comparacao</li>
                <li><code>[RISCOS]</code> Analise de riscos</li>
                <li><code>[RESUMIR]</code> Resumo executivo</li>
                <li><code>[PESQUISAR]</code> Pesquisa web</li>
                <li><code>[MEMORIA]</code> Memoria</li>
            </ul>
        </div>
    </div>
    <div class="quick-actions">
        <button onclick="sendQuick('[DEEP DIVE] ')">DEEP DIVE</button>
        <button onclick="sendQuick('[URGENTE] ')">URGENTE</button>
        <button onclick="sendQuick('[ANALISAR] ')">ANALISAR</button>
        <button onclick="sendQuick('[COMPARAR] ')">COMPARAR</button>
        <button onclick="sendQuick('[RISCOS] ')">RISCOS</button>
        <button onclick="sendQuick('[RESUMIR] ')">RESUMIR</button>
        <button onclick="sendQuick('[PESQUISAR] ')">PESQUISAR</button>
        <button onclick="sendQuick('[MEMORIA] ')">MEMORIA</button>
    </div>
    <div class="input-container">
        <label class="file-upload" title="Anexar ficheiro" id="fileLabel">📎</label>
        <input type="file" id="fileInput" style="display:none" accept=".txt,.py,.js,.html,.css,.json,.md,.csv">
        <input type="text" id="userInput" placeholder="Escreve a tua mensagem..." autocomplete="off">
        <button onclick="sendMessage()">Enviar</button>
    </div>
    <script>
        const chat = document.getElementById('chat');
        const input = document.getElementById('userInput');
        const status = document.getElementById('status');
        const fileInput = document.getElementById('fileInput');
        const fileLabel = document.getElementById('fileLabel');
        let fileContent = null;
        let fileName = null;

        // Markdown config
        marked.setOptions({
            breaks: true,
            gfm: true,
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try { return hljs.highlight(code, {language: lang}).value; } catch(e) {}
                }
                return hljs.highlightAuto(code).value;
            }
        });

        fileLabel.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            fileName = file.name;
            const reader = new FileReader();
            reader.onload = (ev) => {
                fileContent = ev.target.result;
                fileLabel.textContent = `📄 ${fileName}`;
            };
            reader.readAsText(file);
        });

        async function checkConnection() {
            try {
                const res = await fetch('/api/health');
                if (res.ok) {
                    status.textContent = 'Online';
                    status.className = 'status online';
                } else {
                    status.textContent = 'Erro';
                    status.className = 'status offline';
                }
            } catch(e) {
                status.textContent = 'Offline';
                status.className = 'status offline';
            }
        }

        function addMessage(text, isUser = false) {
            const div = document.createElement('div');
            div.className = 'message ' + (isUser ? 'user' : 'bot');
            if (isUser) {
                div.textContent = text;
            } else {
                div.innerHTML = marked.parse(text);
                div.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
            return div;
        }

        function addTyping() {
            const div = document.createElement('div');
            div.className = 'typing-indicator';
            div.id = 'typing';
            div.innerHTML = '<span></span><span></span><span></span>';
            chat.appendChild(div);
            chat.scrollTop = chat.scrollHeight;
        }

        function removeTyping() {
            const el = document.getElementById('typing');
            if (el) el.remove();
        }

        function sendQuick(text) {
            input.value = text;
            sendMessage();
        }

        async function sendMessage() {
            let text = input.value.trim();
            if (!text && !fileContent) return;

            if (fileContent) {
                text = `[Ficheiro: ${fileName}]\n` + "```" + `\n${fileContent.slice(0, 3000)}\n` + "```" + `\n\n${text || 'Analisa este ficheiro.'}`;
                fileContent = null;
                fileName = null;
                fileLabel.textContent = '📎';
                fileInput.value = '';
            }

            addMessage(text, true);
            input.value = '';
            addTyping();

            try {
                const res = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: text })
                });
                const data = await res.json();
                removeTyping();
                addMessage(data.response || 'Sem resposta');
            } catch(e) {
                removeTyping();
                addMessage('Erro de conexao com o servidor.');
            }
        }

        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Ctrl+K to focus input
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                input.focus();
            }
        });

        checkConnection();
        setInterval(checkConnection, 30000);
    </script>
</body>
</html>"""

    class ORIONHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            print(f"[ORION] {format % args}")

        def do_GET(self):
            if self.path == "/api/health":
                self.send_json({
                    "status": "healthy",
                    "version": "6.0",
                    "orion_package": ORION_IMPORTED,
                })
            elif self.path in ("/", "/index.html"):
                content = HTML_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                # Tenta servir ficheiros estáticos
                static_path = WEB_ROOT / self.path.lstrip("/")
                if static_path.exists() and static_path.is_file():
                    content = static_path.read_bytes()
                    ctype = "application/octet-stream"
                    if self.path.endswith(".html"):
                        ctype = "text/html; charset=utf-8"
                    elif self.path.endswith(".css"):
                        ctype = "text/css"
                    elif self.path.endswith(".js"):
                        ctype = "application/javascript"
                    elif self.path.endswith(".json"):
                        ctype = "application/json"
                    elif self.path.endswith(".png"):
                        ctype = "image/png"
                    elif self.path.endswith(".svg"):
                        ctype = "image/svg+xml"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", len(content))
                    self.end_headers()
                    self.wfile.write(content)
                else:
                    self.send_error(404)

        def do_POST(self):
            if self.path == "/api/chat":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    message = data.get("message", "")
                    brain.save_to_github("user", message, "cloud")
                    response = brain.think(message)
                    brain.save_to_github("assistant", response, "cloud")
                    self.send_json({"response": response})
                except Exception as e:
                    self.send_json({"response": f"Erro: {str(e)}"})
            elif self.path == "/api/web/search":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    results = brain.web_search(data.get("message", ""))
                    self.send_json({"query": data.get("message", ""), "results": results or "Sem resultados"})
                except Exception as e:
                    self.send_json({"error": str(e)})
            elif self.path == "/api/conversation/history":
                limit = int(self.headers.get("X-Limit", 20))
                recent = brain.conversation_history[-limit:] if brain.conversation_history else []
                self.send_json({"history": recent})
            elif self.path == "/api/conversation/clear":
                brain.conversation_history = []
                self.send_json({"status": "cleared"})
            elif self.path == "/api/memory":
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                try:
                    data = json.loads(body)
                    q = data.get("query", "")
                    if brain.ltm and q:
                        results = brain.ltm.retrieve(q, limit=10)
                        self.send_json({"memories": [{"type": m.memory_type, "content": m.content[:300]} for m in results]})
                    else:
                        self.send_json({"memories": []})
                except Exception:
                    self.send_json({"memories": [], "total": len(brain.conversation_history)})
            else:
                self.send_error(404)

        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Limit")
            self.end_headers()

        def send_json(self, data):
            response = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", len(response))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response)

    def main():
        print(f"ORION Cloud Server v6.0 - Port {PORT}")
        print(f"Web UI: {WEB_ROOT}")
        print(f"orion/ package: {'IMPORTED' if ORION_IMPORTED else 'NOT AVAILABLE'}")
        server = ThreadingHTTPServer(("0.0.0.0", PORT), ORIONHandler)
        print("Server running!")
        server.serve_forever()


if __name__ == "__main__":
    main()
