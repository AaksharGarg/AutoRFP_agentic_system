# runner.py

"""
Runner module for Priority Queue Layer-4.
Processes new RFPs → scores → outputs JSON.
"""

import os
import json
import traceback
from typing import Dict

from .ner_extractor import extract_specs_from_rfp, extract_pdf_text, download_pdf
from .scorers import (
    compute_spec_score,
    compute_text_score,
    compute_vendor_score,
    compute_urgency_score,
    compute_historical_similarity,
    combine_scores,
    generate_explanation,
)
from .sku_matcher import match_skus_for_rfp


BASE_DIR = os.path.dirname(__file__)
NEW_RFPS_DIR = os.path.join(BASE_DIR, "..", "new_rfps")
OUTPUT_DIR = os.path.join(BASE_DIR, "..", "outputs")
LOG_DIR = os.path.join(BASE_DIR, "..", "logs", "milestones")
LLM_LOG_DIR = os.path.join(BASE_DIR, "..", "logs", "llm_raw")

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(LLM_LOG_DIR, exist_ok=True)


def write_milestone(rfp_id: str, text: str):
    path = os.path.join(LOG_DIR, f"{rfp_id}_milestones.txt")
    with open(path, "a") as f:
        f.write(text + "\n")


def load_rfp(path: str) -> Dict:
    with open(path, "r") as f:
        return json.load(f)


# ----------------------------------------------------------------------
# PDF extraction wrapper
# ----------------------------------------------------------------------
def gather_pdf_text(rfp: Dict) -> str | None:
    full_text = ""
    docs = rfp.get("documents", [])

    if not docs:
        return None  # PDFs optional

    for doc in docs:
        url = doc.get("url")
        if not url:
            continue

        local_path = download_pdf(url)
        if local_path:
            try:
                extracted = extract_pdf_text(local_path)
                if extracted:
                    full_text += "\n" + extracted
            except:
                continue

    return full_text.strip() if full_text else None


# ----------------------------------------------------------------------
# Main processing of ONE RFP
# ----------------------------------------------------------------------
def process_rfp(rfp: Dict):
    rfp_id = rfp.get("id", "unknown")
    write_milestone(rfp_id, "[START] Processing RFP")

    try:
        # 1. Specs
        write_milestone(rfp_id, "Extracting specs...")
        specs = extract_specs_from_rfp(rfp)

        # 2. PDF text (optional)
        write_milestone(rfp_id, "Extracting PDF text...")
        pdf_text = gather_pdf_text(rfp)
        write_milestone(rfp_id, f"PDF_TEXT_FOUND: {'YES' if pdf_text else 'NO'}")

        # 3. Scores
        write_milestone(rfp_id, "Computing scores...")
        spec_score = compute_spec_score(specs)

        text_score, sources_used = compute_text_score(rfp, pdf_text)
        write_milestone(rfp_id, f"TEXT_SOURCES_USED: {', '.join(sources_used)}")

        vendor_score = compute_vendor_score(rfp)
        urgency_score = compute_urgency_score(rfp)
        hist_sim = compute_historical_similarity(rfp, pdf_text)

        # 4. SKU matching
        write_milestone(rfp_id, "Matching SKUs...")
        matched_skus = match_skus_for_rfp(specs, top_n=10)

        # 5. Final score
        scores = {
            "spec_score": spec_score,
            "text_score": text_score,
            "vendor_score": vendor_score,
            "urgency_score": urgency_score,
            "historical_similarity": hist_sim,
        }
        scores["final_score"] = combine_scores(scores)

        # 6. Explanation
        write_milestone(rfp_id, "Generating explanation...")
        explanation = generate_explanation(rfp, scores, matched_skus)

        # 7. Save output
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, f"{rfp_id}.json")

        output = {
            "id": rfp_id,
            "rfp": rfp,
            "specs": specs,
            "scores": scores,
            "matched_skus": [
                {"sku": m["sku"], "score": m["score"]} for m in matched_skus
            ],
            "explanation": explanation,
        }

        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

        write_milestone(rfp_id, f"[DONE] Saved output → {out_path}")
        return output

    except Exception as e:
        write_milestone(rfp_id, f"[ERROR] {e}")
        write_milestone(rfp_id, traceback.format_exc())
        raise


# ----------------------------------------------------------------------
# Run on all RFPs
# ----------------------------------------------------------------------
def run_all():
    results = []
    summary_list = []

    for fname in os.listdir(NEW_RFPS_DIR):
        if not fname.endswith(".json"):
            continue

        path = os.path.join(NEW_RFPS_DIR, fname)
        rfp = load_rfp(path)
        out = process_rfp(rfp)
        results.append(out)

        # Build summary entry
        summary_list.append({
            "id": rfp.get("id"),
            "title": rfp.get("title"),
            "buyer_name": rfp.get("buyer_name"),
            "description": rfp.get("description"),
            "deadline_date": rfp.get("deadline_date"),
            "final_score": out["scores"]["final_score"]
        })

    # Sort by final score DESC
    summary_list = sorted(summary_list, key=lambda x: x["final_score"], reverse=True)

    # Save ranked summary JSON
    summary_path = os.path.join(OUTPUT_DIR, "summary_ranked.json")
    with open(summary_path, "w") as f:
        json.dump(summary_list, f, indent=2)

    return results
