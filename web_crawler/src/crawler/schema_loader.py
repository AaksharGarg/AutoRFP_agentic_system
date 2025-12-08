# src/crawler/schema_loader.py
import json, logging, os
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "rfp_extracted_v1",
    "type": "object",
    "additionalProperties": True
}

def load_rfp_schema(path: str = "src/schemas/rfp_extracted_v1.json") -> Dict[str, Any]:
    """
    Try to load schema from disk. If missing/corrupt -> return a safe fallback schema
    (so imports don't crash) and log a warning.
    """
    try:
        if not os.path.exists(path):
            logger.warning("Schema file not found at %s — using fallback schema", path)
            return DEFAULT_SCHEMA
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
            # quick sanity check
            if not isinstance(schema, dict):
                raise ValueError("Schema is not a JSON object")
            return schema
    except Exception as e:
        logger.exception("Failed to load schema %s: %s. Using fallback.", path, e)
        return DEFAULT_SCHEMA
