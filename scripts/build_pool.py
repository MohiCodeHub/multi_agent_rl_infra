#!/usr/bin/env python3
"""Build validated task pool"""

import argparse
import sys
import traceback
import os
import subprocess
import time
import urllib.request
from urllib.error import URLError
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient
from src.curriculum import TaskCurriculum
from src.environment import WebEnvironment


def main():
    parser = argparse.ArgumentParser(description="Build task pool")
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--sites", nargs="+", default=["signup", "todo", "cart", "settings", "wizard"])
    parser.add_argument("--difficulties", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    parser.add_argument("--tasks-per-difficulty", type=int, default=10)
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--output", default="task_pool.json")
    args = parser.parse_args()

    try:
        print("Initializing...")
        if not args.api_key:
            env_key = os.environ.get("ANTHROPIC_API_KEY")
            if not env_key:
                raise ValueError("Anthropic API key missing. Provide --api-key or set ANTHROPIC_API_KEY.")
            args.api_key = env_key

        def ensure_server(url: str):
            try:
                with urllib.request.urlopen(url, timeout=2) as _:
                    return False  # already running
            except Exception:
                print("Base URL unreachable; starting mock sites server...")
                server_proc = subprocess.Popen([sys.executable, str(Path(__file__).parent.parent / 'mock_sites' / 'server.py')])
                # Wait for server to come up
                for _ in range(10):
                    try:
                        with urllib.request.urlopen(url, timeout=1) as _:
                            print("Mock sites server started.")
                            return server_proc
                    except Exception:
                        time.sleep(0.5)
                raise RuntimeError("Failed to start mock sites server at " + url)

        server_proc = ensure_server(args.base_url + "/")

        llm = LLMClient(api_key=args.api_key)
        curriculum = TaskCurriculum(llm, args.base_url)

        with WebEnvironment() as env:
            print(f"\nBuilding task pool:")
            print(f"  Base URL: {args.base_url}")
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
                print(f"  Difficulty {difficulty}: {stats['count']} tasks, avg {stats['avg_min_actions']:.1f} actions")
        if server_proc:
            server_proc.terminate()
            server_proc.wait(timeout=5)
            print("Mock sites server stopped.")
    except Exception as e:
        print("ERROR: Task pool generation failed.")
        print(f"Reason: {e}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()

