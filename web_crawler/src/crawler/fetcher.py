# src/crawler/fetcher.py
import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse
import aiohttp
import os
import time

USER_AGENT = "AutoRFPAgent/1.0"

class FetchResult:
    def __init__(self, url, html=None, content_type=None, status=0, final_url=None):
        self.url = url
        self.html = html
        self.content_type = content_type
        self.status = status
        self.final_url = final_url

class Fetcher:
    def __init__(self, request_delay: float = 1.0):
        self._last_request = {}
        self.request_delay = request_delay

    async def _respect_rate_limit(self, url: str):
        host = urlparse(url).netloc
        last = self._last_request.get(host, 0)
        now = time.time()
        elapsed = now - last
        if elapsed < self.request_delay:
            await asyncio.sleep(self.request_delay - elapsed)
        self._last_request[host] = time.time()

    async def fetch_html(self, url: str, timeout: int = 30000) -> FetchResult:
        await self._respect_rate_limit(url)
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=USER_AGENT)
            try:
                resp = await page.goto(url, wait_until="networkidle", timeout=timeout)
                status = resp.status if resp else 0
                content_type = resp.headers.get("content-type") if resp else None
                html = await page.content()
                final = page.url
            except Exception as e:
                await browser.close()
                return FetchResult(url, html=None, content_type=None, status=0, final_url=url)
            await browser.close()
            return FetchResult(url, html=html, content_type=content_type, status=status, final_url=final)

    async def download_binary(self, url: str, dst_path: str, timeout: int = 60) -> bool:
        async with aiohttp.ClientSession() as s:
            try:
                async with s.get(url, timeout=timeout) as r:
                    if r.status == 200:
                        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                        with open(dst_path, "wb") as f:
                            f.write(await r.read())
                        return True
            except Exception:
                return False
        return False
