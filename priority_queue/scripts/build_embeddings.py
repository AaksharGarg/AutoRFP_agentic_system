# build_embeddings.py
"""
Optional script: Pre-compute embeddings for new RFPs.
Useful for debugging or performance pre-warming.
"""

import os
import json
from tqdm import tqdm
from priority_queue.src.embeddings import get_embedding

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
NEW_RFPS_DIR = os.path.join(BASE_DIR, "new_rfps")
out_path = os.path.join(BASE_DIR, "outputs", "rfp_embeddings.json")


def main():
    out = {}

    for fname in tqdm(os.listdir(NEW_RFPS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(NEW_RFPS_DIR, fname)
        try:
            rfp = json.load(open(path))
            rfp_id = rfp.get("id", fname)
            text = rfp.get("title", "") + "\n" + rfp.get("description", "")
            embedding = get_embedding(text)
            out[rfp_id] = embedding
        except Exception as e:
            print(f"Error on {fname}: {e}")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"Saved embeddings to {out_path}")


if __name__ == "__main__":
    main()
