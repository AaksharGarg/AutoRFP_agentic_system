import json
import os
import re
from utils.errors import PricingError
from config import Config


def load_new_rfps(path):
    """Load only files starting with 'RFP-' and ending in .json."""
    if not os.path.exists(path):
        raise PricingError(f"New RFP folder missing: {path}")

    rfps = []

    for f in os.listdir(path):
        if not f.endswith(".json"):
            continue
        if not f.startswith("RFP-"):
            continue

        full_path = os.path.join(path, f)
        with open(full_path, "r") as fh:
            rfps.append(json.load(fh))

    return rfps


def normalize_historical_id(hid):
    """
    Convert 'HIST-RFP-0213' → '0213'
    Convert 'HIST-RFP-213'  → '213'
    Convert any junk format   → digits only
    """
    if not hid:
        return None

    # extract the digits
    digits = re.findall(r"\d+", hid)
    if not digits:
        return None

    # if multiple digit groups exist, take the last one
    num = digits[-1]

    # You said you don't care about leading zeros,
    # but your filenames use EXACT digits from JSON,
    # so we keep them EXACT without editing.
    return num


def load_past_rfp_from_matched_id(hid):
    """
    Accepts hid = 'HIST-RFP-0213'
    Loads: past_rfps/rfp_0213.json
    """

    num = normalize_historical_id(hid)
    if not num:
        raise PricingError(f"Invalid matched historical RFP id: {hid}")

    filename = f"rfp_{num}.json"
    full_path = os.path.join(Config.PAST_RFP_DIR, filename)

    if not os.path.exists(full_path):
        raise PricingError(f"Past RFP not found: {full_path}")

    with open(full_path, "r") as fh:
        return json.load(fh)


def load_sku_master(path):
    if not os.path.exists(path):
        raise PricingError(f"SKU master missing: {path}")

    with open(path, "r") as f:
        return json.load(f)
