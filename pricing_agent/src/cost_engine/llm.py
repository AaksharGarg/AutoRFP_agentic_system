import json
import openai
from config import Config
from utils.errors import PricingError


openai.api_key = Config.OPENAI_API_KEY


def call_llm(payload):

    system_prompt = """
You are a Pricing Validator AI. 
Infer area, resolve coats, assess labour complexity, and provide confidence (high/medium/low).
Return ONLY valid JSON with keys:
inferred_area, coat_overrides, labour_complexity_factor, explanation, confidence
"""

    user_prompt = f"""
RFP JSON:
{json.dumps(payload['rfp'])}

Matched SKUs:
{json.dumps(payload['matched_skus'])}

Past Similar RFP:
{json.dumps(payload['past_rfp'])}

Rules:
1. If area missing → infer from description.
2. Coat logic:
   - Primer: 1 coat
   - Others: 2 coats
   - Override only if clearly stated.
3. Labour complexity factor:
   - Hospitals +25%
   - Industrial +40%
   - Decorative +50%
   - Waterproofing +35%
   - Exterior high-rise +20%
4. Confidence: high / medium / low
"""

    try:
        completion = openai.ChatCompletion.create(
            model=Config.MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )

        text = completion["choices"][0]["message"]["content"]
        return json.loads(text)

    except Exception as e:
        raise PricingError(f"LLM Failure: {e}")

