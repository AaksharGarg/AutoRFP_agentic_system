import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import List, Dict, Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SEEDS_PATH = ROOT / "logs/seeds/seeds.json"
DEFAULT_CRAWL_RULES = ROOT / "config/crawl_rules.yaml"
DEFAULT_STANDARDS = ROOT / "config/standards.yaml"
DEFAULT_PROMPTS = ROOT / "config/ollama_prompts.yaml"
DEFAULT_SEED_URLS = ROOT / "config/seed_urls.yaml"


def _read_yaml(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _read_json(path: pathlib.Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_seeds(seeds_path: pathlib.Path = DEFAULT_SEEDS_PATH) -> List[Dict[str, Any]]:
    data = _read_json(seeds_path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("seeds"), list):
        return data["seeds"]
    # fallback to YAML list
    yaml_seeds = _read_yaml(DEFAULT_SEED_URLS)
    if isinstance(yaml_seeds, list):
        return yaml_seeds
    if isinstance(yaml_seeds, dict) and isinstance(yaml_seeds.get("seeds"), list):
        return yaml_seeds["seeds"]
    return []


@dataclass
class CrawlSettings:
    max_depth: int = 2
    request_delay_seconds: float = 1.0
    user_agent: str = "AutoRFPAgent/1.0"
    allowed_domains: List[str] = field(default_factory=lambda: [])
    max_concurrent_fetches: int = 3


@dataclass
class LLMSettings:
    model: str = "llama3"
    base_url: str = "http://localhost:11434"


@dataclass
class AppSettings:
    redis_url: str = "redis://localhost:6379/0"
    crawl: CrawlSettings = field(default_factory=CrawlSettings)
    llm: LLMSettings = field(default_factory=LLMSettings)
    goal: str = "Find coating and waterproofing tenders"
    seeds_path: pathlib.Path = DEFAULT_SEEDS_PATH


def load_settings() -> AppSettings:
    crawl_cfg = _read_yaml(DEFAULT_CRAWL_RULES)
    llm_cfg = crawl_cfg.get("llm", {}) if isinstance(crawl_cfg, dict) else {}

    crawl = CrawlSettings(
        max_depth=crawl_cfg.get("crawl", {}).get("max_depth", 2) if isinstance(crawl_cfg, dict) else 2,
        request_delay_seconds=crawl_cfg.get("crawl", {}).get("request_delay_seconds", 1.0) if isinstance(crawl_cfg, dict) else 1.0,
        user_agent=crawl_cfg.get("crawl", {}).get("user_agent", "AutoRFPAgent/1.0") if isinstance(crawl_cfg, dict) else "AutoRFPAgent/1.0",
        allowed_domains=crawl_cfg.get("crawl", {}).get("allowed_domains", []) if isinstance(crawl_cfg, dict) else [],
        max_concurrent_fetches=crawl_cfg.get("crawl", {}).get("max_concurrent_fetches", 3) if isinstance(crawl_cfg, dict) else 3,
    )

    llm = LLMSettings(
        model=llm_cfg.get("model", "llama3") if isinstance(llm_cfg, dict) else "llama3",
        base_url=llm_cfg.get("base_url", "http://localhost:11434") if isinstance(llm_cfg, dict) else "http://localhost:11434",
    )

    redis_url = crawl_cfg.get("redis", {}).get("url", "redis://localhost:6379/0") if isinstance(crawl_cfg, dict) else "redis://localhost:6379/0"
    goal = crawl_cfg.get("goal", "Find coating and waterproofing tenders") if isinstance(crawl_cfg, dict) else "Find coating and waterproofing tenders"

    return AppSettings(
        redis_url=os.getenv("REDIS_URL", redis_url),
        crawl=crawl,
        llm=llm,
        goal=os.getenv("CRAWL_GOAL", goal),
        seeds_path=pathlib.Path(os.getenv("SEEDS_PATH", str(DEFAULT_SEEDS_PATH))),
    )
