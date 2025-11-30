import json
import os
import subprocess
from pathlib import Path
import datetime
from collections import Counter
import streamlit as st

REPO_ROOT = Path(__file__).parent.parent.parent
TASK_POOL_PATH = REPO_ROOT / "task_cache" / "task_pool.json"
RESULTS_DIR = REPO_ROOT / "results"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_pool.py"

st.set_page_config(page_title="Multi-Agent RL Dashboard", layout="wide")
st.title("🤖 Multi-Agent RL Dashboard")

# Controls
with st.sidebar:
    st.header("Generate Tasks")
    tasks_per_difficulty = st.number_input("Tasks per difficulty", min_value=1, value=2)
    generate = st.button("Generate Task Pool")

# Trigger generation
if generate:
    cmd = [
        "python", str(BUILD_SCRIPT),
        "--tasks-per-difficulty", str(tasks_per_difficulty),
        "--output", str(TASK_POOL_PATH),
    ]
    # Ensure base URL is passed and API key forwarded when available
    cmd += ["--base-url", "http://localhost:3000"]
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        cmd += ["--api-key", api_key]
    with st.spinner("Generating tasks..."):
        try:
            subprocess.run(cmd, cwd=str(REPO_ROOT), check=True, capture_output=True, text=True)
            st.success("Task pool generated successfully.")
        except subprocess.CalledProcessError as e:
            st.error("Generation failed. Ensure mock server is running and ANTHROPIC_API_KEY is set.")
            st.code("python mock_sites\\server.py\nset ANTHROPIC_API_KEY=sk-ant-xxxxxxxx", language="bash")
            if e.stdout:
                st.text(e.stdout)
            if e.stderr:
                st.text(e.stderr)

# Helper: load latest results
def get_latest_results_file():
    if not RESULTS_DIR.exists():
        return None
    files = sorted(RESULTS_DIR.glob("evaluation_*.json"))
    return files[-1] if files else None

@st.cache_data
def load_task_pool():
    if not TASK_POOL_PATH.exists():
        return {}
    return json.loads(TASK_POOL_PATH.read_text())

@st.cache_data
def load_results(results_path: Path | None):
    if not results_path or not results_path.exists():
        return {}
    return json.loads(results_path.read_text())

# Load data
tasks = load_task_pool()
results_files = sorted(RESULTS_DIR.glob("evaluation_*.json"))
selected_name = None
if results_files:
    names = [f.name for f in results_files]
    selected_name = st.sidebar.selectbox("Results file", names, index=len(names)-1)
selected_path = (RESULTS_DIR / selected_name) if selected_name else None
results = load_results(selected_path)

# Tabs
overview_tab, tasks_tab = st.tabs(["Overview", "Tasks"])

# Overview: key metrics
with overview_tab:
    st.subheader("Key Metrics")
    # Aggregate overall metrics across difficulties if present
    def collect_metrics(res: dict):
        diffs = []
        for k, v in res.items():
            # results may be nested; collect dicts with expected keys
            if isinstance(v, dict) and all(key in v for key in (
                "success_rate","avg_actual_actions","avg_min_actions",
                "avg_multi_step_tokens","avg_single_step_tokens",
                "token_reduction_percent","avg_inference_calls","avg_expected_calls"
            )):
                diffs.append(v)
        return diffs

    diff_metrics = collect_metrics(results)
    if diff_metrics:
        total = len(diff_metrics)
        overall_success = sum(m["success_rate"] for m in diff_metrics) / total
        overall_token_reduction = sum(m["token_reduction_percent"] for m in diff_metrics) / total
        avg_multi_tokens = sum(m["avg_multi_step_tokens"] for m in diff_metrics) / total
        avg_single_tokens = sum(m["avg_single_step_tokens"] for m in diff_metrics) / total
        avg_actual_actions = sum(m["avg_actual_actions"] for m in diff_metrics) / total
        avg_min_actions = sum(m["avg_min_actions"] for m in diff_metrics) / total
        avg_inference_calls = sum(m["avg_inference_calls"] for m in diff_metrics) / total
        avg_expected_calls = sum(m["avg_expected_calls"] for m in diff_metrics) / total

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Success Rate", f"{overall_success*100:.1f}%")
            st.metric("Avg Actions (actual)", f"{avg_actual_actions:.1f}")
        with c2:
            st.metric("Token Reduction", f"{overall_token_reduction:.1f}%")
            st.metric("Avg Actions (min)", f"{avg_min_actions:.1f}")
        with c3:
            st.metric("Avg Multi-step Tokens", f"{avg_multi_tokens:.0f}")
            st.metric("Avg Single-step Tokens", f"{avg_single_tokens:.0f}")
        with c4:
            st.metric("Avg Inference Calls", f"{avg_inference_calls:.1f}")
            st.metric("Avg Expected Calls", f"{avg_expected_calls:.1f}")
    else:
        st.info("No evaluation results found. Run an evaluation to populate metrics.")

    # Simple tasks-by-site chart
    st.subheader("Tasks by Site")
    if tasks:
        site_counts = Counter()
        for lst in tasks.values():
            for t in lst:
                site_counts[t.get("site", "unknown")] += 1
        cols = st.columns(min(4, len(site_counts)) or 1)
        for i, (site, count) in enumerate(site_counts.items()):
            with cols[i % len(cols)]:
                st.metric(site, count)
    else:
        st.write("No tasks yet.")

    # Per-difficulty cards
    st.subheader("Per-difficulty (key metrics)")
    if diff_metrics:
        # Build compact rows with the requested fields
        rows = []
        for k, v in results.items():
            if isinstance(v, dict) and all(f in v for f in (
                "success_rate","avg_multi_step_tokens","avg_single_step_tokens","token_reduction_percent"
            )):
                try:
                    diff_label = int(k)
                except:
                    diff_label = k
                # Apply rule: show 0 if reduction is negative
                reduction = v.get("token_reduction_percent", 0.0)
                reduction_display = max(0.0, reduction)
                rows.append({
                    "Difficulty": diff_label,
                    "Success Rate": f"{v['success_rate']*100:.0f}%",
                    "Avg Single-step Tokens": f"{v['avg_single_step_tokens']:.0f}",
                    "Avg Multi-step Tokens": f"{v['avg_multi_step_tokens']:.0f}",
                    "Token Reduction": f"{reduction_display:.1f}%",
                })
        # Sort by difficulty label
        try:
            rows.sort(key=lambda r: int(r["Difficulty"]))
        except:
            pass
        # Render as a simple table
        if rows:
            st.table(rows)
        else:
            st.write("No per-difficulty metrics available.")

# Tasks tab: grouped cards
with tasks_tab:
    st.subheader("Task Pool")
    if not tasks:
        st.info("No tasks in pool yet. Use Generate in the sidebar.")
    else:
        # tasks is dict of difficulty -> list
        for diff_str, task_list in sorted(tasks.items(), key=lambda x: int(x[0])):
            st.markdown(f"### Difficulty {diff_str}")
            for t in task_list:
                with st.expander(f"{t.get('id','')} | {t.get('site','')} | {t.get('min_actions','?')} actions"):
                    st.write(t.get('description',''))
                    meta = {
                        "Validated": t.get("validated", False),
                        "Estimated replans": t.get("estimated_replans", None),
                        "Oracle tokens": t.get("oracle_tokens", None),
                    }
                    st.json(meta)
                    if t.get("expected_actions"):
                        st.write("Expected actions:")
                        st.json(t["expected_actions"])