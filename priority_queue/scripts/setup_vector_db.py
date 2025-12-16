# setup_vector_db.py
"""
Build Vector DB from past_rfps/
---------------------------------
This script indexes ALL past RFPs into the vector DB.
Each document = title + description + SKU solution summary.
"""

import os
import json
from tqdm import tqdm

from priority_queue.src.vectorstore import get_vectorstore
from priority_queue.src.embeddings import get_embedding

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
PAST_RFPS_DIR = os.path.join(BASE_DIR, "past_rfps")

store = get_vectorstore()

def build_document_text(rfp: dict) -> str:
    title = rfp.get("title", "")
    desc = rfp.get("description", "")
    skus = rfp.get("sku_solution", {})
    sku_txt = json.dumps(skus) if skus else ""
    return f"{title}\n{desc}\n{sku_txt}"


def main():
    texts, metas, ids = [], [], []

    for fname in tqdm(os.listdir(PAST_RFPS_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(PAST_RFPS_DIR, fname)
        try:
            rfp = json.load(open(path))
            doc_id = rfp.get("id", fname)
            text = build_document_text(rfp)

            texts.append(text)
            metas.append({"file": fname, "id": doc_id})
            ids.append(doc_id)
        except Exception:
            continue

    if texts:
        store.index_documents(texts, metas, ids)
        print(f"Indexed {len(texts)} documents into vector DB.")
    else:
        print("No documents indexed.")


if __name__ == "__main__":
    main()
