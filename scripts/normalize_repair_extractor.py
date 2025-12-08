# scripts/normalize_repair_extractor.py
import json, time, os, re
from urllib.parse import urlparse
from datetime import datetime
from dateutil import parser as dateparser
from jsonschema import validate, ValidationError

INPUT_DIR = "logs/raw"
SCHEMA_PATH = "src/schemas/rfp_extracted_v1.json"   # adjust if your schema path differs

def load_schema(path):
    if not os.path.exists(path):
        raise SystemExit(f"Schema not found at {path}")
    return json.load(open(path, "r", encoding="utf-8"))

def guess_filename_from_url(url):
    if not url:
        return None
    p = urlparse(url)
    name = os.path.basename(p.path) or None
    # If query-like filename present, take it
    if name and '.' in name:
        return name
    return None

def guess_filetype(entry):
    # prefer explicit keys, else try extension
    ft = entry.get("filetype") or entry.get("file_type") or ""
    if ft:
        return ft
    url = entry.get("url", "")
    if not url:
        return None
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext == ".pdf":
        return "application/pdf"
    if ext in (".doc", ".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if ext in (".xls", ".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return None

def parse_date_to_iso_date(s):
    if not s:
        return None
    try:
        dt = dateparser.parse(str(s), dayfirst=False)
        return dt.date().isoformat()
    except Exception:
        return None

def parse_date_to_iso_datetime(s):
    if not s:
        return None
    try:
        dt = dateparser.parse(str(s), dayfirst=False)
        # normalize to UTC-like naive ISO with time if time missing add 00:00:00
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ") if dt.time() != datetime.min.time() else dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None

def to_number(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return x
    s = str(x)
    # remove currency symbols and commas
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        if s == "":
            return None
        if "." in s:
            return float(s)
        return int(s)
    except Exception:
        try:
            return float(s)
        except:
            return None

def normalize_contact(cd):
    # input example: {"email": "a@b", "phone": "+91 ...", "address": "..."}
    if not cd or not isinstance(cd, dict):
        return {"contact_emails": [], "contact_phones": [], "contact_person": None}
    emails = []
    phones = []
    if "email" in cd:
        if isinstance(cd["email"], list):
            emails.extend(cd["email"])
        else:
            emails.append(cd["email"])
    if "contact_emails" in cd:
        if isinstance(cd["contact_emails"], list):
            emails.extend(cd["contact_emails"])
        else:
            emails.append(cd["contact_emails"])
    if "phone" in cd:
        if isinstance(cd["phone"], list):
            phones.extend(cd["phone"])
        else:
            phones.append(cd["phone"])
    if "contact_phones" in cd:
        if isinstance(cd["contact_phones"], list):
            phones.extend(cd["contact_phones"])
        else:
            phones.append(cd["contact_phones"])
    # dedupe and clean
    emails = [e for e in (emails or []) if e]
    phones = [p for p in (phones or []) if p]
    return {"contact_emails": emails, "contact_phones": phones, "contact_person": cd.get("contact_person") or cd.get("name") or None}

def normalize_document(doc):
    if not isinstance(doc, dict):
        return None
    url = doc.get("url")
    filename = doc.get("filename") or guess_filename_from_url(url) or None
    filetype = guess_filetype(doc)
    snippet = doc.get("extracted_text_snippet") or doc.get("extracted_text") or doc.get("snippet") or ""
    return {"url": url or None, "filename": filename, "filetype": filetype, "extracted_text_snippet": snippet or ""}

# --- REPLACE normalize_record with this version ---
def normalize_record(rec, parent_source_url=None):
    # map fields into schema names
    out = {}

    # preserve or generate id
    out["id"] = rec.get("id") or rec.get("rfp_number") or f"no-id-{int(time.time())}"

    # source fields - fill from record or parent_source_url
    out["source_url"] = rec.get("source_url") or rec.get("url") or parent_source_url or None
    out["source_domain"] = rec.get("source_domain") or (urlparse(out["source_url"]).netloc if out["source_url"] else None)
    out["crawl_timestamp"] = rec.get("crawl_timestamp") or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    out["language"] = rec.get("language") or None
    out["is_rfp"] = rec.get("is_rfp") if isinstance(rec.get("is_rfp"), bool) else True

    out["title"] = rec.get("title") or None
    out["rfp_number"] = rec.get("rfp_number") or None

    # dates
    out["date_of_posting"] = parse_date_to_iso_date(rec.get("date_of_posting")) or None
    dd = parse_date_to_iso_datetime(rec.get("deadline_date"))
    if dd is None:
        donly = parse_date_to_iso_date(rec.get("deadline_date"))
        dd = (donly + "T00:00:00Z") if donly else None
    out["deadline_date"] = dd

    # duration_days
    dur = rec.get("duration_days")
    if dur is None and out["date_of_posting"] and out["deadline_date"]:
        try:
            dp = dateparser.parse(out["date_of_posting"])
            dl = dateparser.parse(out["deadline_date"])
            out["duration_days"] = max(0, (dl.date() - dp.date()).days)
        except Exception:
            out["duration_days"] = None
    else:
        out["duration_days"] = int(dur) if isinstance(dur, (int, float)) else None

    # budgets mapping
    out["estimated_budget_min"] = to_number(rec.get("estimated_budget_min") or rec.get("budget_min") or rec.get("min_budget") or rec.get("budget_min"))
    out["estimated_budget_max"] = to_number(rec.get("estimated_budget_max") or rec.get("budget_max") or rec.get("max_budget") or rec.get("budget_max"))
    out["currency"] = rec.get("currency") or None

    out["agency"] = rec.get("agency") or None

    # location object
    loc = rec.get("location") or {}
    if isinstance(loc, str):
        out["location"] = {"country": loc, "state": None, "city": None}
    else:
        out["location"] = {
            "country": loc.get("country") or None,
            "state": loc.get("state") or None,
            "city": loc.get("city") or None
        }

    # contact mapping
    contact_in = rec.get("contact") or rec.get("contact_details") or rec.get("contact_info") or {}
    out["contact"] = normalize_contact(contact_in)

    out["description"] = rec.get("description") or None
    out["requirements_summary"] = rec.get("requirements_summary") or rec.get("requirements") or None

    out["coating_fields"] = rec.get("coating_fields") or None

    # documents - ensure required keys exist
    docs_in = rec.get("documents") or []
    out_docs = []
    for d in docs_in:
        nd = normalize_document(d)
        if nd:
            out_docs.append(nd)
    out["documents"] = out_docs

    return out

# --- REPLACE process_file to pass parent_source_url to normalize_record ---
def process_file(path, schema):
    j = json.load(open(path, "r", encoding="utf-8"))
    # Try to get the parent/source url from the debug file metadata
    parent_source_url = j.get("url") or j.get("source_url") or j.get("page_url") or None

    raw = j.get("raw") or ""
    arr = []
    try:
        parsed = json.loads(raw) if raw and isinstance(raw, str) and raw.strip().startswith("[") else None
        if isinstance(parsed, list):
            arr = parsed
    except Exception:
        if isinstance(j.get("repaired"), list):
            arr = j.get("repaired")
    if not arr:
        if isinstance(j, list):
            arr = j
    if not arr and j.get("raw") and j.get("raw").strip().startswith("{"):
        try:
            o = json.loads(j.get("raw"))
            arr = [o]
        except:
            pass
    if not arr:
        print("No parseable array found in", path)
        return None

    repaired = []
    errors = []
    for rec in arr:
        nr = normalize_record(rec, parent_source_url=parent_source_url)
        try:
            validate(instance=nr, schema=schema)
            repaired.append(nr)
        except ValidationError as e:
            errors.append({"record_sample": nr, "error": str(e)})
    return repaired, errors


def main():
    schema = load_schema(SCHEMA_PATH)
    files = sorted([os.path.join(INPUT_DIR, f) for f in os.listdir(INPUT_DIR) if f.startswith("extractor_invalid")], key=os.path.getmtime)
    if not files:
        print("No extractor_invalid files in", INPUT_DIR)
        return
    for f in files:
        print("Processing", f)
        repaired, errors = process_file(f, schema) or (None, None)
        ts = int(time.time())
        outpath = os.path.join(INPUT_DIR, f"extractor_repaired_{ts}.json")
        if repaired:
            json.dump({"source": f, "repaired": repaired, "errors": errors}, open(outpath, "w", encoding="utf-8"), indent=2)
            print("Saved repaired records to", outpath, "repaired_count=", len(repaired))
        else:
            json.dump({"source": f, "repaired": [], "errors": errors}, open(outpath, "w", encoding="utf-8"), indent=2)
            print("No repaired records; saved debug to", outpath)

if __name__ == "__main__":
    main()
