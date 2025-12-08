# src/connectors/db_writer.py
import os
import json
from typing import Dict, Any

OUT_DIR = "./logs/extracted"
os.makedirs(OUT_DIR, exist_ok=True)

def upsert_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Default persistence: save JSON to disk using id as filename.
    You can replace this with real Postgres / Chroma / queue insertion.
    """
    rid = record.get("id") or "no-id-" + str(hash(record.get("source_url", "")))
    path = os.path.join(OUT_DIR, f"{rid}.json")
    with open(path, "w") as f:
        json.dump(record, f, indent=2)
    return {"path": path}
