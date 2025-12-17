# src/crawler/validator.py
import json
from jsonschema import validate, ValidationError
from typing import List, Dict
SCHEMA_PATH = "AutoRFP_agentic_system/web_crawler/src/schemas/rfp_extracted_v1.json"

with open(SCHEMA_PATH, "r") as f:
    SCHEMA = json.load(f)

class ValidationResult:
    def __init__(self, valid: bool, errors=None):
        self.valid = valid
        self.errors = errors or []

def validate_record(record: Dict) -> ValidationResult:
    try:
        validate(instance=record, schema=SCHEMA)
        return ValidationResult(valid=True)
    except ValidationError as e:
        return ValidationResult(valid=False, errors=[str(e)])

def validate_array(records: List[Dict]) -> ValidationResult:
    errors = []
    for i, r in enumerate(records):
        res = validate_record(r)
        if not res.valid:
            errors.append({"index": i, "errors": res.errors})
    if errors:
        return ValidationResult(valid=False, errors=errors)
    return ValidationResult(valid=True)
