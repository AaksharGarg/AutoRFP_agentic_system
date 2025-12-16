# sku_matcher.py

"""
SKU Matcher Module
------------------
Matches extracted RFP specs (from ner_extractor) against the SKU master JSON.

Returns ONLY the top-N matching SKUs (default N=10).

Matching criteria implemented:
- application (interior/exterior/metal/concrete)
- low VOC requirements
- antibacterial / antifungal needs
- certifications (GreenPro etc.)
- category / sub-category proximity
- surface types
- recommended_rfp_tags overlap
- inferred coverage vs SKU coverage if available

The scoring model is heuristic but explainable.
"""

import os
import json
from typing import List, Dict

# Path to SKU master JSON
SKUS_PATH = os.path.join(os.path.dirname(__file__), "..", "skus", "sku_master.json")

# ------------------------------------------------------------
# Utility: Jaccard similarity
# ------------------------------------------------------------
def jaccard(a: List[str], b: List[str]) -> float:
    if not a or not b:
        return 0.0
    set_a, set_b = set(a), set(b)
    return len(set_a & set_b) / len(set_a | set_b)


# ------------------------------------------------------------
# Load SKU master JSON
# ------------------------------------------------------------
def load_sku_master() -> List[Dict]:
    with open(SKUS_PATH, "r") as f:
        data = json.load(f)
    return data.get("sku_master", [])


# ------------------------------------------------------------
# Compute SKU match score against extracted RFP specs
# ------------------------------------------------------------
def compute_sku_score(sku: dict, specs: dict) -> float:
    score = 0.0

    # 1. Application matching (interior, exterior, metal, concrete)
    rfp_app = specs.get("application", [])
    sku_surfaces = sku.get("surface_types", [])
    score += jaccard(rfp_app, sku_surfaces) * 2.0  # weight 2

    # 2. Low VOC requirement
    if specs.get("low_voc"):
        if sku.get("key_properties", {}).get("low_voc"):
            score += 1.5

    # 3. Antibacterial / antifungal
    if specs.get("needs_antibacterial"):
        if sku.get("key_properties", {}).get("anti_bacterial"):
            score += 1.5

    if specs.get("needs_antifungal"):
        if sku.get("key_properties", {}).get("anti_fungal"):
            score += 1.5

    # 4. Certifications
    if "certifications" in specs:
        score += jaccard(specs.get("certifications", []), sku.get("certifications", [])) * 1.0

    # 5. Category / sub-category matching
    if "category" in specs:
        if specs.get("category") == sku.get("category"):
            score += 1.2

    if "sub_category" in specs:
        if specs.get("sub_category") == sku.get("sub_category"):
            score += 1.0

    # 6. Tags related to RFP
    score += jaccard(specs.get("recommended_rfp_tags", []), sku.get("recommended_rfp_tags", [])) * 1.0

    # 7. Coverage estimation (very rough heuristic)
    if "area" in specs:
        area_text = specs.get("area", "")
        area_num = extract_number(area_text)
        if area_num:
            sku_cov = sku.get("coverage_sqft_per_litre", 0)
            if sku_cov > 0:
                score += 0.5

    return score


# ------------------------------------------------------------
# Utility: Extract number from string
# ------------------------------------------------------------
def extract_number(s: str) -> float:
    import re
    m = re.search(r"(\d+)", s)
    return float(m.group(1)) if m else None


# ------------------------------------------------------------
# Main function: return top-N SKUs
# ------------------------------------------------------------
def match_skus(specs: dict, top_n: int = 10) -> List[Dict]:
    skus = load_sku_master()

    scored = []
    for sku in skus:
        s = compute_sku_score(sku, specs)
        scored.append({"sku": sku, "score": s})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


# Convenience wrapper for debug
def match_skus_for_rfp(rfp_specs: dict, top_n: int = 10):
    return match_skus(rfp_specs, top_n)
