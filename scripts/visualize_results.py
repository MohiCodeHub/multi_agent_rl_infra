#!/usr/bin/env python3
"""
Visualization script for Multi-Step Web Agent Task Curriculum results.
Creates publication-ready charts for presentations.
"""

import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Professional color palette
COLORS = {
    'multi_step': '#2E86AB',      # Deep blue
    'single_step': '#A23B72',     # Magenta
    'reduction': '#28965A',       # Green
    'background': '#FAFAFA',
    'grid': '#E0E0E0',
    'text': '#2D3436',
}

# Font settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Helvetica Neue', 'Arial', 'DejaVu Sans']
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['figure.titlesize'] = 18


def load_results(filepath: str) -> dict:
    """Load evaluation results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def create_success_rate_chart(results: dict, output_path: Path):
    """
    Create a bar chart comparing success rates between multi-step and single-step agents.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    multi_step_rates = [results[str(d)]['success_rate'] * 100 for d in difficulties]
    single_step_rates = [100.0 for _ in difficulties]  # Oracle baseline is always 100%
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, multi_step_rates, width, 
                   label='Multi-Step Agent', color=COLORS['multi_step'],
                   edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x + width/2, single_step_rates, width,
                   label='Single-Step Oracle', color=COLORS['single_step'],
                   edgecolor='white', linewidth=1.5)
    
    # Add value labels on bars
    for bar, rate in zip(bars1, multi_step_rates):
        height = bar.get_height()
        ax.annotate(f'{rate:.0f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold',
                    color=COLORS['text'])
    
    for bar, rate in zip(bars2, single_step_rates):
        height = bar.get_height()
        ax.annotate(f'{rate:.0f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, fontweight='bold',
                    color=COLORS['text'])
    
    ax.set_xlabel('Task Difficulty (Number of Actions)', fontweight='bold', color=COLORS['text'])
    ax.set_ylabel('Success Rate (%)', fontweight='bold', color=COLORS['text'])
    ax.set_title('Success Rate Comparison: Multi-Step vs Single-Step Agents', 
                 fontweight='bold', color=COLORS['text'], pad=20)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'D{d}' for d in difficulties])
    ax.set_ylim(0, 115)
    
    ax.legend(loc='upper right', framealpha=0.9, edgecolor='none')
    ax.grid(axis='y', linestyle='--', alpha=0.7, color=COLORS['grid'])
    ax.set_axisbelow(True)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    
    plt.tight_layout()
    plt.savefig(output_path / 'success_rate_comparison.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'success_rate_comparison.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved success_rate_comparison.png/pdf")


def create_token_consumption_chart(results: dict, output_path: Path):
    """
    Create a bar chart comparing token consumption between multi-step and single-step agents.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    multi_step_tokens = [results[str(d)]['avg_multi_step_tokens'] for d in difficulties]
    single_step_tokens = [results[str(d)]['avg_single_step_tokens'] for d in difficulties]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, multi_step_tokens, width,
                   label='Multi-Step Agent (1 call)', color=COLORS['multi_step'],
                   edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x + width/2, single_step_tokens, width,
                   label='Single-Step Oracle (N calls)', color=COLORS['single_step'],
                   edgecolor='white', linewidth=1.5)
    
    # Add value labels on bars
    for bar, tokens in zip(bars1, multi_step_tokens):
        height = bar.get_height()
        ax.annotate(f'{tokens:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    color=COLORS['text'])
    
    for bar, tokens in zip(bars2, single_step_tokens):
        height = bar.get_height()
        ax.annotate(f'{tokens:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    color=COLORS['text'])
    
    ax.set_xlabel('Task Difficulty (Number of Actions)', fontweight='bold', color=COLORS['text'])
    ax.set_ylabel('Average Tokens Used', fontweight='bold', color=COLORS['text'])
    ax.set_title('Token Consumption: Multi-Step vs Single-Step Agents',
                 fontweight='bold', color=COLORS['text'], pad=20)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'D{d}' for d in difficulties])
    
    ax.legend(loc='upper left', framealpha=0.9, edgecolor='none')
    ax.grid(axis='y', linestyle='--', alpha=0.7, color=COLORS['grid'])
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    
    plt.tight_layout()
    plt.savefig(output_path / 'token_consumption_comparison.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'token_consumption_comparison.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved token_consumption_comparison.png/pdf")


def create_token_reduction_chart(results: dict, output_path: Path):
    """
    Create a bar chart showing token reduction percentage by difficulty.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    reductions = [results[str(d)]['token_reduction_percent'] for d in difficulties]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    x = np.arange(len(difficulties))
    
    # Color bars based on positive/negative reduction
    colors = [COLORS['reduction'] if r > 0 else '#E74C3C' for r in reductions]
    
    bars = ax.bar(x, reductions, color=colors, edgecolor='white', linewidth=1.5, width=0.6)
    
    # Add value labels on bars
    for bar, reduction in zip(bars, reductions):
        height = bar.get_height()
        va = 'bottom' if height >= 0 else 'top'
        offset = 3 if height >= 0 else -3
        ax.annotate(f'{reduction:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, offset), textcoords="offset points",
                    ha='center', va=va, fontsize=12, fontweight='bold',
                    color=COLORS['text'])
    
    # Add horizontal line at y=0
    ax.axhline(y=0, color=COLORS['grid'], linestyle='-', linewidth=1)
    
    ax.set_xlabel('Task Difficulty (Number of Actions)', fontweight='bold', color=COLORS['text'])
    ax.set_ylabel('Token Reduction (%)', fontweight='bold', color=COLORS['text'])
    ax.set_title('Token Reduction by Difficulty\n(Multi-Step vs Single-Step)',
                 fontweight='bold', color=COLORS['text'], pad=20)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'D{d}' for d in difficulties])
    
    ax.grid(axis='y', linestyle='--', alpha=0.7, color=COLORS['grid'])
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    
    # Add legend explaining colors
    positive_patch = mpatches.Patch(color=COLORS['reduction'], label='Token Savings')
    negative_patch = mpatches.Patch(color='#E74C3C', label='Token Overhead')
    ax.legend(handles=[positive_patch, negative_patch], loc='upper left', framealpha=0.9, edgecolor='none')
    
    plt.tight_layout()
    plt.savefig(output_path / 'token_reduction_by_difficulty.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'token_reduction_by_difficulty.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved token_reduction_by_difficulty.png/pdf")


def create_inference_calls_chart(results: dict, output_path: Path):
    """
    Create a bar chart comparing inference calls between multi-step and single-step agents.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    multi_step_calls = [results[str(d)]['avg_inference_calls'] for d in difficulties]
    single_step_calls = [results[str(d)]['avg_expected_calls'] for d in difficulties]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, multi_step_calls, width,
                   label='Multi-Step Agent', color=COLORS['multi_step'],
                   edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x + width/2, single_step_calls, width,
                   label='Single-Step Oracle', color=COLORS['single_step'],
                   edgecolor='white', linewidth=1.5)
    
    # Add value labels on bars
    for bar, calls in zip(bars1, multi_step_calls):
        height = bar.get_height()
        ax.annotate(f'{calls:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold',
                    color=COLORS['text'])
    
    for bar, calls in zip(bars2, single_step_calls):
        height = bar.get_height()
        ax.annotate(f'{calls:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=12, fontweight='bold',
                    color=COLORS['text'])
    
    ax.set_xlabel('Task Difficulty (Number of Actions)', fontweight='bold', color=COLORS['text'])
    ax.set_ylabel('LLM Inference Calls', fontweight='bold', color=COLORS['text'])
    ax.set_title('LLM Inference Calls: Multi-Step vs Single-Step Agents',
                 fontweight='bold', color=COLORS['text'], pad=20)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'D{d}' for d in difficulties])
    ax.set_ylim(0, max(single_step_calls) * 1.2)
    
    ax.legend(loc='upper left', framealpha=0.9, edgecolor='none')
    ax.grid(axis='y', linestyle='--', alpha=0.7, color=COLORS['grid'])
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    
    plt.tight_layout()
    plt.savefig(output_path / 'inference_calls_comparison.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'inference_calls_comparison.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved inference_calls_comparison.png/pdf")


def create_combined_dashboard(results: dict, output_path: Path):
    """
    Create a combined 2x2 dashboard with all key metrics.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor(COLORS['background'])
    
    # --- Success Rate (Top Left) ---
    ax1 = axes[0, 0]
    ax1.set_facecolor(COLORS['background'])
    
    multi_step_rates = [results[str(d)]['success_rate'] * 100 for d in difficulties]
    single_step_rates = [100.0 for _ in difficulties]
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    ax1.bar(x - width/2, multi_step_rates, width, label='Multi-Step', color=COLORS['multi_step'])
    ax1.bar(x + width/2, single_step_rates, width, label='Single-Step', color=COLORS['single_step'])
    
    ax1.set_xlabel('Difficulty')
    ax1.set_ylabel('Success Rate (%)')
    ax1.set_title('Success Rate Comparison', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f'D{d}' for d in difficulties])
    ax1.set_ylim(0, 115)
    ax1.legend(loc='lower left', fontsize=9)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # --- Token Consumption (Top Right) ---
    ax2 = axes[0, 1]
    ax2.set_facecolor(COLORS['background'])
    
    multi_step_tokens = [results[str(d)]['avg_multi_step_tokens'] for d in difficulties]
    single_step_tokens = [results[str(d)]['avg_single_step_tokens'] for d in difficulties]
    
    ax2.bar(x - width/2, multi_step_tokens, width, label='Multi-Step', color=COLORS['multi_step'])
    ax2.bar(x + width/2, single_step_tokens, width, label='Single-Step', color=COLORS['single_step'])
    
    ax2.set_xlabel('Difficulty')
    ax2.set_ylabel('Avg Tokens')
    ax2.set_title('Token Consumption', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f'D{d}' for d in difficulties])
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    
    # --- Token Reduction (Bottom Left) ---
    ax3 = axes[1, 0]
    ax3.set_facecolor(COLORS['background'])
    
    reductions = [results[str(d)]['token_reduction_percent'] for d in difficulties]
    colors = [COLORS['reduction'] if r > 0 else '#E74C3C' for r in reductions]
    
    ax3.bar(x, reductions, color=colors, width=0.6)
    ax3.axhline(y=0, color=COLORS['grid'], linestyle='-', linewidth=1)
    
    ax3.set_xlabel('Difficulty')
    ax3.set_ylabel('Token Reduction (%)')
    ax3.set_title('Token Savings by Difficulty', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels([f'D{d}' for d in difficulties])
    ax3.grid(axis='y', linestyle='--', alpha=0.5)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    
    # --- Inference Calls (Bottom Right) ---
    ax4 = axes[1, 1]
    ax4.set_facecolor(COLORS['background'])
    
    multi_step_calls = [results[str(d)]['avg_inference_calls'] for d in difficulties]
    single_step_calls = [results[str(d)]['avg_expected_calls'] for d in difficulties]
    
    ax4.bar(x - width/2, multi_step_calls, width, label='Multi-Step', color=COLORS['multi_step'])
    ax4.bar(x + width/2, single_step_calls, width, label='Single-Step', color=COLORS['single_step'])
    
    ax4.set_xlabel('Difficulty')
    ax4.set_ylabel('LLM Calls')
    ax4.set_title('LLM Inference Calls', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels([f'D{d}' for d in difficulties])
    ax4.legend(loc='upper left', fontsize=9)
    ax4.grid(axis='y', linestyle='--', alpha=0.5)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    
    # Add main title
    fig.suptitle('Multi-Step Web Agent Evaluation Dashboard', 
                 fontsize=18, fontweight='bold', color=COLORS['text'], y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path / 'evaluation_dashboard.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'evaluation_dashboard.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved evaluation_dashboard.png/pdf")


def create_token_consumption_with_reduction(results: dict, output_path: Path):
    """
    Create a bar chart showing token consumption with percentage reduction annotations.
    Combines token consumption and reduction into one compelling visual.
    """
    difficulties = sorted([int(d) for d in results.keys()])
    multi_step_tokens = [results[str(d)]['avg_multi_step_tokens'] for d in difficulties]
    single_step_tokens = [results[str(d)]['avg_single_step_tokens'] for d in difficulties]
    reductions = [results[str(d)]['token_reduction_percent'] for d in difficulties]
    
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, multi_step_tokens, width,
                   label='Multi-Step Agent (1 LLM call)', color=COLORS['multi_step'],
                   edgecolor='white', linewidth=1.5)
    bars2 = ax.bar(x + width/2, single_step_tokens, width,
                   label='Single-Step Oracle (N LLM calls)', color=COLORS['single_step'],
                   edgecolor='white', linewidth=1.5)
    
    # Add value labels on bars
    for bar, tokens in zip(bars1, multi_step_tokens):
        height = bar.get_height()
        ax.annotate(f'{tokens:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    color=COLORS['text'])
    
    for bar, tokens in zip(bars2, single_step_tokens):
        height = bar.get_height()
        ax.annotate(f'{tokens:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=10, fontweight='bold',
                    color=COLORS['text'])
    
    # Add percentage reduction annotations between bars
    for i, (multi, single, reduction) in enumerate(zip(multi_step_tokens, single_step_tokens, reductions)):
        # Position the annotation above both bars
        max_height = max(multi, single)
        
        # Color based on positive/negative reduction
        if reduction > 0:
            reduction_color = COLORS['reduction']
            label = f'-{reduction:.1f}%'
        else:
            reduction_color = '#E74C3C'
            label = f'+{abs(reduction):.1f}%'
        
        # Add a box with the reduction percentage
        ax.annotate(label,
                    xy=(x[i], max_height + 120),
                    ha='center', va='bottom',
                    fontsize=14, fontweight='bold',
                    color='white',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor=reduction_color, 
                             edgecolor='none', alpha=0.9))
    
    ax.set_xlabel('Task Difficulty (Number of Actions)', fontweight='bold', color=COLORS['text'], fontsize=13)
    ax.set_ylabel('Average Tokens Used', fontweight='bold', color=COLORS['text'], fontsize=13)
    ax.set_title('Token Consumption & Savings: Multi-Step vs Single-Step Agents',
                 fontweight='bold', color=COLORS['text'], pad=25, fontsize=16)
    
    ax.set_xticks(x)
    ax.set_xticklabels([f'Difficulty {d}' for d in difficulties], fontsize=11)
    
    # Add some headroom for the reduction labels
    ax.set_ylim(0, max(single_step_tokens) * 1.25)
    
    ax.legend(loc='upper left', framealpha=0.9, edgecolor='none', fontsize=11)
    ax.grid(axis='y', linestyle='--', alpha=0.7, color=COLORS['grid'])
    ax.set_axisbelow(True)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(COLORS['grid'])
    ax.spines['bottom'].set_color(COLORS['grid'])
    
    # Add subtitle explaining the badges
    fig.text(0.5, 0.01, 'Green badges = token savings vs single-step baseline | Red badges = overhead',
             ha='center', fontsize=10, color='gray', style='italic')
    
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.12)
    
    plt.savefig(output_path / 'token_consumption_with_savings.png', dpi=300, bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.savefig(output_path / 'token_consumption_with_savings.pdf', bbox_inches='tight',
                facecolor=COLORS['background'])
    plt.close()
    
    print(f"  ✓ Saved token_consumption_with_savings.png/pdf")


def main():
    parser = argparse.ArgumentParser(description="Visualize evaluation results")
    parser.add_argument("--results", default="results", help="Results directory or specific JSON file")
    parser.add_argument("--output", default="visualizations", help="Output directory for charts")
    args = parser.parse_args()
    
    results_path = Path(args.results)
    output_path = Path(args.output)
    output_path.mkdir(exist_ok=True)
    
    # Find the most recent results file
    if results_path.is_file():
        results_file = results_path
    else:
        results_files = sorted(results_path.glob("evaluation_*.json"), reverse=True)
        if not results_files:
            print(f"Error: No evaluation results found in {results_path}")
            return
        results_file = results_files[0]
    
    print(f"\nLoading results from: {results_file}")
    results = load_results(results_file)
    
    print(f"Generating visualizations...")
    
    # Create individual charts
    create_success_rate_chart(results, output_path)
    create_token_consumption_chart(results, output_path)
    create_token_reduction_chart(results, output_path)
    create_inference_calls_chart(results, output_path)
    
    # Create combined token chart (consumption + reduction %)
    create_token_consumption_with_reduction(results, output_path)
    
    # Create combined dashboard
    create_combined_dashboard(results, output_path)
    
    print(f"\n✅ All visualizations saved to {output_path}/")
    print("\nGenerated files:")
    for f in sorted(output_path.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    main()

