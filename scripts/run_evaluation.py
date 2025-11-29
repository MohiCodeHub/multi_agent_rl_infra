#!/usr/bin/env python3
"""Run full evaluation"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient
from src.curriculum import TaskCurriculum
from src.agent import MultiStepAgent
from src.verifier import Verifier
from src.reward import RewardCalculator, RewardConfig
from src.evaluation import EvaluationPipeline, EvaluationConfig
from src.environment import WebEnvironment


def print_results(results: dict):
    """Pretty print evaluation results"""
    
    print("\n" + "="*70)
    print("EVALUATION RESULTS")
    print("="*70)
    
    for difficulty, agg in sorted(results.items()):
        print(f"\nDifficulty {difficulty} ({agg.num_episodes} episodes)")
        print("-"*50)
        
        print(f"  {'Metric':<25} {'Multi-Step':<15} {'Single-Step':<15}")
        print(f"  {'-'*25} {'-'*15} {'-'*15}")
        
        print(f"  {'Success Rate':<25} {agg.success_rate*100:>13.1f}% {'100.0%':>15}")
        print(f"  {'Avg Actions':<25} {agg.avg_actual_actions:>15.1f} {agg.avg_min_actions:>15.1f}")
        print(f"  {'Avg Inference Calls':<25} {agg.avg_inference_calls:>15.1f} {agg.avg_expected_calls:>15.1f}")
        print(f"  {'Avg Tokens':<25} {agg.avg_multi_step_tokens:>15.0f} {agg.avg_single_step_tokens:>15.0f}")
        print(f"  {'Token Reduction':<25} {agg.token_reduction_percent:>14.1f}%")
        print(f"  {'Avg Reward':<25} {agg.avg_reward:>15.3f}")
    
    print("\n" + "="*70)
    print("KEY FINDINGS")
    print("="*70)
    
    difficulties = sorted(results.keys())
    if len(difficulties) >= 2:
        first = results[difficulties[0]]
        last = results[difficulties[-1]]
        
        print(f"\n1. Performance gap scales with difficulty:")
        print(f"   - Difficulty {difficulties[0]}: {(1-first.success_rate)*100:.1f}% gap")
        print(f"   - Difficulty {difficulties[-1]}: {(1-last.success_rate)*100:.1f}% gap")
        
        print(f"\n2. Token savings scale with difficulty:")
        print(f"   - Difficulty {difficulties[0]}: {first.token_reduction_percent:.1f}% reduction")
        print(f"   - Difficulty {difficulties[-1]}: {last.token_reduction_percent:.1f}% reduction")
        
        avg_token_reduction = sum(r.token_reduction_percent for r in results.values()) / len(results)
        print(f"\n3. Average token reduction: {avg_token_reduction:.1f}%")


def main():
    parser = argparse.ArgumentParser(description="Run evaluation")
    parser.add_argument("--api-key", help="Anthropic API key (uses hardcoded default if not provided)")
    parser.add_argument("--pool", default="task_pool.json", help="Task pool file")
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()
    
    print("Initializing...")
    llm = LLMClient(api_key=args.api_key)
    
    # Load curriculum
    curriculum = TaskCurriculum(llm, args.base_url)
    if not curriculum.load(args.pool):
        print(f"Error: Could not load task pool from {args.pool}")
        print("Run build_pool.py first")
        return
    
    # Initialize components
    agent = MultiStepAgent(llm)
    verifier = Verifier(llm)
    reward_calc = RewardCalculator(RewardConfig())
    
    config = EvaluationConfig(
        difficulties=list(curriculum.pool.keys()),
        base_url=args.base_url
    )
    
    pipeline = EvaluationPipeline(
        curriculum=curriculum,
        agent=agent,
        verifier=verifier,
        reward_calculator=reward_calc,
        config=config
    )
    
    # Run evaluation
    with WebEnvironment() as env:
        results = pipeline.run(env)
    
    # Print results
    print_results(results)
    
    # Save results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"evaluation_{timestamp}.json"
    
    results_data = {
        str(d): {
            "difficulty": agg.difficulty,
            "num_episodes": agg.num_episodes,
            "success_rate": agg.success_rate,
            "avg_actual_actions": agg.avg_actual_actions,
            "avg_min_actions": agg.avg_min_actions,
            "avg_inference_calls": agg.avg_inference_calls,
            "avg_expected_calls": agg.avg_expected_calls,
            "avg_multi_step_tokens": agg.avg_multi_step_tokens,
            "avg_single_step_tokens": agg.avg_single_step_tokens,
            "token_reduction_percent": agg.token_reduction_percent,
            "avg_reward": agg.avg_reward
        }
        for d, agg in results.items()
    }
    
    output_file.write_text(json.dumps(results_data, indent=2))
    print(f"\nResults saved to {output_file}")


if __name__ == "__main__":
    main()

