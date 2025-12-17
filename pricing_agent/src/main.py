import json
import os
from loader import load_new_rfps, load_past_rfp_from_matched_id, load_sku_master
from cost_engine.material import compute_material_cost
from cost_engine.labour import compute_labour_cost
from cost_engine.llm import call_llm
from utils.file_utils import write_output
from utils.logs import log_raw_llm
from utils.errors import PricingError
from config import Config


def process_single_rfp(rfp):

    # 1. Extract matched SKUs
    matched_skus = rfp.get("matched_skus", [])
    if not matched_skus:
        print(f"[WARNING] No matched SKUs for {rfp['id']} — skipping.")
        return None

    # 2. Extract matched historical RFP ID
    hist = rfp.get("matched_historical_rfp", {})
    matched_id = hist.get("id", None)

    # 3. Load past RFP OR fallback
    if not matched_id:
        print(f"[WARNING] No historical RFP for {rfp['id']} → using fallback values")
        past_rfp = {
            "area": 50000,
            "labour_cost_inr": 100000
        }
        fallback_used = True
    else:
        past_rfp = load_past_rfp_from_matched_id(matched_id)
        fallback_used = False

    # 4. Apply rule engine (offline inference)
    from processors.rule_engine import apply_rules
    rules = apply_rules(rfp, matched_skus, past_rfp)

    inferred_area = rules["area"]
    coat_overrides = rules["coat_overrides"]
    labour_factor = rules["labour_factor"]
    confidence = rules["confidence"]
    explanation = rules["explanation"]

    # 5. Material cost
    from cost_engine.material import compute_material_cost
    material_result = compute_material_cost(
        rfp, matched_skus, inferred_area, coat_overrides
    )

    # 6. Labour cost
    from cost_engine.labour import compute_labour_cost
    labour_result = compute_labour_cost(
        rfp, past_rfp, inferred_area, labour_factor
    )

    total_cost = (
        material_result["material_cost_total_inr"]
        + labour_result["labour_cost_inr"]
    )

    # 7. Build output JSON
    output = {
        "rfp_id": rfp["id"],
        "matched_historical_rfp": matched_id,
        "fallback_used": fallback_used,
        "area_used_sqft": inferred_area,

        "skus": material_result["skus"],
        "material_cost_total_inr": material_result["material_cost_total_inr"],
        "labour_cost_inr": labour_result["labour_cost_inr"],
        "total_cost_inr": total_cost,

        "confidence": confidence,
        "explanation": explanation,
        "similar_rfps_used": [matched_id] if matched_id else []
    }

    # 8. Write output
    from utils.file_utils import write_output
    write_output(rfp["id"], output)
    return output



def main():
    new_rfps = load_new_rfps(Config.NEW_RFP_DIR)
    sku_master = load_sku_master(Config.SKU_MASTER_PATH)

    for rfp in new_rfps:
        print(f"Processing RFP: {rfp['id']}")
        try:
            process_single_rfp(rfp)
        except Exception as e:
            print(f"Incomplete info in {rfp['id']}")
            continue  # move to next RFP



if __name__ == "__main__":
    main()

