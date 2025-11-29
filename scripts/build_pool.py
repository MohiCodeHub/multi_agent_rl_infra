#!/usr/bin/env python3
"""Build validated task pool"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient
from src.curriculum import TaskCurriculum
from src.environment import WebEnvironment


def main():
    parser = argparse.ArgumentParser(description="Build task pool")
    parser.add_argument("--api-key", help="Anthropic API key (uses hardcoded default if not provided)")
    parser.add_argument("--sites", nargs="+", default=["signup", "todo", "cart", "settings", "wizard"])
    parser.add_argument("--difficulties", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--tasks-per-difficulty", type=int, default=10)
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--output", default="task_pool.json")
    args = parser.parse_args()
    
    print("Initializing...")
    llm = LLMClient(api_key=args.api_key)
    curriculum = TaskCurriculum(llm, args.base_url)
    
    with WebEnvironment() as env:
        print(f"\nBuilding task pool:")
        print(f"  Sites: {args.sites}")
        print(f"  Difficulties: {args.difficulties}")
        print(f"  Tasks per difficulty: {args.tasks_per_difficulty}")
        
        curriculum.build_pool(
            sites=args.sites,
            difficulties=args.difficulties,
            tasks_per_difficulty=args.tasks_per_difficulty,
            env=env
        )
        
        curriculum.save(args.output)
        
        print("\nPool statistics:")
        for difficulty, stats in curriculum.stats().items():
            print(f"  Difficulty {difficulty}: {stats['count']} tasks, "
                  f"avg {stats['avg_min_actions']:.1f} actions")


if __name__ == "__main__":
    main()

