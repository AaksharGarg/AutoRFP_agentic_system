# src/crawler/normalize.py
import json, time, urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

def _make_id(rec: Dict[str, Any], source_url: Optional[str]) -> str:
    # deterministic-ish id: prefer rfp_number then source_url then uuid
    if rec.get("rfp_number"):
        return str(rec["rfp_number"])
    if source_url:
        return urllib.parse.urlparse(source_url).path.replace("/", "_").strip("_") or str(uuid.uuid4())
    return str(uuid.uuid4())

def _ensure_filename_from_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    p = urllib.parse.urlparse(url).path
    if not p:
        return None
    name = p.split("/")[-1]
    return name or None

def normalize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    # normalize document fields to schema: url, filename, filetype, filesize_bytes, extracted_text_snippet, ocr_used, extraction_confidence
    out = {}
    out["url"] = doc.get("url") or doc.get("link") or doc.get("document_url") or None
    out["filename"] = doc.get("filename") or doc.get("name") or _ensure_filename_from_url(out["url"]) or ""
    # some sources use file_type or filetype; accept both
    out["filetype"] = doc.get("filetype") or doc.get("file_type") or doc.get("mime") or ""
    out["filesize_bytes"] = doc.get("filesize_bytes") if isinstance(doc.get("filesize_bytes"), int) else None
    # snippet fields
    snippet = doc.get("extracted_text_snippet") or doc.get("snippet") or doc.get("text") or None
    if isinstance(snippet, (list, dict)):
        snippet = json.dumps(snippet)[:500]
    if isinstance(snippet, str):
        out["extracted_text_snippet"] = snippet[:500]
    else:
        out["extracted_text_snippet"] = None
    out["ocr_used"] = bool(doc.get("ocr_used")) if doc.get("ocr_used") is not None else False
    # confidence may be missing
    try:
        conf = doc.get("extraction_confidence")
        out["extraction_confidence"] = float(conf) if conf is not None else None
    except Exception:
        out["extraction_confidence"] = None
    return out

def normalize_contact(raw: Dict[str, Any]) -> Dict[str, Any]:
    # Accept both contact and contact_details keys
    cd = raw or {}
    out = {
        "contact_emails": [],
        "contact_phones": [],
        "contact_person": None
    }
    # emails: might be string or list
    emails = cd.get("contact_emails") or cd.get("emails") or cd.get("email")
    if isinstance(emails, str):
        out["contact_emails"] = [emails]
    elif isinstance(emails, list):
        out["contact_emails"] = [e for e in emails if isinstance(e, str)]
    else:
        out["contact_emails"] = []

    phones = cd.get("contact_phones") or cd.get("phones") or cd.get("phone")
    if isinstance(phones, str):
        out["contact_phones"] = [phones]
    elif isinstance(phones, list):
        out["contact_phones"] = [p for p in phones if isinstance(p, str)]
    else:
        out["contact_phones"] = []

    out["contact_person"] = cd.get("contact_person") or cd.get("contact_name") or None
    return out

def normalize_coating_fields(raw: Any) -> Optional[Dict[str, Any]]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    # keep whatever model provided, but normalise keys ink-lower
    out = {}
    out["coating_type"] = raw.get("coating_type") or raw.get("coating") or raw.get("type") or None
    out["surface_type"] = raw.get("surface_type") or raw.get("surface") or None
    out["certifications"] = raw.get("certifications") or []
    out["sector"] = raw.get("sector") or None
    return out

def normalize_record(rec: Dict[str, Any], source_url: Optional[str]) -> Dict[str, Any]:
    # Map and rename fields to match your schema exactly.
    out: Dict[str, Any] = {}

    # minimal required source fields
    out["source_url"] = rec.get("source_url") or source_url or None
    # attempt to fill source_domain
    if out["source_url"]:
        out["source_domain"] = urllib.parse.urlparse(out["source_url"]).netloc
    else:
        out["source_domain"] = rec.get("source_domain") or None

    out["crawl_timestamp"] = datetime.utcnow().isoformat() + "Z"
    out["language"] = rec.get("language") or None
    out["is_rfp"] = bool(rec.get("is_rfp")) if rec.get("is_rfp") is not None else True

    out["title"] = rec.get("title") or rec.get("name") or None
    out["rfp_number"] = rec.get("rfp_number") or rec.get("tender_number") or None

    # dates: date_of_posting (date), deadline_date (datetime)
    out["date_of_posting"] = rec.get("date_of_posting") or rec.get("posted_on") or None
    dd = rec.get("deadline_date") or rec.get("closing_date") or rec.get("deadline")
    # normalize deadline to ISO if possible - leave as string if model returned ISO
    out["deadline_date"] = dd or None

    # duration
    out["duration_days"] = rec.get("duration_days") if isinstance(rec.get("duration_days"), int) else None

    # budgets map
    out["estimated_budget_min"] = rec.get("estimated_budget_min") or rec.get("budget_min") or rec.get("budget_lower") or None
    out["estimated_budget_max"] = rec.get("estimated_budget_max") or rec.get("budget_max") or rec.get("budget_upper") or None
    out["currency"] = rec.get("currency") or None
    out["agency"] = rec.get("agency") or rec.get("department") or None

    # location subobject
    loc = rec.get("location") or {}
    out["location"] = {
        "country": loc.get("country") if loc.get("country") is not None else None,
        "state": loc.get("state") if loc.get("state") is not None else None,
        "city": loc.get("city") if loc.get("city") is not None else None
    }

    # contacts
    contact_raw = rec.get("contact") or rec.get("contact_details") or {}
    out["contact"] = normalize_contact(contact_raw)

    # description + requirements
    out["description"] = rec.get("description") or None
    out["requirements_summary"] = rec.get("requirements_summary") or rec.get("scope") or None

    # 50-word summary if present, but schema doesn't require it (avoid adding unexpected property)
    # schema does not include "summary_50_words", so do not include it (drop it)

    # coating_fields mapping
    out["coating_fields"] = normalize_coating_fields(rec.get("coating_fields") or rec.get("coatings"))    

    # documents: normalize each doc
    docs = rec.get("documents") or []
    norm_docs: List[Dict[str, Any]] = []
    for d in docs:
        try:
            nd = normalize_document(d)
            # ensure required keys exist (url + filename + filetype + extracted_text_snippet)
            # fill empty filename if missing
            if not nd.get("filename"):
                nd["filename"] = _ensure_filename_from_url(nd.get("url")) or ""
            if not nd.get("filetype"):
                nd["filetype"] = ""
            # keep ocr_used as bool
            nd.setdefault("ocr_used", False)
            norm_docs.append(nd)
        except Exception:
            continue
    out["documents"] = norm_docs

    out["keywords"] = rec.get("keywords") or []
    out["matched_terms"] = rec.get("matched_terms") or []
    out["match_signals"] = rec.get("match_signals") or {}
    out["raw_html"] = rec.get("raw_html") or None
    out["raw_json"] = rec.get("raw_json") or None
    out["provenance"] = rec.get("provenance") or {}

    # id: generate deterministic id if not present
    out["id"] = rec.get("id") or _make_id(rec, out["source_url"])

    # Ensure required schema keys present (the schema requires title, date_of_posting, deadline_date, description, documents)
    # we won't fabricate them; keep None if missing
    # Return exactly the target fields only
    # Reorder to match schema order (not required, but nice)
    ordered = {
        "id": out["id"],
        "source_url": out["source_url"],
        "source_domain": out["source_domain"],
        "crawl_timestamp": out["crawl_timestamp"],
        "language": out["language"],
        "is_rfp": out["is_rfp"],
        "title": out["title"],
        "rfp_number": out["rfp_number"],
        "date_of_posting": out["date_of_posting"],
        "duration_days": out["duration_days"],
        "deadline_date": out["deadline_date"],
        "estimated_budget_min": out["estimated_budget_min"],
        "estimated_budget_max": out["estimated_budget_max"],
        "currency": out["currency"],
        "agency": out["agency"],
        "location": out["location"],
        "contact": out["contact"],
        "description": out["description"],
        "requirements_summary": out["requirements_summary"],
        "coating_fields": out["coating_fields"],
        "documents": out["documents"],
        "keywords": out["keywords"],
        "matched_terms": out["matched_terms"],
        "match_signals": out["match_signals"],
        "raw_html": out["raw_html"],
        "raw_json": out["raw_json"],
        "provenance": out["provenance"],
    }
    return ordered

def normalize_array(arr: List[Dict[str, Any]], source_url: Optional[str]) -> List[Dict[str, Any]]:
    out = []
    for rec in arr:
        try:
            nr = normalize_record(rec, source_url)
            out.append(nr)
        except Exception:
            continue
    return out
