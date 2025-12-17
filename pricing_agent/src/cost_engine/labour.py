def compute_labour_cost(rfp, past_rfp, area, labour_factor):

    past_area = past_rfp.get("area", 50000)
    past_labour_cost = past_rfp.get("labour_cost_inr", 100000)

    # Scale by ratio
    base = (area / past_area) * past_labour_cost

    # Apply complexity
    final = base * labour_factor

    return {"labour_cost_inr": final}
