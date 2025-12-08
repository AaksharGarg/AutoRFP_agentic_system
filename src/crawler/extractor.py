# src/crawler/extractor.py
"""
Rule-based extractor for RFP candidate detection.
This module DOES NOT try to satisfy full schema.
It only detects possible tender/RFP items in text
and returns lightweight "candidate" dicts.

Final normalization, LLM enrichment, and validation
happen downstream (normalizer.py + llm_helpers.py + validator.py)
"""

import re
from typing import List, Dict, Any
from urllib.parse import urlparse

# Keyword lists (expand anytime)
COATING_KEYWORDS = [
    "epoxy", "polyurethane", "polyurea", "alkyd",
    "waterproof", "waterproofing", "anti-corrosive",
    "fire-retardant", "flooring", "epoxy flooring",
    "shot blast", "sand blast", "hydroblast",
    "surface preparation", "PU membrane", "liquid membrane"
]

# Regex helpers
RFPN_RE = re.compile(r"\b(RFP|RFQ|EOI|Tender|Bid)[\s\-:]*([A-Za-z0-9\/\-\._]+)", re.I)
DATE_RE = re.compile(r"\d{1,2}[ \-/](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*[ \-/]\d{2,4}", re.I)
DATE_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[- ]?)?\d{7,12}")
DOC_RE = re.compile(r"(https?://[^\s\"\'<>]+?\.(?:pdf|docx|doc|xlsx))", re.I)


class Extractor:
    """
    Main extractor class used by AgentManager via `extract_all`.
    Kept lightweight and synchronous-friendly; exposed as async for ToolRegistry.
    """

    def __init__(self, *args, **kwargs):
        # Accept unused args to stay forward-compatible with AgentManager wiring.
        pass

    async def extract_all(self, url: str, html: str = None, text: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Entry point called by AgentManager.
        Accepts either raw HTML or plain text.

        Returns:
            List[Dict] of lightweight candidates.
        """
        page_text = text or html or ""
        return extract_candidates(url, page_text)


def extract_candidates(url: str, page_text: str) -> List[Dict[str, Any]]:
    """
    Core extraction function.
    Takes raw page_text and produces 1..N candidate objects.

    Candidate contains:
     - title
     - rfp_number
     - dates
     - budgets (currently empty, ready for upgrade)
     - contact_emails
     - contact_phones
     - documents
     - matched_keywords
     - raw_text
     - source_url
    """
    if not page_text:
        return []

    text = page_text[:200000]  # safety cutoff

    ### 1) TITLE heuristics (first strong line)
    title = None
    for line in text.split("\n"):
        s = line.strip()
        if 10 < len(s) < 180 and not s.islower():
            title = s
            break

    ### 2) RFP/Tender numbers
    rfps = []
    for m in RFPN_RE.findall(text):
        num = m[1].strip()
        if num:
            rfps.append(num)

    ### 3) Dates
    dates = []
    dates.extend(DATE_ISO_RE.findall(text))
    for m in DATE_RE.findall(text):
        dates.append(m)

    ### 4) Documents (.pdf/.docx/etc)
    docs = [{"url": u} for u in DOC_RE.findall(text)]

    ### 5) Contacts
    emails = list(set(EMAIL_RE.findall(text)))
    def _clean_phone(p: str):
        digits = re.sub(r"\D", "", p)
        return digits if 7 <= len(digits) <= 15 else None
    phones = list({d for d in (_clean_phone(p) for p in PHONE_RE.findall(text)) if d})

    ### 6) Coating keyword match
    matched_keywords = [
        kw for kw in COATING_KEYWORDS
        if re.search(r"\b" + re.escape(kw) + r"\b", text, re.I)
    ]

    # Drop pages that show no tender signals
    if not rfps and not docs and not matched_keywords and not dates:
        return []

    ### 7) Produce candidates: one per RFP number OR one default
    candidates = []

    if rfps:
        for rfp_no in rfps:
            candidates.append({
                "source_url": url,
                "title": title,
                "rfp_number": rfp_no,
                "dates": dates,
                "budgets": [],      # future enhancement
                "contact_emails": emails,
                "contact_phones": phones,
                "documents": docs,
                "matched_keywords": matched_keywords,
                "raw_text": text[:150000]
            })
    else:
        # fallback: one candidate for the whole page
        candidates.append({
            "source_url": url,
            "title": title,
            "rfp_number": None,
            "dates": dates,
            "budgets": [],
            "contact_emails": emails,
            "contact_phones": phones,
            "documents": docs,
            "matched_keywords": matched_keywords,
            "raw_text": text[:150000]
        })

    return candidates
