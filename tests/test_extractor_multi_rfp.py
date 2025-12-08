# tests/test_extractor_multi_rfp.py
import asyncio
from src.crawler.ollama_client import OllamaClient
from src.crawler.fetcher import Fetcher
from src.crawler.extractor import Extractor

async def test_extract_multi(monkeypatch, tmp_path):
    # mock ollama.generate to return two RFPs
    def fake_generate(prompt, max_tokens=2048, timeout=120):
        return '[{"id":"a","source_url":"https://example.gov/t1","crawl_timestamp":"2025-01-01T00:00:00Z","source_domain":"example.gov","is_rfp":true,"title":"RFP A","date_of_posting":"2025-01-01","deadline_date":"2025-02-01T00:00:00Z","description":"desc A","documents":[]},{"id":"b","source_url":"https://example.gov/t2","crawl_timestamp":"2025-01-02T00:00:00Z","source_domain":"example.gov","is_rfp":true,"title":"RFP B","date_of_posting":"2025-01-05","deadline_date":"2025-03-01T00:00:00Z","description":"desc B","documents":[]}]'
    monkeypatch.setattr(OllamaClient, "generate", staticmethod(fake_generate))
    ollama = OllamaClient()
    fetcher = Fetcher()
    extractor = Extractor(ollama, fetcher, tmp_dir=str(tmp_path))
    html = "<html><body><h1>Multiple tenders</h1></body></html>"
    result = await extractor.extract_all("https://example.gov/page", html)
    assert isinstance(result, list)
    assert len(result) == 2

if __name__ == '__main__':
    asyncio.run(test_extract_multi())
