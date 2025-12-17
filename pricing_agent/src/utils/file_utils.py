import json
import os
from config import Config

def write_output(rfp_id, data):
    path = os.path.join(Config.OUTPUT_DIR, f"{rfp_id}.json")
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)

