import json
import pathlib
from datetime import datetime

def save_valid_record(record: dict) -> str:
    base = pathlib.Path(__file__).resolve().parents[2] / "logs" / "extracted"
    base.mkdir(parents=True, exist_ok=True)
    rec_id = record.get("id") or f"rfp_{int(datetime.utcnow().timestamp())}"
    path = base / f"{rec_id}.json"
    payload = {**record, "_saved_at": datetime.utcnow().isoformat() + "Z"}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
