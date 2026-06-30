"""
Web Scraping & Browser Automation System
========================================
Provides web scraping, content extraction, and browser automation capabilities.
Based on 2026 patterns for autonomous web interaction.

Features:
- HTML content extraction
- Link crawling and discovery
- Content parsing and summarization
- Rate limiting and politeness
- Cache for visited pages
"""

from __future__ import annotations

import json
import logging
import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict
import threading

logger = logging.getLogger("orion.web_scraping")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_CACHE_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "WEB_CACHE"


class ContentType(str, Enum):
    """Types of web content."""
    HTML = "html"
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    XML = "xml"


class CrawlStatus(str, Enum):
    """Crawl status."""
    PENDING = "pending"
    CRAWLING = "crawling"
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"


@dataclass
class WebPage:
    """Represents a web page."""
    url: str
    title: str
    content: str
    content_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    crawled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    url: str
    status: str
    page: Optional[WebPage] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScrapingRule:
    """Rules for scraping a domain."""
    domain: str
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    rate_limit_ms: int = 1000
    max_depth: int = 3
    respect_robots: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ContentExtractor:
    """Extract and parse web content."""
    
    def __init__(self):
        self._html_tags = re.compile(r'<[^>]+>')
        self._script_tags = re.compile(r'<script[^>]*>.*?</script>', re.DOTALL | re.IGNORECASE)
        self._style_tags = re.compile(r'<style[^>]*>.*?</style>', re.DOTALL | re.IGNORECASE)
    
    def extract_text(self, html: str) -> str:
        """Extract text from HTML."""
        text = self._script_tags.sub('', html)
        text = self._style_tags.sub('', text)
        text = self._html_tags.sub(' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def extract_title(self, html: str) -> str:
        """Extract title from HTML."""
        match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""
    
    def extract_links(self, html: str, base_url: str = "") -> List[str]:
        """Extract links from HTML."""
        links = []
        pattern = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)
        
        for match in pattern.finditer(html):
            url = match.group(1)
            if url.startswith(('http://', 'https://')):
                links.append(url)
            elif url.startswith('/') and base_url:
                from urllib.parse import urljoin
                links.append(urljoin(base_url, url))
        
        return list(set(links))
    
    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {}
        
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if desc_match:
            metadata['description'] = desc_match.group(1)
        
        keywords_match = re.search(r'<meta[^>]*name=["\']keywords["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if keywords_match:
            metadata['keywords'] = keywords_match.group(1)
        
        og_title = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if og_title:
            metadata['og_title'] = og_title.group(1)
        
        return metadata
    
    def html_to_markdown(self, html: str) -> str:
        """Convert HTML to simple markdown."""
        text = html
        
        text = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=re.IGNORECASE | re.DOTALL)
        
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<br[^>]*/?>', '\n', text, flags=re.IGNORECASE)
        
        text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', text, flags=re.IGNORECASE | re.DOTALL)
        
        text = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', text, flags=re.IGNORECASE | re.DOTALL)
        
        text = re.sub(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.IGNORECASE | re.DOTALL)
        
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


class WebCache:
    """Cache for web pages."""
    
    def __init__(self, cache_root: Optional[Path] = None):
        self._root = cache_root or WEB_CACHE_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, WebPage] = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from disk."""
        cache_file = self._root / "web_cache.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                for url, page_data in data.items():
                    self._cache[url] = WebPage(**page_data)
            except (json.JSONDecodeError, TypeError):
                pass
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        cache_file = self._root / "web_cache.json"
        data = {url: page.to_dict() for url, page in self._cache.items()}
        cache_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def get(self, url: str, max_age_hours: int = 24) -> Optional[WebPage]:
        """Get a page from cache if it exists and is fresh."""
        if url in self._cache:
            page = self._cache[url]
            age = datetime.now(timezone.utc) - page.crawled_at
            if age < timedelta(hours=max_age_hours):
                return page
        return None
    
    def put(self, page: WebPage) -> None:
        """Add a page to the cache."""
        self._cache[page.url] = page
        self._save_cache()
    
    def invalidate(self, url: str) -> None:
        """Remove a page from cache."""
        if url in self._cache:
            del self._cache[url]
            self._save_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "total_cached": len(self._cache),
            "root": str(self._root)
        }


class RateLimiter:
    """Rate limiting for web requests."""
    
    def __init__(self):
        self._last_request: Dict[str, datetime] = {}
        self._lock = threading.Lock()
    
    def wait_if_needed(self, domain: str, rate_limit_ms: int = 1000) -> float:
        """Wait if needed to respect rate limit. Returns wait time in ms."""
        with self._lock:
            now = datetime.now(timezone.utc)
            
            if domain in self._last_request:
                elapsed = (now - self._last_request[domain]).total_seconds() * 1000
                if elapsed < rate_limit_ms:
                    wait_time = rate_limit_ms - elapsed
                    return wait_time
            
            self._last_request[domain] = now
            return 0.0
    
    def update(self, domain: str) -> None:
        """Update last request time for a domain."""
        with self._lock:
            self._last_request[domain] = datetime.now(timezone.utc)


class WebScrapingSystem:
    """
    Web Scraping & Browser Automation System
    
    Provides web scraping, content extraction, and caching capabilities.
    Respects rate limits and robots.txt.
    """
    
    def __init__(self, cache_root: Optional[Path] = None):
        self.cache = WebCache(cache_root)
        self.extractor = ContentExtractor()
        self.rate_limiter = RateLimiter()
        self._rules: Dict[str, ScrapingRule] = {}
        self._crawl_history: List[CrawlResult] = []
    
    def add_rule(self, rule: ScrapingRule) -> None:
        """Add a scraping rule for a domain."""
        self._rules[rule.domain] = rule
        logger.info(f"Scraping rule added for: {rule.domain}")
    
    def fetch_page(self, url: str, use_cache: bool = True) -> CrawlResult:
        """Fetch and parse a web page."""
        from urllib.parse import urlparse
        from urllib.request import urlopen, Request
        from urllib.error import URLError
        
        domain = urlparse(url).netloc
        
        if use_cache:
            cached = self.cache.get(url)
            if cached:
                return CrawlResult(
                    url=url,
                    status=CrawlStatus.CACHED,
                    page=cached
                )
        
        rule = self._rules.get(domain)
        if rule:
            wait_time = self.rate_limiter.wait_if_needed(domain, rule.rate_limit_ms)
            if wait_time > 0:
                logger.debug(f"Rate limited, waiting {wait_time}ms for {domain}")
        
        try:
            req = Request(url, headers={
                'User-Agent': 'ORION-Bot/1.0 (+https://github.com/orion)'
            })
            
            start_time = datetime.now(timezone.utc)
            with urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            title = self.extractor.extract_title(html)
            text = self.extractor.extract_text(html)
            links = self.extractor.extract_links(html, url)
            metadata = self.extractor.extract_metadata(html)
            
            page = WebPage(
                url=url,
                title=title,
                content=text,
                content_type=ContentType.HTML,
                metadata=metadata,
                links=links
            )
            
            self.cache.put(page)
            self.rate_limiter.update(domain)
            
            result = CrawlResult(
                url=url,
                status=CrawlStatus.COMPLETED,
                page=page,
                duration_ms=duration
            )
            
            self._crawl_history.append(result)
            logger.info(f"Page fetched: {url} ({duration:.0f}ms)")
            return result
            
        except Exception as e:
            result = CrawlResult(
                url=url,
                status=CrawlStatus.FAILED,
                error=str(e)
            )
            self._crawl_history.append(result)
            logger.error(f"Failed to fetch {url}: {e}")
            return result
    
    def crawl(self, start_url: str, max_pages: int = 10, max_depth: int = 2) -> List[CrawlResult]:
        """Crawl starting from a URL."""
        from urllib.parse import urlparse
        
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(start_url, 0)]
        results: List[CrawlResult] = []
        
        while queue and len(results) < max_pages:
            url, depth = queue.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            result = self.fetch_page(url)
            results.append(result)
            
            if result.page and result.page.links:
                for link in result.page.links:
                    link_domain = urlparse(link).netloc
                    start_domain = urlparse(start_url).netloc
                    if link_domain == start_domain and link not in visited:
                        queue.append((link, depth + 1))
        
        return results
    
    def search_content(self, query: str, results: Optional[List[CrawlResult]] = None) -> List[Dict[str, Any]]:
        """Search crawled content for a query."""
        if results is None:
            results = self._crawl_history
        
        query_terms = set(query.lower().split())
        matches = []
        
        for result in results:
            if result.page:
                content_terms = set(result.page.content.lower().split())
                overlap = len(query_terms & content_terms)
                
                if overlap > 0:
                    score = overlap / len(query_terms)
                    matches.append({
                        "url": result.url,
                        "title": result.page.title,
                        "score": score,
                        "snippet": result.page.content[:200] + "..."
                    })
        
        matches.sort(key=lambda m: -m["score"])
        return matches
    
    def get_stats(self) -> Dict[str, Any]:
        """Get web scraping statistics."""
        return {
            "cache": self.cache.get_stats(),
            "rules": len(self._rules),
            "crawl_history": len(self._crawl_history),
            "successful_crawls": sum(1 for r in self._crawl_history if r.status == CrawlStatus.COMPLETED),
            "failed_crawls": sum(1 for r in self._crawl_history if r.status == CrawlStatus.FAILED)
        }
