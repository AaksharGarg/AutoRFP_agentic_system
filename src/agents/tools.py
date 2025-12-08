# src/agent/tools.py
import os
import asyncio
from typing import Callable, Dict, Any, Optional
from src.crawler.frontier import Frontier
from src.crawler.fetcher import Fetcher, FetchResult
from src.crawler.extractor import Extractor

class ToolRegistry:
    def __init__(self, frontier: Frontier, fetcher: Fetcher, extractor: Extractor):
        self.frontier = frontier
        self.fetcher = fetcher
        self.extractor = extractor
        self._map = {
            "frontier.add": self.frontier_add,
            "frontier.pop": self.frontier_pop,
            "fetcher.fetch_html": self.fetch_html,
            "extractor.extract_all": self.extract_all,
            "downloader.download_binary": self.download_binary,
            "noop": self.noop,
            "log": self.log,
        }

    def get(self, name: str):
        return self._map.get(name)

    def register(self, name: str, fn: Callable):
        self._map[name] = fn

    # Tools
    def frontier_add(self, url: str, priority: int = 1, depth: int = 0, meta: dict = None):
        return {"added": self.frontier.add(url, priority=priority, depth=depth, meta=meta or {})}

    def frontier_pop(self):
        return self.frontier.pop()

    def frontier_pop(self):
        return self.frontier.pop()

    async def fetch_html(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        fr: FetchResult = await self.fetcher.fetch_html(url, timeout=timeout)
        return {
            "url": fr.url,
            "final_url": fr.final_url,
            "status": fr.status,
            "content_type": fr.content_type,
            "html_snippet": (fr.html or "")[:10000],
        }

    async def extract_all(self, url: str, html: Optional[str] = None) -> Any:
        # extractor.extract_all returns list of RFP dictionaries
        if html is None:
            fr: FetchResult = await self.fetcher.fetch_html(url)
            html = fr.html or ""
        results = await self.extractor.extract_all(url, html)
        return results

    async def download_binary(self, url: str, dst_path: str) -> Dict[str, Any]:
        ok = await self.fetcher.download_binary(url, dst_path)
        return {"success": ok, "path": dst_path if ok else None}

    def noop(self, **kwargs):
        return {"ok": True}

    def log(self, message: str):
        print("[AGENT-LOG]", message)
        return {"logged": True}
