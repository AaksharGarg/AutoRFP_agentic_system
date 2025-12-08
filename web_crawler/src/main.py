import argparse
import asyncio
import logging
import pathlib

from src.agents.agent_manager import AgentManager
from src.config import load_settings, load_seeds


async def run_once_loop(goal: str, max_steps: int, iterations: int, ollama_base: str, ollama_model: str, redis_url: str, seeds_path: str):
    settings = load_settings()

    # Use CLI overrides if provided
    redis_url = redis_url or settings.redis_url
    ollama_base = ollama_base or settings.llm.base_url
    ollama_model = ollama_model or settings.llm.model
    goal = goal or settings.goal
    seeds = load_seeds(pathlib.Path(seeds_path)) if seeds_path else load_seeds()

    logging.info("Loaded %d seeds", len(seeds))

    agent = AgentManager(ollama_base=ollama_base, model=ollama_model, redis_url=redis_url)

    # enqueue seeds
    added = 0
    for seed in seeds:
        try:
            agent.frontier.add(seed)
            added += 1
        except Exception as e:
            logging.warning("Failed to add seed %s: %s", seed, e)
    logging.info("Seeds enqueued: %d", added)

    for i in range(iterations):
        logging.info("Iteration %d/%d", i + 1, iterations)
        await agent.run_once(goal, max_steps=max_steps)
        if agent.frontier.size() == 0:
            logging.info("Frontier empty; stopping early")
            break


def parse_args():
    parser = argparse.ArgumentParser(description="Run the AutoRFP crawler loop")
    parser.add_argument("--goal", default=None, help="Planner goal text")
    parser.add_argument("--max-steps", type=int, default=50, help="Max actions per plan")
    parser.add_argument("--iterations", type=int, default=3, help="How many planner iterations to run")
    parser.add_argument("--ollama-base", default=None, help="Ollama base URL")
    parser.add_argument("--ollama-model", default=None, help="Ollama model name")
    parser.add_argument("--redis-url", default=None, help="Redis connection URL")
    parser.add_argument("--seeds-path", default="logs/seeds/seeds.json", help="Path to seeds JSON/YAML")
    return parser.parse_args()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    args = parse_args()
    asyncio.run(
        run_once_loop(
            goal=args.goal,
            max_steps=args.max_steps,
            iterations=args.iterations,
            ollama_base=args.ollama_base,
            ollama_model=args.ollama_model,
            redis_url=args.redis_url,
            seeds_path=args.seeds_path,
        )
    )
