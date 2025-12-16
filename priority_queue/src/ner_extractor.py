# ner_extractor.py

"""
Specification extraction module for new RFPs.

Features:
- Rule-based extraction from title and description
- PDF download + parsing using pdfminer.six
- Automatic OCR fallback using pytesseract if PDF has little or no text
- GPT-4.1 fallback extraction when rule-based confidence is low
- Logs raw LLM outputs into logs/llm_raw/
"""

import os
import re
import json
import requests
import tempfile
import pytesseract
from PIL import Image
from urllib.parse import urlparse
from pdfminer.high_level import extract_text as pdf_extract_text
from pdf2image import convert_from_path

from .embeddings import get_embedding

# Logging paths
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "llm_raw")
os.makedirs(LOG_DIR, exist_ok=True)

# Download folder for PDFs
download_dir = os.path.join(os.path.dirname(__file__), "..", "downloaded_pdfs")
os.makedirs(download_dir, exist_ok=True)

# OpenAI LLM
from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
llm_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


# -------------------------------------------------------------
# Helper: download PDF
# -------------------------------------------------------------
def download_pdf(url: str) -> str:
    """Download PDF file and return local path."""
    try:
        filename = os.path.basename(urlparse(url).path) or "document.pdf"
        local_path = os.path.join(download_dir, filename)

        resp = requests.get(url, timeout=20)
        resp.raise_for_status()

        with open(local_path, "wb") as f:
            f.write(resp.content)

        return local_path
    except Exception:
        return None


# -------------------------------------------------------------
# Helper: extract text from PDF, fallback to OCR
# -------------------------------------------------------------
def extract_pdf_text(pdf_path: str) -> str:
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    try:
        text = pdf_extract_text(pdf_path)
        # If nearly empty, do OCR
        if len(text.strip()) < 50:
            return ocr_pdf(pdf_path)
        return text
    except Exception:
        return ""


# OCR fallback

def ocr_pdf(pdf_path: str) -> str:
    try:
        pages = convert_from_path(pdf_path)
        text = ""
        for p in pages:
            text += pytesseract.image_to_string(p)
        return text
    except Exception:
        return ""


# -------------------------------------------------------------
# RULE-BASED EXTRACTION
# -------------------------------------------------------------
def rule_based_extract(text: str) -> dict:
    """Extract simple specs based on keywords.
    Returns a dict with possible fields found.
    """

    text_low = text.lower()
    specs = {}

    # Example rules — can be expanded

    # Detect area in sq ft / sqm
    area_match = re.search(r"(\d{3,7})\s*(sq\.?\s*ft|square\s*feet|sqm|sq\.?\s*m)", text_low)
    if area_match:
        specs["area"] = area_match.group(0)

    # Detect scope: interior/exterior
    if "interior" in text_low:
        specs.setdefault("application", []).append("interior")
    if "exterior" in text_low or "weather-proof" in text_low or "weatherproof" in text_low:
        specs.setdefault("application", []).append("exterior")

    # Detect eco-friendly
    if "low voc" in text_low or "low-voc" in text_low:
        specs["low_voc"] = True

    # Warranty requirement
    warr = re.search(r"(\d+)\s*-?year\s*warranty", text_low)
    if warr:
        specs["warranty_years_required"] = int(warr.group(1))

    # Detect keywords related to antibacterial / antifungal
    if "anti-bacterial" in text_low or "antibacterial" in text_low:
        specs["needs_antibacterial"] = True
    if "anti-fungal" in text_low or "antifungal" in text_low:
        specs["needs_antifungal"] = True

    return specs


# -------------------------------------------------------------
# LLM FALLBACK EXTRACTION
# -------------------------------------------------------------
def llm_extract_specs(text: str, rfp_id: str) -> dict:
    """Call OpenAI GPT-4.1 to extract specs in structured JSON.
    Logs raw output for debugging.
    """

    if not llm_client:
        return {}

    prompt = f"""
You are a specification extraction assistant.
Extract all key requirements from this RFP in JSON.
Include:
- application areas (interior, exterior, metal, concrete, etc.)
- environmental requirements (low VOC, eco-friendly)
- technical performance (washability, durability, antibacterial, antifungal)
- warranty requirements
- coverage or area details

Text:
{text}

Return ONLY JSON.
    """

    resp = llm_client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw_output = resp.choices[0].message.content

    # Log raw LLM output
    with open(os.path.join(LOG_DIR, f"{rfp_id}_spec_llm.txt"), "w") as f:
        f.write(raw_output)

    try:
        return json.loads(raw_output)
    except Exception:
        return {}


# -------------------------------------------------------------
# MAIN ENTRYPOINT
# -------------------------------------------------------------
def extract_specs_from_rfp(rfp: dict) -> dict:
    """Extract specs from an RFP using rule-based+LLM+PDF text.
    Returns structured dictionary.
    """

    rfp_id = rfp.get("id", "unknown")
    title = rfp.get("title", "")
    desc = rfp.get("description", "")

    # Gather text from PDFs
    pdf_text = ""
    for doc in rfp.get("documents", []):
        url = doc.get("url")
        if not url:
            continue
        pdf_path = download_pdf(url)
        if pdf_path:
            pdf_text += "\n" + extract_pdf_text(pdf_path)

    combined_text = f"{title}\n{desc}\n{pdf_text}".strip()

    # 1. Rule-based first
    rule_specs = rule_based_extract(combined_text)

    # If rule-based extraction found enough info → return it
    if len(rule_specs) >= 2:
        return rule_specs

    # 2. LLM fallback
    llm_specs = llm_extract_specs(combined_text, rfp_id)

    # Merge rule + LLM
    merged = {**llm_specs, **rule_specs}
    return merged
