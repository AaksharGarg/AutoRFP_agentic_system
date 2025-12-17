# ner_extractor.py (LLM-FREE / PURE RULE-BASED VERSION)

"""
Specification extraction module for new RFPs.

Features:
- Rule-based extraction from title and description
- PDF download + parsing using pdfminer.six
- Automatic OCR fallback using pytesseract if PDF has little or no text
(NO LLM USAGE IN THIS FILE)
"""

import os
import re
import requests
from urllib.parse import urlparse

from pdfminer.high_level import extract_text as pdf_extract_text
from pdf2image import convert_from_path
import pytesseract


# -------------------------------------------------------------
# PDF download directory
# -------------------------------------------------------------
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "downloaded_pdfs")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


# -------------------------------------------------------------
# Download PDF from URL
# -------------------------------------------------------------
def download_pdf(url: str) -> str:
    try:
        filename = os.path.basename(urlparse(url).path) or "document.pdf"
        local_path = os.path.join(DOWNLOAD_DIR, filename)

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(resp.content)

        return local_path
    except Exception:
        return None


# -------------------------------------------------------------
# PDF text extraction + OCR fallback
# -------------------------------------------------------------
def extract_pdf_text(pdf_path: str) -> str:
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    try:
        text = pdf_extract_text(pdf_path)

        # If PDF has almost no text → run OCR
        if len(text.strip()) < 50:
            return ocr_pdf(pdf_path)

        return text
    except Exception:
        return ""


def ocr_pdf(pdf_path: str) -> str:
    try:
        pages = convert_from_path(pdf_path)
        text = ""
        for page in pages:
            text += pytesseract.image_to_string(page)
        return text
    except Exception:
        return ""


# -------------------------------------------------------------
# RULE-BASED SPEC EXTRACTION (DETERMINISTIC)
# -------------------------------------------------------------
def rule_based_extract(text: str) -> dict:
    """Extract specs based purely on keywords and regex (no LLM)."""

    specs = {}
    t = text.lower()

    # ---- Area detection (sqft / sqm)
    m = re.search(r"(\d{2,7})\s*(sq\.?\s*ft|square\s*feet|sqm|sq\.?\s*m)", t)
    if m:
        specs["area"] = m.group(0)

    # ---- Application scope
    if "interior" in t:
        specs.setdefault("application", []).append("interior")
    if "exterior" in t or "weather-proof" in t or "weatherproof" in t:
        specs.setdefault("application", []).append("exterior")

    # ---- Low VOC requirement
    if "low voc" in t or "low-voc" in t:
        specs["low_voc"] = True

    # ---- Warranty requirement
    w = re.search(r"(\d+)\s*-?year\s*warranty", t)
    if w:
        specs["warranty_years_required"] = int(w.group(1))

    # ---- Anti-bacterial / anti-fungal requirements
    if "antibacterial" in t or "anti-bacterial" in t:
        specs["needs_antibacterial"] = True
    if "antifungal" in t or "anti-fungal" in t:
        specs["needs_antifungal"] = True

    return specs


# -------------------------------------------------------------
# MAIN ENTRYPOINT (NO LLM)
# -------------------------------------------------------------
def extract_specs_from_rfp(rfp: dict) -> dict:
    """Extract specs by combining title + description + PDF text."""

    title = rfp.get("title", "")
    desc = rfp.get("description", "")

    # Gather all PDF text
    pdf_text = ""
    for doc in rfp.get("documents", []):
        url = doc.get("url")
        if not url:
            continue
        p = download_pdf(url)
        if p:
            pdf_text += "\n" + extract_pdf_text(p)

    combined_text = f"{title}\n{desc}\n{pdf_text}"

    # Rule extraction only
    specs = rule_based_extract(combined_text)

    # Always return deterministic specs
    return specs
