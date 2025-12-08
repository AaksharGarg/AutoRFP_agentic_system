# src/agent/post_filter.py
from typing import Dict, Any, List
import re

# Keywords / patterns that indicate relevance to Asian Paints business
DOMAIN_KEYWORDS = [
    "paint", "coating", "coatings", "waterproof", "waterproofing",
    "anti-corrosive", "anti corrosive", "epoxy", "polyurethane", "pu",
    "structural steel", "steel", "bridge", "roof", "basement", "flooring",
    "floor", "epoxy flooring", "protective coating", "corrosion",
    "surface preparation", "sandblast", "shot blast", "hydroblasting",
    "primer", "topcoat", "industrial coating", "marine coating", "pipeline"
]

def normalize_text(s: str) -> str:
    if not s:
        return ""
    return re.sub(r"\s+", " ", s.lower()).strip()

def is_domain_relevant(record: Dict[str, Any]) -> bool:
    """
    Heuristic: check coating_fields, matched_terms, keywords, title, and description
    for domain keywords. Returns True if at least one strong signal present.
    """
    text_fields = []
    coating = record.get("coating_fields") or {}
    for v in coating.values():
        if isinstance(v, str):
            text_fields.append(v)
    text_fields.extend(record.get("matched_terms") or [])
    text_fields.extend(record.get("keywords") or [])
    text_fields.append(record.get("title") or "")
    text_fields.append(record.get("description") or "")

    combined = " ".join([normalize_text(t) for t in text_fields if t])
    hits = 0
    for kw in DOMAIN_KEYWORDS:
        if kw in combined:
            hits += 1
    # threshold: at least 1 hit among strong keywords, or matched_terms contains a domain term
    return hits >= 1
