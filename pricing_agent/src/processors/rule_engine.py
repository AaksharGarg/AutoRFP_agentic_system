import re

def extract_area_from_text(text):
    try:
        # always convert to string
        if not isinstance(text, str):
            text = ""

        patterns = [
            r"(\d[\d,\.]+)\s*sq\s*ft",
            r"(\d[\d,\.]+)\s*sqft",
            r"(\d[\d,\.]+)\s*sqm",
            r"(\d[\d,\.]+)\s*sq\s*m",
            r"area\s*[:\-]\s*(\d[\d,\.]+)"
        ]

        for p in patterns:
            try:
                m = re.search(p, text, re.IGNORECASE)
                if m:
                    num = float(m.group(1).replace(",", ""))

                    # sqm → sqft
                    if "sqm" in p or "sq m" in p:
                        num = num * 10.7639

                    return int(num)
            except:
                pass

        return None

    except:
        return None




def determine_coats(category):
    cat = category.lower()
    if "primer" in cat:
        return 1
    if "putty" in cat:
        return 1
    if "interior" in cat:
        return 2
    if "exterior" in cat:
        return 2
    if "texture" in cat or "finish" in cat:
        return 2
    if "industrial" in cat:
        return 3
    if "waterproof" in cat:
        return 2
    return 2  # default


def determine_labour_factor(rfp):
    text = rfp["rfp"]["description"].lower()
    factor = 1.0

    if "hospital" in text:
        factor *= 1.25
    if "industrial" in text or "chemical" in text or "refinery" in text:
        factor *= 1.40
    if "texture" in text:
        factor *= 1.50
    if "waterproof" in text:
        factor *= 1.35
    if "exterior" in text and "tower" in text:
        factor *= 1.20

    return factor


def apply_rules(rfp, matched_skus, past_rfp):

    # 1. AREA
    area_raw = rfp.get("specs", {}).get("area", "")
    if area_raw and "000" not in area_raw:
        # Example: "80000 sq ft"
        area_num = int(re.findall(r"\d+", area_raw)[0])
        area = area_num
        conf = "high"
    else:
        # try description
        desc = (rfp.get("rfp", {}).get("description") or "")

        area_guess = extract_area_from_text(desc)
        if area_guess:
            area = area_guess
            conf = "medium"
        else:
            area = 50000  # default fallback
            conf = "low"

    # 2. COATS
    coat_overrides = {}
    for item in matched_skus:
        sku = item["sku"]
        category = sku.get("category", "")
        coat_overrides[sku["sku_id"]] = determine_coats(category)

    # 3. LABOUR COMPLEXITY FACTOR
    labour_factor = determine_labour_factor(rfp)

    # 4. EXPLANATION
    explanation = (
        f"Area used: {area} sqft. "
        f"Confidence: {conf}. "
        f"Coats per SKU based on category rules. "
        f"Labour multiplier: {labour_factor}. "
    )

    return {
        "area": area,
        "coat_overrides": coat_overrides,
        "labour_factor": labour_factor,
        "confidence": {"area_confidence": conf},
        "explanation": explanation
    }
