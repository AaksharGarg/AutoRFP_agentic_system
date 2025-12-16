# scorers.py

"""
Scoring functions for Priority Queue Layer-4.
Includes:
- spec_score
- text_score (TF-IDF, embeddings, keyword Jaccard)
- vendor_score
- urgency_score
- historical_similarity
- final score combining
- LLM explanation generation
"""

import os
import json
import math
import datetime
from typing import Dict, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import get_embedding
from .vectorstore import get_vectorstore, CHROMA_AVAILABLE

# ----------------------------------------------------------------------
# GLOBAL TF-IDF VECTORIZE (simple per-input model)
# ----------------------------------------------------------------------
_tfidf_vectorizer = TfidfVectorizer(stop_words="english")


# ----------------------------------------------------------------------
# 1. SPEC SCORE (placeholder rules, to be expanded)
# ----------------------------------------------------------------------
def compute_spec_score(specs: dict) -> float:
    """
    Basic scoring based on extracted specs.
    Expand this as your spec extraction becomes more structured.
    """
    if not specs:
        return 0.0

    score = 0
    total = 0

    # Simple rule examples
    if specs.get("low_voc") is True:
        score += 1
    total += 1

    if specs.get("anti_fungal") is True:
        score += 1
    total += 1

    if "application_area" in specs:
        score += 1
    total += 1

    return score / total if total > 0 else 0.0


# ----------------------------------------------------------------------
# 2. TEXT SCORE HELPERS
# ----------------------------------------------------------------------
def compute_tfidf_score(text: str) -> float:
    try:
        tfidf = _tfidf_vectorizer.fit_transform([text])
        sim = cosine_similarity(tfidf[0:1], tfidf)[0][0]
        return float(sim)
    except:
        return 0.0


def compute_embedding_cosine(text: str) -> float:
    """
    For now compares embedding to itself (normed) → returns 1.0.
    Later replace with comparison against a global corpus.
    """
    try:
        emb = get_embedding(text)
        dot = sum([x * y for x, y in zip(emb, emb)])
        norm = (sum([x * x for x in emb]) ** 0.5) ** 2
        return float(dot / norm) if norm > 0 else 0.0
    except:
        return 0.0


def compute_keyword_jaccard(rfp: dict) -> float:
    rfp_kw = set([k.lower() for k in rfp.get("keywords", [])])
    ref_kw = {"paint", "primer", "coating", "interior", "exterior", "wall", "low voc"}

    if not rfp_kw:
        return 0.0

    inter = len(rfp_kw.intersection(ref_kw))
    union = len(rfp_kw.union(ref_kw))
    return inter / union if union > 0 else 0.0


# ----------------------------------------------------------------------
# 3. TEXT SCORE (FINAL HYBRID)
# ----------------------------------------------------------------------
def compute_text_score(rfp: dict, extracted_pdf_text: str | None):
    """
    Computes hybrid textual relevance score.
    - PDF text is optional.
    - If missing → use only title + description.
    Returns:
        (final_text_score, text_sources_used)
    """

    title = rfp.get("title", "") or ""
    desc = rfp.get("description", "") or ""

    if extracted_pdf_text and isinstance(extracted_pdf_text, str):
        text = f"{title} {desc} {extracted_pdf_text}".strip()
        sources = ["title", "description", "pdf"]
    else:
        text = f"{title} {desc}".strip()
        sources = ["title", "description"]

    if not text:
        return 0.0, sources

    tfidf_score = compute_tfidf_score(text)
    embed_score = compute_embedding_cosine(text)
    keyword_score = compute_keyword_jaccard(rfp)

    final = (
        0.5 * embed_score +
        0.3 * tfidf_score +
        0.2 * keyword_score
    )

    return final, sources


# ----------------------------------------------------------------------
# 4. VENDOR SCORE
# ----------------------------------------------------------------------
def compute_vendor_score(rfp: dict) -> float:
    buyer = rfp.get("buyer_name")
    if not buyer:
        return 0.0

    hist_path = os.path.join(os.path.dirname(__file__), "..", "past_rfps", "buyer_history.json")
    if not os.path.exists(hist_path):
        return 0.0

    data = json.load(open(hist_path, "r"))
    if buyer not in data:
        return 0.0

    meta = data[buyer]
    orders = meta.get("orders", 1)
    success = meta.get("success_rate", 0.5)

    # Simple formula: normalized experience * success_rate
    return min(1.0, (orders / 20) * success)


# ----------------------------------------------------------------------
# 5. URGENCY SCORE
# ----------------------------------------------------------------------
def compute_urgency_score(rfp: dict) -> float:
    deadline = rfp.get("deadline_date")
    if not deadline:
        return 0.0

    try:
        deadline_dt = datetime.datetime.fromisoformat(deadline.replace("Z", ""))
        now = datetime.datetime.utcnow()
        days_left = (deadline_dt - now).days
        return 1 / (1 + math.exp(-days_left / 7))
    except:
        return 0.0


# ----------------------------------------------------------------------
# 6. HISTORICAL SIMILARITY
# ----------------------------------------------------------------------
def compute_historical_similarity(rfp: dict, pdf_text: str | None) -> float:
    text_blob = (
        (rfp.get("title") or "") + " " +
        (rfp.get("description") or "") + " " +
        (pdf_text or "")
    ).strip()

    if not text_blob:
        return 0.0

    # embed
    emb = get_embedding(text_blob)

    # vector DB
    store = get_vectorstore()

    # CALL WITH CORRECT SIGNATURE
    results = store.query_embedding(emb, k=5)

    if not results:
        return 0.0

    # for Chroma, this is distance; for JSON fallback, it's cosine similarity
    # So we invert Chroma's distance
    score = results[0]["score"]

    # If using Chroma, distance MUST be converted → smaller distance means more similar:
    if CHROMA_AVAILABLE:
        score = 1 - score

    return float(score)


# ----------------------------------------------------------------------
# 7. COMBINE SCORES
# ----------------------------------------------------------------------
def combine_scores(scores: dict) -> float:
    return float(
        0.40 * scores["spec_score"] +
        0.20 * scores["text_score"] +
        0.10 * scores["vendor_score"] +
        0.15 * scores["urgency_score"] +
        0.15 * scores["historical_similarity"]
    )


# ----------------------------------------------------------------------
# 8. LLM EXPLANATION (placeholder)
# ----------------------------------------------------------------------
def generate_explanation(rfp, scores, matched_skus):
    # Replace with GPT-4.1 call later
    return (
        f"Spec Score: {scores['spec_score']:.2f}, "
        f"Text Score: {scores['text_score']:.2f}, "
        f"Vendor Score: {scores['vendor_score']:.2f}, "
        f"Urgency: {scores['urgency_score']:.2f}, "
        f"Historical: {scores['historical_similarity']:.2f}. "
        f"Matched SKUs: {len(matched_skus)}"
    )
