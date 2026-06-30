"""
ORION General Agent - Web Scraping
===================================
Sistema de pesquisa na web em tempo real.

Capacidades:
- Pesquisa na web via DuckDuckGo (sem API key)
- Extração de conteúdo de páginas web
- Análise de fontes confiáveis
- Cache de resultados
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus
import urllib.request
import urllib.error
import ssl


@dataclass
class WebResult:
    """Resultado de pesquisa web"""
    id: str
    title: str
    url: str
    snippet: str
    source: str
    timestamp: str


@dataclass
class WebPage:
    """Página web extraída"""
    url: str
    title: str
    content: str
    extracted_at: str


@dataclass
class SearchCache:
    """Cache de pesquisa"""
    query: str
    results: List[WebResult]
    timestamp: str


class WebScraper:
    """
    Sistema de Web Scraping do General
    ===================================
    
    Pesquisa na web:
    1. Usa DuckDuckGo (sem API key)
    2. Extrai conteúdo de páginas
    3. Cacheia resultados
    4. Analisa fontes confiáveis
    """
    
    TRUSTED_DOMAINS = [
        "gov", "edu", "org", "mil",
        "wikipedia.org", "bbc.com", "reuters.com",
        "who.int", "fao.org", "un.org",
        "pt.wikipedia.org", "rtp.pt", "publique.pt",
    ]
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data" / "web_cache")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_file = self.data_dir / "search_cache.json"
        self.cache: List[SearchCache] = []
        
        self._load_cache()
        
        # SSL context para HTTPS
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def _load_cache(self):
        """Carrega cache do disco"""
        if self.cache_file.exists():
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.cache = [SearchCache(**c) for c in data]
    
    def _save_cache(self):
        """Guarda cache no disco"""
        # Mantém apenas últimos 100 items
        if len(self.cache) > 100:
            self.cache = self.cache[-100:]
        
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in self.cache], f, ensure_ascii=False, indent=2)
    
    def _generate_id(self, content: str) -> str:
        """Gera ID único"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _fetch_url(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Busca conteúdo de uma URL
        
        Args:
            url: URL para buscar
            timeout: Timeout em segundos
        
        Returns:
            Conteúdo HTML ou None
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=timeout, context=self.ssl_context) as response:
                return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Erro ao buscar {url}: {e}")
            return None
    
    def _extract_text(self, html: str) -> str:
        """Extrai texto do HTML"""
        # Remove scripts e estilos
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # Remove tags HTML
        text = re.sub(r'<[^>]+>', ' ', html)
        
        # Remove espaços extras
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:5000]  # Limita a 5000 caracteres
    
    def _extract_title(self, html: str) -> str:
        """Extrai título do HTML"""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]
        return "Sem título"
    
    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        """
        Pesquisa na web via DuckDuckGo
        
        Args:
            query: Termo de pesquisa
            max_results: Máximo de resultados
        
        Returns:
            Lista de resultados
        """
        # Verifica cache
        cached = self._get_cached(query)
        if cached:
            return cached[:max_results]
        
        results = []
        
        try:
            # DuckDuckGo HTML search
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            html = self._fetch_url(search_url)
            
            if html:
                # Extrai resultados
                # Padrão para resultados DuckDuckGo
                result_pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>'
                snippet_pattern = r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
                
                urls = re.findall(result_pattern, html, re.DOTALL)
                snippets = re.findall(snippet_pattern, html, re.DOTALL)
                
                for i, (url, title) in enumerate(urls[:max_results]):
                    # Limpa URL (remove tracking)
                    if 'uddg=' in url:
                        url = re.search(r'uddg=([^&]+)', url)
                        if url:
                            url = urllib.request.unquote(url.group(1))
                        else:
                            continue
                    
                    # Limpa título
                    title = re.sub(r'<[^>]+>', '', title).strip()
                    
                    # Obtém snippet
                    snippet = ""
                    if i < len(snippets):
                        snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                    
                    result = WebResult(
                        id=self._generate_id(url),
                        title=title[:200],
                        url=url,
                        snippet=snippet[:500],
                        source=self._extract_domain(url),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    results.append(result)
        
        except Exception as e:
            print(f"Erro na pesquisa: {e}")
        
        # Cacheia resultados
        if results:
            self._cache_results(query, results)
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extrai domínio da URL"""
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        if match:
            return match.group(1)
        return url
    
    def _is_trusted(self, domain: str) -> bool:
        """Verifica se o domínio é confiável"""
        return any(trusted in domain for trusted in self.TRUSTED_DOMAINS)
    
    def _get_cached(self, query: str) -> Optional[List[WebResult]]:
        """Obtém resultados do cache"""
        for cache_entry in self.cache:
            if cache_entry.query.lower() == query.lower():
                # Verifica se não expirou (24 horas)
                cached_time = datetime.fromisoformat(cache_entry.timestamp.replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - cached_time).total_seconds() < 86400:
                    return cache_entry.results
        return None
    
    def _cache_results(self, query: str, results: List[WebResult]):
        """Cacheia resultados"""
        cache_entry = SearchCache(
            query=query,
            results=results,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.cache.append(cache_entry)
        self._save_cache()
    
    def fetch_page(self, url: str) -> Optional[WebPage]:
        """
        Busca e extrai conteúdo de uma página
        
        Args:
            url: URL da página
        
        Returns:
            Página extraída ou None
        """
        html = self._fetch_url(url)
        if not html:
            return None
        
        title = self._extract_title(html)
        content = self._extract_text(html)
        
        return WebPage(
            url=url,
            title=title,
            content=content,
            extracted_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def research_topic(self, topic: str, max_sources: int = 5) -> Dict:
        """
        Pesquisa completa sobre um tópico
        
        Args:
            topic: Tópico para pesquisar
            max_sources: Máximo de fontes
        
        Returns:
            Resultado da pesquisa
        """
        # Pesquisa na web
        results = self.search(topic, max_results=max_sources)
        
        # Analisa fontes
        trusted_results = []
        other_results = []
        
        for result in results:
            if self._is_trusted(result.source):
                trusted_results.append(result)
            else:
                other_results.append(result)
        
        # Busca conteúdo das páginas confiáveis
        full_content = []
        for result in trusted_results[:3]:
            page = self.fetch_page(result.url)
            if page:
                full_content.append({
                    "url": result.url,
                    "title": page.title,
                    "content": page.content[:2000],
                })
        
        return {
            "query": topic,
            "total_results": len(results),
            "trusted_sources": len(trusted_results),
            "results": [asdict(r) for r in results],
            "full_content": full_content,
            "summary": self._generate_summary(topic, results),
        }
    
    def _generate_summary(self, topic: str, results: List[WebResult]) -> str:
        """Gera resumo da pesquisa"""
        if not results:
            return f"Nenhum resultado encontrado para '{topic}'"
        
        summary = f"Pesquisa sobre '{topic}':\n\n"
        summary += f"Encontrados {len(results)} resultados.\n\n"
        
        # Destaca fontes confiáveis
        trusted = [r for r in results if self._is_trusted(r.source)]
        if trusted:
            summary += "Fontes confiáveis encontradas:\n"
            for r in trusted[:3]:
                summary += f"- {r.title} ({r.source})\n"
        
        return summary
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas"""
        return {
            "cached_queries": len(self.cache),
            "trusted_domains": len(self.TRUSTED_DOMAINS),
        }


# Instância global
_scraper = None


def get_web_scraper(data_dir: str = None) -> WebScraper:
    """Retorna instância global do scraper"""
    global _scraper
    if _scraper is None:
        _scraper = WebScraper(data_dir)
    return _scraper
