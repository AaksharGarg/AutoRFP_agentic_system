# vectorstore.py

"""
A lightweight vector database wrapper for the Priority Queue system.

Supports two modes:
1. ChromaDB persistent storage in priority_queue/vector_db/
2. JSON fallback if chromadb is not available

Functions:
- index_documents(texts, metadatas, ids)
- query_embedding(embedding, k)

Returned format for query:
[
    {"id": ..., "score": float, "metadata": {...}},
    ...
]
"""

import os
import json
import math
from typing import List, Dict, Any

from .embeddings import get_embedding

VECTOR_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "vector_db")
JSON_FALLBACK_PATH = os.path.join(VECTOR_DB_PATH, "embeddings.json")

# Try loading chromadb
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except Exception:
    CHROMA_AVAILABLE = False


# Utility: cosine similarity

def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorStore:
    def __init__(self):
        os.makedirs(VECTOR_DB_PATH, exist_ok=True)

        self.use_chroma = CHROMA_AVAILABLE

        if self.use_chroma:
            import chromadb

            self.client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
            self.collection = self.client.get_or_create_collection("rfp_vectors")

        else:
            # JSON fallback
            if not os.path.exists(JSON_FALLBACK_PATH):
                with open(JSON_FALLBACK_PATH, "w") as f:
                    json.dump([], f)

    def index_documents(self, texts: List[str], metadatas: List[Dict], ids: List[str]):
        """Index documents in Chroma or JSON fallback."""
        embeddings = [get_embedding(t) for t in texts]

        if self.use_chroma:
            self.collection.add(documents=texts, metadatas=metadatas, embeddings=embeddings, ids=ids)
            return

        # JSON fallback
        with open(JSON_FALLBACK_PATH, "r") as f:
            data = json.load(f)

        for text, meta, vec, _id in zip(texts, metadatas, embeddings, ids):
            data.append({"id": _id, "text": text, "metadata": meta, "embedding": vec})

        with open(JSON_FALLBACK_PATH, "w") as f:
            json.dump(data, f)

    def query_embedding(self, query_emb: List[float], k: int = 5):
        """Query the most similar documents by cosine similarity.
        Returns: [{"id":..., "score":..., "metadata":...}]
        """
        if self.use_chroma:
            resp = self.collection.query(query_embeddings=[query_emb], n_results=k)
            out = []
            for i in range(len(resp["ids"][0])):
                out.append({
                    "id": resp["ids"][0][i],
                    "score": resp["distances"][0][i],
                    "metadata": resp["metadatas"][0][i],
                })
            return out

        # JSON fallback
        with open(JSON_FALLBACK_PATH, "r") as f:
            data = json.load(f)

        scored = []
        for row in data:
            sim = cosine_similarity(query_emb, row["embedding"])
            scored.append({"id": row["id"], "score": sim, "metadata": row["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]


# Singleton accessor
def get_vectorstore() -> VectorStore:
    return VectorStore()
