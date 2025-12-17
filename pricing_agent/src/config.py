import os

class Config:
    MODEL = "gpt-4.1-mini"
    OUTPUT_DIR = "pricing_agent/outputs"
    LOG_DIR = "pricing_agent/logs"
    PAST_RFP_DIR = "priority_queue/past_rfps"
    NEW_RFP_DIR = "priority_queue/outputs"
    SKU_MASTER_PATH = "priority_queue/skus/sku_master.json"
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

