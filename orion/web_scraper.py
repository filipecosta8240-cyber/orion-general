"""
ORION General Agent - Web Scraping v2
======================================
Pesquisa web em tempo real com múltiplos motores de busca.
Capacidades:
- DuckDuckGo, Google, Bing, Mojeek, Brave (sem API key)
- Extração de conteúdo de qualquer URL
- Fetch de páginas completas
- Cache inteligente
"""

import json
import hashlib
import re
import time
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus, urlparse
import urllib.request
import urllib.error
import ssl

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
]


@dataclass
class WebResult:
    id: str
    title: str
    url: str
    snippet: str
    source: str
    engine: str = ""


@dataclass
class WebPage:
    url: str
    title: str
    content: str
    extracted_at: str
    word_count: int = 0


class WebScraper:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(Path(__file__).parent.parent / "data" / "web_cache")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.data_dir / "search_cache.json"
        self.cache: List[dict] = []
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self.cache = []

    def _save_cache(self):
        if len(self.cache) > 200:
            self.cache = self.cache[-200:]
        self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")

    def _fetch(self, url: str, timeout: int = 12) -> Optional[str]:
        for attempt in range(3):
            try:
                ua = random.choice(USER_AGENTS)
                req = urllib.request.Request(url, headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
                })
                with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
                    raw = resp.read()
                    # Detect encoding
                    content_type = resp.headers.get("Content-Type", "")
                    enc = "utf-8"
                    if "charset=" in content_type:
                        enc = content_type.split("charset=")[-1].split(";")[0].strip()
                    try:
                        return raw.decode(enc, errors="replace")
                    except Exception:
                        return raw.decode("utf-8", errors="replace")
            except Exception as e:
                if attempt < 2:
                    time.sleep(1.5)
        return None

    def _extract_text(self, html: str, max_chars: int = 8000) -> str:
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<aside[^>]*>.*?</aside>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<form[^>]*>.*?</form>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<svg[^>]*>.*?</svg>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<[ou]l[^>]*>.*?</[ou]l>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<a[^>]*class="[^"]*sidebar[^"]*"[^>]*>.*?</a>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove comentarios HTML
        html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
        # Decode entidades HTML
        html = html.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        html = html.replace('&quot;', '"').replace('&#39;', "'").replace('&#x27;', "'")
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        # Split em paragrafos e filtra linhas curtas
        paragraphs = re.split(r'</?p[^>]*>|</?div[^>]*>|<br\s*/?>|</?h[1-6][^>]*>', text)
        lines = []
        for p in paragraphs:
            p = p.strip()
            p = re.sub(r'\s+', ' ', p)
            if len(p) > 40:
                lines.append(p)
        text = '\n\n'.join(lines)
        return text[:max_chars]

    def _extract_title(self, html: str) -> str:
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip()[:200] if m else "Sem título"

    def _gen_id(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()[:10]

    def _domain(self, url: str) -> str:
        m = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return m.group(1) if m else url

    def _get_cached(self, query: str) -> Optional[List[dict]]:
        for entry in self.cache:
            if entry.get("q", "").lower() == query.lower():
                t = entry.get("t", "")
                if t:
                    try:
                        ct = datetime.fromisoformat(t.replace('Z', '+00:00'))
                        if (datetime.now(timezone.utc) - ct).total_seconds() < 3600:
                            return entry.get("r", [])
                    except Exception:
                        pass
        return None

    def _cache_results(self, query: str, results: List[dict]):
        self.cache.append({"q": query, "r": results, "t": datetime.now(timezone.utc).isoformat()})
        self._save_cache()

    # ========== SEARCH ENGINES ==========

    def _search_duckduckgo(self, query: str, max_results: int) -> List[dict]:
        results = []
        html = self._fetch(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
        if not html:
            return results
        for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL):
            if len(results) >= max_results:
                break
            url_raw, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if 'uddg=' in url_raw:
                u = re.search(r'uddg=([^&]+)', url_raw)
                url = urllib.request.unquote(u.group(1)) if u else ""
            else:
                url = url_raw
            if not url:
                continue
            results.append({"title": title[:200], "url": url, "snippet": "", "source": self._domain(url), "engine": "duckduckgo"})
        # Get snippets
        snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
        for i, s in enumerate(snippets[:len(results)]):
            results[i]["snippet"] = re.sub(r'<[^>]+>', '', s).strip()[:400]
        return results

    def _search_google(self, query: str, max_results: int) -> List[dict]:
        results = []
        html = self._fetch(f"https://www.google.com/search?q={quote_plus(query)}&hl=pt-PT")
        if not html:
            return results
        for m in re.finditer(r'<a[^>]*href="(/url\?q=[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            if len(results) >= max_results:
                break
            href = m.group(1)
            u = re.search(r'q=([^&]+)', href)
            url = urllib.request.unquote(u.group(1)) if u else ""
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if not url or not title or "google.com" in url:
                continue
            results.append({"title": title[:200], "url": url, "snippet": "", "source": self._domain(url), "engine": "google"})
        # Get snippets from div.VwiC3b or span.st
        snippets = re.findall(r'<div[^>]*class="[^"]*VwiC3b[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        for i, s in enumerate(snippets[:len(results)]):
            results[i]["snippet"] = re.sub(r'<[^>]+>', '', s).strip()[:400]
        if not snippets:
            snippets2 = re.findall(r'<span[^>]*class="[^"]*st[^"]*"[^>]*>(.*?)</span>', html, re.DOTALL)
            for i, s in enumerate(snippets2[:len(results)]):
                results[i]["snippet"] = re.sub(r'<[^>]+>', '', s).strip()[:400]
        return results

    def _search_bing(self, query: str, max_results: int) -> List[dict]:
        results = []
        html = self._fetch(f"https://www.bing.com/search?q={quote_plus(query)}&setlang=pt-PT")
        if not html:
            return results
        for m in re.finditer(r'<li[^>]*class="[^"]*b_algo[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            if len(results) >= max_results:
                break
            url, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if not url or not title:
                continue
            results.append({"title": title[:200], "url": url, "snippet": "", "source": self._domain(url), "engine": "bing"})
        snippets = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        for i, s in enumerate(snippets[:len(results)]):
            t = re.sub(r'<[^>]+>', '', s).strip()
            if len(t) > 30:
                results[i]["snippet"] = t[:400]
        return results

    def _search_mojeek(self, query: str, max_results: int) -> List[dict]:
        results = []
        html = self._fetch(f"https://www.mojeek.com/search?q={quote_plus(query)}")
        if not html:
            return results
        for m in re.finditer(r'<a[^>]*class="[^"]*title[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            if len(results) >= max_results:
                break
            url, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if not url or not title or url.startswith("#"):
                continue
            results.append({"title": title[:200], "url": url, "snippet": "", "source": self._domain(url), "engine": "mojeek"})
        snippets = re.findall(r'<p[^>]*class="[^"]*s[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)
        for i, s in enumerate(snippets[:len(results)]):
            results[i]["snippet"] = re.sub(r'<[^>]+>', '', s).strip()[:400]
        return results

    def _search_brave(self, query: str, max_results: int) -> List[dict]:
        results = []
        html = self._fetch(f"https://search.brave.com/search?q={quote_plus(query)}")
        if not html:
            return results
        for m in re.finditer(r'<a[^>]*class="[^"]*snippet-title[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            if len(results) >= max_results:
                break
            url, title = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if not url or not title:
                continue
            results.append({"title": title[:200], "url": url, "snippet": "", "source": self._domain(url), "engine": "brave"})
        return results

    # ========== PUBLIC API ==========

    def search(self, query: str, max_results: int = 8) -> List[WebResult]:
        cached = self._get_cached(query)
        if cached:
            return [WebResult(**r) for r in cached[:max_results]]

        all_results: List[dict] = []
        seen_urls = set()

        engines = [
            ("duckduckgo", self._search_duckduckgo),
            ("google", self._search_google),
            ("bing", self._search_bing),
            ("mojeek", self._search_mojeek),
            ("brave", self._search_brave),
        ]

        random.shuffle(engines)

        for name, engine_fn in engines:
            try:
                engine_results = engine_fn(query, max_results)
                for r in engine_results:
                    if r["url"] not in seen_urls and r["url"]:
                        seen_urls.add(r["url"])
                        all_results.append(r)
                if len(all_results) >= max_results:
                    break
            except Exception as e:
                continue

        # Wikipedia fallback
        if len(all_results) < 3:
            try:
                wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
                wiki = self._fetch(wiki_url)
                if wiki:
                    data = json.loads(wiki)
                    if data.get("extract"):
                        all_results.append({
                            "title": data.get("title", query),
                            "url": f"https://en.wikipedia.org/wiki/{quote_plus(data.get('title', query))}",
                            "snippet": data["extract"][:500],
                            "source": "wikipedia.org",
                            "engine": "wikipedia",
                        })
            except Exception:
                pass

        if not all_results:
            try:
                search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote_plus(query)}&format=json&srlimit=3"
                wiki_search = self._fetch(search_url)
                if wiki_search:
                    data = json.loads(wiki_search)
                    for r in data.get("query", {}).get("search", []):
                        snippet = re.sub(r'<[^>]+>', '', r.get("snippet", ""))[:400]
                        all_results.append({
                            "title": r.get("title", ""),
                            "url": f"https://en.wikipedia.org/wiki/{quote_plus(r.get('title', ''))}",
                            "snippet": snippet,
                            "source": "wikipedia.org",
                            "engine": "wikipedia",
                        })
            except Exception:
                pass

        results = []
        for r in all_results[:max_results]:
            web_result = WebResult(
                id=self._gen_id(r["url"]),
                title=r.get("title", "")[:200],
                url=r["url"],
                snippet=r.get("snippet", "")[:500],
                source=r.get("source", self._domain(r["url"])),
                engine=r.get("engine", "unknown"),
            )
            results.append(web_result)

        if results:
            self._cache_results(query, [asdict(r) for r in results])

        return results

    def fetch_page(self, url: str, max_chars: int = 8000) -> Optional[WebPage]:
        html = self._fetch(url, timeout=15)
        if not html:
            return None
        title = self._extract_title(html)
        content = self._extract_text(html, max_chars)
        words = len(content.split())
        return WebPage(
            url=url,
            title=title,
            content=content,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            word_count=words,
        )

    def research_topic(self, topic: str, max_sources: int = 5, fetch_content: bool = True) -> Dict:
        results = self.search(topic, max_results=max_sources)

        full_content = []
        if fetch_content:
            for r in results[:3]:
                page = self.fetch_page(r.url, max_chars=3000)
                if page:
                    full_content.append({
                        "url": r.url,
                        "title": page.title,
                        "content": page.content,
                        "words": page.word_count,
                    })

        return {
            "query": topic,
            "total_results": len(results),
            "results": [asdict(r) for r in results],
            "full_content": full_content,
        }

    def get_stats(self) -> Dict:
        return {"cached_queries": len(self.cache), "engines": ["duckduckgo", "google", "bing", "mojeek", "brave", "wikipedia"]}


_scraper = None


def get_web_scraper(data_dir: str = None) -> WebScraper:
    global _scraper
    if _scraper is None:
        _scraper = WebScraper(data_dir)
    return _scraper
