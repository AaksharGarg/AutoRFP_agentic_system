import os
from config import Config

def log_raw_llm(rfp_id, content):
    path = os.path.join(Config.LOG_DIR, f"{rfp_id}.txt")
    with open(path, "w") as fh:
        fh.write(str(content))

