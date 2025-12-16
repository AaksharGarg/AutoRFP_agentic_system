# run_priority_queue.py
"""
Entry script to run the entire Priority Queue scoring pipeline.
Uses runner.run_all() to score all RFPs inside new_rfps/.
"""

import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append(BASE_DIR)

from priority_queue.src.runner import run_all


def main():
    print("Running Priority Queue Layer-4...")
    outputs = run_all()
    print(f"Processed {len(outputs)} RFPs.")

    # optional: write a combined file for dashboard
    combined_path = os.path.join(BASE_DIR, "outputs", "combined_scores.json")
    json.dump(outputs, open(combined_path, "w"), indent=2)

    print(f"Combined output saved to {combined_path}")


if __name__ == "__main__":
    main()
