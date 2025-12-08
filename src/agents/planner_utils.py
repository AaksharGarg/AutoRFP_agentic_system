import json, logging, time
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError
from src.crawler.ollama_client import OllamaClient
import os

logger = logging.getLogger(__name__)

PLAN_SCHEMA = {
  "type": "object",
  "required": ["plan_id","goal","actions","max_steps"],
  "properties": {
    "plan_id": {"type":"string"},
    "goal": {"type":"string"},
    "actions": {
      "type":"array",
      "items": {
        "type":"object",
        "required":["id","tool"],
        "properties":{
          "id":{"type":"string"},
          "tool":{"type":"string"},
          "args":{"type":"object"},
          "retry_policy":{"type":"object"},
          "expectation":{"type":"object"}
        }
      }
    },
    "max_steps": {"type":"integer"}
  }
}

def _try_load_json(text: str) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(text)
    except Exception:
        # try to extract first balanced JSON object
        start = None; depth = 0; in_string = False; esc = False
        for i,ch in enumerate(text):
            if start is None:
                if ch == '{':
                    start = i; depth = 1; in_string = False; esc = False
            else:
                if esc:
                    esc = False
                elif ch == '\\\\':
                    esc = True
                elif ch == '"' and not esc:
                    in_string = not in_string
                elif not in_string:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[start:i+1]
                            try:
                                return json.loads(candidate)
                            except Exception:
                                break
        return None

def _assemble_ndjson(text: str) -> Optional[str]:
    parts = []
    any_parsed = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            any_parsed = True
            if isinstance(obj, dict) and "response" in obj and obj["response"] is not None:
                parts.append(str(obj["response"]))
        except Exception:
            continue
    if any_parsed and parts:
        return "".join(parts)
    return None

def get_plan_from_ollama(ollama: OllamaClient, prompt: str, max_tokens: int = 2048, repair_attempts: int = 2) -> Dict[str, Any]:
    raw = ollama.generate(prompt, max_tokens=max_tokens)
    logger.debug("Planner raw len=%d", len(raw) if raw else 0)

    # 1) direct parse
    plan = _try_load_json(raw)
    if plan is None:
        # 2) try NDJSON assembly
        nd = _assemble_ndjson(raw)
        if nd:
            plan = _try_load_json(nd)

    if plan is not None:
        try:
            validate(instance=plan, schema=PLAN_SCHEMA)
            return plan
        except ValidationError as e:
            logger.warning("Parsed plan failed schema: %s", e)

    # 3) attempts to repair by asking LLM to return only valid JSON
    for attempt in range(repair_attempts):
        repair_prompt = (
            "You returned text that is not valid JSON. Convert the following text into a single, valid JSON object that strictly matches the plan schema below. RETURN ONLY THE JSON OBJECT.\n\n"
            "PLAN_SCHEMA: " + json.dumps(PLAN_SCHEMA) + "\n\n"
            "RAW_OUTPUT:\n" + (raw or "")[:60000] + "\n\n"
            "Return only the corrected JSON object."
        )
        logger.info("Planner: repair attempt %d", attempt+1)
        repaired = ollama.generate(repair_prompt, max_tokens=max_tokens)
        # first try direct parse
        plan = _try_load_json(repaired)
        if plan is None:
            # try NDJSON assembly
            nd = _assemble_ndjson(repaired)
            if nd:
                plan = _try_load_json(nd)
        if plan is not None:
            try:
                validate(instance=plan, schema=PLAN_SCHEMA)
                logger.info("Repaired plan validated on attempt %d", attempt+1)
                return plan
            except ValidationError as e:
                logger.warning("Repaired plan parse succeeded but failed schema validation: %s", e)
                raw = repaired  # feed repaired into next attempt
                continue
        raw = repaired

    # 4) final failure: save raw to logs and raise
    os.makedirs("logs/raw", exist_ok=True)
    fname = f"logs/raw/planner_raw_{int(time.time())}.txt"
    with open(fname, "w", encoding="utf-8") as fh:
        fh.write((raw or "")[:200000])
    logger.error("Planner output not parseable. Raw saved to %s", fname)
    raise RuntimeError(f"Failed to parse or repair planner output. Raw saved to {fname}")
