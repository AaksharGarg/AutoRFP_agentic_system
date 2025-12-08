# src/crawler/normalizer.py
import hashlib, datetime, re
from typing import Dict, Any, List, Optional
from dateutil import parser as dateparser

def deterministic_id(source_url: str, rfp_number: Optional[str], title: Optional[str]) -> str:
    base = (source_url or "") + "|" + (rfp_number or "") + "|" + (title or "")[:100]
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]

def _to_int_or_none(x):
    if x is None: return None
    try:
        return int(float(re.sub(r"[^\d.-]", "", str(x))))
    except Exception:
        return None

def _to_number_or_none(x):
    if x is None: return None
    try:
        return float(re.sub(r"[^\d.-]", "", str(x)))
    except Exception:
        return None

def _parse_date_iso(d):
    if not d: return None
    try:
        dt = dateparser.parse(d)
        return dt.date().isoformat()
    except Exception:
        return None

def _parse_datetime_iso(d):
    if not d: return None
    try:
        dt = dateparser.parse(d)
        return dt.isoformat() + "Z" if dt.tzinfo is None else dt.astimezone(datetime.timezone.utc).isoformat()
    except Exception:
        return None

def normalize_document(doc):
    # ensure required keys
    url = doc.get("url") or doc.get("link") or None
    filename = doc.get("filename") or doc.get("file_name") or (url.split("/")[-1] if url else None)
    filetype = doc.get("filetype") or doc.get("file_type") or None
    snippet = doc.get("extracted_text_snippet") or doc.get("snippet") or None
    filesize = _to_int_or_none(doc.get("filesize_bytes") or doc.get("filesize") or None)
    return {
        "url": url,
        "filename": filename,
        "filetype": filetype,
        "filesize_bytes": filesize,
        "extracted_text_snippet": snippet,
        "ocr_used": bool(doc.get("ocr_used", False)),
        "extraction_confidence": (doc.get("extraction_confidence") if isinstance(doc.get("extraction_confidence"), (int,float)) else None)
    }

def _extract_contact_from_old(contact_details):
    emails = []
    phones = []
    person = None
    if not contact_details:
        return {"contact_emails": [], "contact_phones": [], "contact_person": None}
    text = None
    if isinstance(contact_details, dict):
        # common shapes
        emails = contact_details.get("email") and [contact_details.get("email")] or contact_details.get("emails") or []
        if isinstance(emails, str): emails = [emails]
        phones = contact_details.get("phone") and [contact_details.get("phone")] or contact_details.get("phones") or []
        if isinstance(phones, str): phones = [phones]
        person = contact_details.get("contact_person") or contact_details.get("contact_name") or None
    else:
        text = str(contact_details)
        # simple regex
        emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        phones = re.findall(r"\+?\d[\d\-\s]{6,}\d", text)
    return {"contact_emails": emails or [], "contact_phones": phones or [], "contact_person": person}

def normalize_record(candidate: Dict[str, Any], source_url: str) -> Dict[str, Any]:
    # candidate: output of rule_extractor
    rfp_number = candidate.get("rfp_number") or candidate.get("tender_no") or None
    title = candidate.get("title") or candidate.get("heading") or None
    rec = {}
    rec["id"] = rfp_number if rfp_number else deterministic_id(source_url, rfp_number, title)
    rec["source_url"] = source_url
    rec["source_domain"] = (source_url.split("/")[2] if source_url and "://" in source_url else None)
    rec["crawl_timestamp"] = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    rec["language"] = candidate.get("language") or None
    rec["is_rfp"] = True if candidate.get("is_rfp") is not False else False
    rec["title"] = title or None
    rec["rfp_number"] = rfp_number or None
    rec["date_of_posting"] = _parse_date_iso(candidate.get("date_of_posting") or candidate.get("posted") or None)
    rec["duration_days"] = _to_int_or_none(candidate.get("duration_days") or candidate.get("duration") or None)
    rec["deadline_date"] = _parse_datetime_iso(candidate.get("deadline_date") or candidate.get("closing") or None)
    rec["estimated_budget_min"] = _to_number_or_none(candidate.get("budget_min") or candidate.get("estimated_budget_min") or None)
    rec["estimated_budget_max"] = _to_number_or_none(candidate.get("budget_max") or candidate.get("estimated_budget_max") or None)
    rec["currency"] = candidate.get("currency") or None
    rec["agency"] = candidate.get("agency") or None
    loc = candidate.get("location") or {}
    rec["location"] = {
        "country": loc.get("country") or None,
        "state": loc.get("state") or None,
        "city": loc.get("city") or None
    }
    # contact
    contact = candidate.get("contact") or _extract_contact_from_old(candidate.get("contact_details") or candidate.get("contact_info") or None)
    # ensure arrays
    contact["contact_emails"] = contact.get("contact_emails") or []
    contact["contact_phones"] = contact.get("contact_phones") or []
    contact["contact_person"] = contact.get("contact_person") or None
    rec["contact"] = contact
    rec["description"] = (candidate.get("description") or candidate.get("desc") or None)
    rec["requirements_summary"] = candidate.get("requirements_summary") or None
    # summary 50 words: keep only if it exists and schema allows it
    if candidate.get("summary_50_words"):
        rec["summary_50_words"] = candidate.get("summary_50_words")[:500]  # but ensure schema permits
    else:
        rec["summary_50_words"] = None
    # coating fields: prefer dict from candidate; else None
    rec["coating_fields"] = candidate.get("coating_fields") or None
    # docs normalize
    raw_docs = candidate.get("documents") or []
    rec["documents"] = [normalize_document(d) for d in raw_docs]
    # keywords/match
    rec["keywords"] = candidate.get("keywords") or []
    rec["matched_terms"] = candidate.get("matched_terms") or []
    rec["match_signals"] = candidate.get("match_signals") or {}
    rec["raw_html"] = candidate.get("raw_html") or None
    rec["raw_json"] = candidate.get("raw_json") or None
    rec["provenance"] = candidate.get("provenance") or {}
    return rec
