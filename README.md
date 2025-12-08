# AutoRFP Agentic System

A lightweight agentic crawler that finds coating/waterproofing RFPs, extracts structured data, and scores relevance.

## Quick start
1. **Install deps** (Python 3.10+):
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   python -m playwright install chromium
   ```
2. **Run Redis** (needed by frontier):
   ```bash
   redis-server --port 6379
   ```
3. **Start Ollama** with the required model (defaults: llama3) listening on `http://localhost:11434`.
4. **Seeds** live in `logs/seeds/seeds.json` (also mirrored in `config/seed_urls.yaml`). Edit as needed.
5. **Run the crawler loop**:
   ```bash
   python -m src.main --iterations 3 --max-steps 50 --goal "Find coating and waterproofing tenders"
   ```
   Override endpoints if needed:
   ```bash
   python -m src.main --ollama-base http://localhost:11434 --ollama-model llama3 --redis-url redis://localhost:6379/0
   ```

## Configuration
- `config/crawl_rules.yaml` — crawl depth, delay, user agent, allowed domains, Redis/Ollama endpoints, default goal.
- `config/seed_urls.yaml` — seed URLs with priority/depth/meta.
- `config/standards.yaml` — business profile, keywords, scoring thresholds (used by matching layer).
- `config/ollama_prompts.yaml` — model/endpoint knobs for planner (prompt text lives in `src/agents/planner_prompts.py`).

## Pipeline overview
- **AgentManager** seeds Redis frontier, fetches pages (Playwright), extracts candidates (regex/keywords), normalizes to `src/schemas/rfp_extracted_v1.json`, validates, and scores (Jaccard + cosine + LLM).
- **Runner** (`src/main.py`) enqueues seeds and iterates `AgentManager.run_once` with a configurable goal.

## Notes
- Make sure the sentence-transformers model downloads on first run (network access required).
- Some TODOs in matching (tfidf/ner) are still placeholders; they won’t block core crawling.
