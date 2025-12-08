# scripts/run_live.py
import sys
import pathlib
import asyncio
import json
import os

# ensure repo root is on sys.path so "import src..." works
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]  # repo_root/scripts/.. -> repo_root
sys.path.insert(0, str(REPO_ROOT))

from src.agents.agent_manager import AgentManager

SEEDS_PATH = "logs/seeds/seeds.json"  # relative to repo root

def load_seeds(path=SEEDS_PATH):
    p = REPO_ROOT / path
    if not p.exists():
        print("No seeds file found at", p)
        return []
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(j, list):
            return j
        if isinstance(j, dict) and "seeds" in j and isinstance(j["seeds"], list):
            return j["seeds"]
    except Exception as e:
        print("Failed to load seeds:", e)
    return []

async def main():
    seeds = load_seeds()
    print("Loaded seeds:", len(seeds))
    am = AgentManager(ollama_base="http://localhost:11434", model="llama3")
    # try adding seeds to frontier — adjust if your Frontier API is different
    added = 0
    for s in seeds:
        try:
            # many frontiers provide add(url) or add_seed(url)
            if hasattr(am.frontier, "add"):
                am.frontier.add(s)
            elif hasattr(am.frontier, "add_seed"):
                am.frontier.add_seed(s)
            else:
                # fallback: try to call a generic method
                try:
                    am.frontier.add_url(s)
                except Exception:
                    print("Couldn't add seed via known frontier API for:", s)
                    continue
            added += 1
        except Exception as e:
            print("Failed to add seed:", s, e)
    print(f"Seeds added to frontier: {added}")
    await am.run_once("Find coating and waterproofing tenders from seeds", max_steps=50)

if __name__ == "__main__":
    asyncio.run(main())
