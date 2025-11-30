# Multi-Step Web Agent Task Curriculum

RL training infrastructure for multi-step web agents. Generates tasks at controllable difficulty (planning horizon), validates with oracle, evaluates efficiency-accuracy tradeoff.

## Overview

This project builds RL training infrastructure for multi-step web agents. The core contribution is a task curriculum where difficulty equals planning horizon (number of actions required). The system:

1. **Generates tasks via LLM** based on site specifications
2. **Validates tasks with an oracle agent** using single-step prediction
3. **Evaluates multi-step agents** against validated tasks
4. **Measures the efficiency-accuracy tradeoff** between multi-step and single-step prediction

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GENERATION PHASE                                │
│  Site Specs → Task Generator (LLM) → Oracle Validator → Task Pool (Cache)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             EVALUATION PHASE                                 │
│  Task Pool → Multi-Step Agent → LLM Verifier → Reward Calculator → Results  │
│                    ↓                                                        │
│              Web Environment (Playwright) → Mock Websites (localhost)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Set API key

**Option A: Use hardcoded default** (already configured):
```bash
# No setup needed - key is hardcoded in src/llm_client.py
```

**Option B: Override with command-line argument**:
```bash
# Pass your own key to any script
python scripts/build_pool.py --api-key sk-ant-...
```

**Option C: Use environment variable**:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

The system checks in this order: CLI arg → env var → hardcoded default

### 3. Generate mock websites

```bash
python scripts/generate_sites.py
```

This creates interactive HTML pages for:
- **signup** - User registration with validation
- **todo** - Todo list with CRUD operations
- **cart** - Shopping cart with checkout
- **settings** - User preferences with toggles
- **wizard** - Multi-step form wizard

### 4. Start mock site server (in separate terminal)

```bash
python mock_sites/server.py
```

Server runs at http://localhost:3000

## Usage

### Build Task Pool

Generate and validate tasks at various difficulty levels:

```bash
python scripts/build_pool.py --tasks-per-difficulty 10
```

Options:
- `--api-key` - Anthropic API key (optional, uses hardcoded default)
- `--sites` - Sites to use (default: all)
- `--difficulties` - Difficulty levels (default: 1-5)
- `--tasks-per-difficulty` - Tasks per level (default: 10)
- `--base-url` - Mock site URL (default: http://localhost:3000)
- `--output` - Output filename (default: task_pool.json)

### Run Evaluation

Evaluate multi-step agent against the task pool:

```bash
python scripts/run_evaluation.py
```

Options:
- `--api-key` - Anthropic API key (optional, uses hardcoded default)
- `--pool` - Task pool file (default: task_pool.json)
- `--base-url` - Mock site URL (default: http://localhost:3000)
- `--output-dir` - Results directory (default: results/)

## Output

Results are saved to `results/` directory as JSON with metrics:

| Metric | Description |
|--------|-------------|
| `success_rate` | Task completion rate |
| `avg_actual_actions` | Average actions taken |
| `avg_min_actions` | Optimal actions (oracle) |
| `avg_inference_calls` | Multi-step LLM calls |
| `avg_expected_calls` | Expected calls |
| `avg_multi_step_tokens` | Tokens used by multi-step |
| `avg_single_step_tokens` | Tokens used by oracle |
| `token_reduction_percent` | Token savings |
| `avg_reward` | Efficiency-weighted reward |

## Project Structure

```
/multi-step-curriculum
├── /mock_sites           # Mock websites for testing
│   ├── /signup/          # Registration form
│   ├── /todo/            # Todo list
│   ├── /cart/            # Shopping cart
│   ├── /settings/        # User settings
│   ├── /wizard/          # Multi-step wizard
│   └── server.py         # HTTP server
│
├── /src                  # Core library
│   ├── models.py         # Data classes
│   ├── environment.py    # Playwright wrapper
│   ├── generator.py      # Task generation
│   ├── oracle.py         # Task validation
│   ├── agent.py          # Multi-step agent
│   ├── verifier.py       # Success verification
│   ├── reward.py         # Reward calculation
│   ├── curriculum.py     # Task pool management
│   ├── evaluation.py     # Evaluation pipeline
│   └── token_counter.py  # Token tracking
│
├── /scripts              # CLI tools
│   ├── generate_sites.py # Create mock websites
│   ├── build_pool.py     # Generate/validate tasks
│   └── run_evaluation.py # Run evaluation
│
├── /results              # Generated outputs
├── /task_cache           # Cached task pools
├── config.yaml           # Configuration
├── requirements.txt      # Dependencies
└── README.md             # This file
```

## Key Concepts

### Difficulty = Planning Horizon

Task difficulty is defined by the number of sequential actions required:
- **Difficulty 1**: Single action (click a button)
- **Difficulty 3**: Fill form and submit
- **Difficulty 5**: Multi-step wizard with validation

### Oracle Validation

Each generated task is validated by an oracle agent using single-step prediction:
- Ensures tasks are completable
- Establishes ground-truth difficulty (min_actions)
- Records baseline token usage for comparison

### Reward Function

Reward balances action efficiency and inference efficiency:

```
reward = (action_weight × action_efficiency + inference_weight × inference_efficiency) × penalty
```

Where:
- `action_efficiency = min(1, min_actions / actual_actions)`
- `inference_efficiency = min(1, expected_calls / actual_calls)`
- `penalty = exp(-deviation_penalty × extra_steps)`

### Multi-Step vs Single-Step Tradeoff

- **Single-step**: One LLM call per action (accurate but expensive)
- **Multi-step**: Predict all actions at once (efficient but may need replanning)

The evaluation measures:
- How much token savings multi-step provides
- How accuracy degrades with difficulty
- When replanning is needed

## Configuration

Edit `config.yaml` to customize:

```yaml
llm:
  model: "claude-sonnet-4-20250514"
  temperature: 0.7

reward:
  action_weight: 0.6
  inference_weight: 0.4
  action_deviation_penalty: 0.15
```

## License

MIT

