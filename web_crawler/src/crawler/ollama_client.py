# inside src/crawler/ollama_client.py (replace or adapt generate())
import json, logging, httpx

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434", model="llama3", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, max_tokens: int = 1024):
        """
        Call Ollama's /api/generate (or /v1/generate) depending on your cli. 
        This version tries to parse JSON, NDJSON stream, or fall back to plain text.
        """
        url = f"{self.base_url}/api/generate"  # adapt if your Ollama endpoint differs
        payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "stream": False,
            "options": {"temperature": 0}
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            text = resp.text or ""
            # try direct JSON
            try:
                return resp.json().get("response", "") if isinstance(resp.json(), dict) else json.dumps(resp.json())
            except Exception:
                # try NDJSON line-join: many Ollama configs send newline-delimited chunks
                lines = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        part = json.loads(line)
                        if isinstance(part, dict) and "response" in part:
                            lines.append(part["response"])
                        else:
                            lines.append(line)
                    except Exception:
                        lines.append(line)
                joined = "".join(lines)
                return joined
        except Exception as e:
            logger.exception("Ollama request failed: %s", e)
            raise
