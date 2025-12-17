from utils.errors import PricingError


def compute_material_cost(rfp, matched_skus, area, coat_overrides):

    sku_results = []
    total_material_cost = 0

    for item in matched_skus:
        sku = item["sku"]
        sku_id = sku["sku_id"]

        coverage = sku["coverage_sqft_per_litre"]
        coats = coat_overrides.get(sku_id, None)

        # If coats not provided by override → default category rule
        if coats is None:
            if "primer" in sku["category"].lower():
                coats = 1
            else:
                coats = 2

        litres_needed = (area / coverage) * coats

        unit_price = sku["pricing_inr"]["institutional_price_per_litre"]
        cost = litres_needed * unit_price
        total_material_cost += cost

        sku_results.append({
            "sku_id": sku_id,
            "coats": coats,
            "coverage_sqft_per_litre": coverage,
            "litres_needed": litres_needed,
            "unit_price_inr": unit_price,
            "material_cost_inr": cost
        })

    return {
        "skus": sku_results,
        "material_cost_total_inr": total_material_cost
    }


