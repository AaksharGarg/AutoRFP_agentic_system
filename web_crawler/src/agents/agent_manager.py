import json
import uuid
import asyncio
import traceback
from typing import Dict, Any
import os, json, urllib.parse

from src.crawler.ollama_client import OllamaClient
from src.crawler.frontier import Frontier
from src.crawler.fetcher import Fetcher
from src.crawler.extractor import Extractor
from src.crawler.validator import validate_array
from src.crawler.normalize import normalize_array
from src.crawler.persist import save_valid_record
from src.agents.tools import ToolRegistry
from src.agents.planner_prompts import PLANNER_PROMPT_TEMPLATE
from src.agents.post_filter import is_domain_relevant
from src.connectors.db_writer import upsert_record
from src.agents.planner_utils import get_plan_from_ollama

class AgentManager:
    def __init__(self, ollama_base: str = "http://localhost:11434", model: str = "llama3", redis_url: str = "redis://localhost:6379/0"):
        self.ollama = OllamaClient(base_url=ollama_base, model=model)
        self.frontier = Frontier(redis_url=redis_url)
        self.fetcher = Fetcher()
        # Extractor currently uses only local regex/heuristics; keep construction simple
        self.extractor = Extractor()
        self.tools = ToolRegistry(self.frontier, self.fetcher, self.extractor)
        # register DB writer (replace this with your real DB function)
        self.tools.register("db.insert_rfp", lambda record: upsert_record(record))
        seeds_path = "logs/seeds/seeds.json"
        try:
            if os.path.exists(seeds_path):
                with open(seeds_path, "r", encoding="utf-8") as sf:
                    seeds = json.load(sf)
                added = 0
                for s in seeds:
                    print("%", s)
                    # s is expected to be a dict: {"url": "...", "priority": 5, "depth": 0, "meta": {...}}
                    url = s.get("url")
                    if not url:
                        print(f"[SEED LOADER] skipping empty/invalid seed entry: {s}")
                        continue
                    if not isinstance(url, str):
                        print(f"[SEED LOADER] skipping seed with non-str url: {s!r}")
                        continue
                    parsed = urllib.parse.urlparse(url)
                    if parsed.scheme not in ("http", "https") or not parsed.netloc:
                        print(f"[SEED LOADER] skipping invalid url: {url}")
                        continue
                    priority = s.get("priority", 5)
                    depth = s.get("depth", 0)
                    meta = s.get("meta", {}) or {}
                    try:
                        self.frontier.add(url, priority=priority, depth=depth, meta=meta)
                        added += 1
                    except Exception as e:
                        print(f"[SEED LOADER] frontier.add failed for {url}: {e}")
                print(f"[SEED LOADER] added {added} seeds from {seeds_path}")
        except Exception as e:
            print("[SEED LOADER] failed to load seeds:", e)

    def _call_planner(self, goal: str, state_summary: str, max_tokens: int = 2048) -> Dict[str, Any]:
        prompt = PLANNER_PROMPT_TEMPLATE.replace("{goal}", goal).replace("{state}", state_summary)
        # get_plan_from_ollama will parse + attempt to repair if needed
        return get_plan_from_ollama(self.ollama, prompt, max_tokens=max_tokens, repair_attempts=1)

    async def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = action.get("tool")
        args = action.get("args", {}) or {}
        retry_policy = action.get("retry_policy", {"retries": 0, "backoff_seconds": 1})
        retries = retry_policy.get("retries", 0)
        backoff = retry_policy.get("backoff_seconds", 1)

        tool_fn = self.tools.get(tool_name)
        if tool_fn is None:
            return {"status": "error", "error": f"unknown tool: {tool_name}"}

        attempt = 0
        while True:
            try:
                if asyncio.iscoroutinefunction(tool_fn):
                    result = await tool_fn(**args)
                else:
                    result = tool_fn(**args)
                return {"status": "ok", "result": result}
            except Exception as e:
                attempt += 1
                if attempt > retries:
                    return {"status": "error", "error": str(e), "trace": traceback.format_exc()}
                await asyncio.sleep(backoff * attempt)

    async def run_once(self, goal: str, max_steps: int = 50):
        # Pop up to 5 URLs from frontier to process
        urls_to_process = []
        for _ in range(5):
            item = self.frontier.pop()
            if item:
                urls_to_process.append(item)
            else:
                break

        state = {
            "frontier_size": self.frontier.size(),
            "urls_to_process": urls_to_process
        }
        state_summary = json.dumps(state, default=str)
        plan = self._call_planner(goal, state_summary)
        print("[AGENT] Received plan:", plan.get("plan_id"))
        actions = plan.get("actions", [])[:max_steps]

        # Store results of previous actions
        action_results = {}

        for action in actions:
            aid = action.get("id")
            print(f"[AGENT] Executing {aid} -> {action.get('tool')}")

            # Resolve placeholders in args
            args = action.get("args", {}) or {}
            resolved_args = self._resolve_args(args, action_results)
            action["args"] = resolved_args

            print("[AGENT] action args:", json.dumps(resolved_args, default=str)[:1000])
            out = await self._execute_action(action)
            print(f"[AGENT] Result for {aid}: {out.get('status')}")

            # Store result for future reference
            action_results[aid] = out

            # Special handling for extractor results
            if action.get("tool") == "extractor.extract_all" and out.get("status") == "ok":
                raw_records = out["result"] or []
                normalized = normalize_array(raw_records, resolved_args.get("url"))

                # schema validation
                val = validate_array(normalized)
                if not val.valid:
                    print("[AGENT] Validation failed for extracted records:", val.errors)
                    import os, time
                    os.makedirs("logs/raw", exist_ok=True)
                    fname = f"logs/raw/raw_{int(time.time())}.json"
                    with open(fname, "w") as f:
                        json.dump({"url": resolved_args.get("url"), "raw": raw_records, "normalized": normalized, "errors": val.errors}, f, indent=2)
                    continue

                db_tool = self.tools.get("db.insert_rfp")
                for rec in normalized:
                    path = save_valid_record(rec)
                    print(f"[AGENT] Saved valid record -> {path}")
                    if is_domain_relevant(rec) and db_tool:
                        try:
                            db_res = db_tool(rec)
                            print("[AGENT] db.insert_rfp ->", db_res)
                        except Exception as e:
                            print("[AGENT] db.insert_rfp failed:", e)
                    else:
                        print("[AGENT] Record not relevant to domain, skipping db insert: ", rec.get("title"))
        print("[AGENT] Plan complete")

    def _resolve_args(self, args: Dict[str, Any], action_results: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve placeholders like {action_id.result} in args"""
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # Extract action_id and field
                placeholder = value[1:-1]  # remove {}
                if "." in placeholder:
                    action_id, field = placeholder.split(".", 1)
                    if action_id in action_results:
                        result = action_results[action_id]
                        if field == "result":
                            resolved[key] = result.get("result")
                        elif field in result:
                            resolved[key] = result[field]
                        else:
                            resolved[key] = result
                    else:
                        resolved[key] = None  # action not executed yet
                else:
                    resolved[key] = value  # not a valid placeholder
            else:
                resolved[key] = value
        return resolved
