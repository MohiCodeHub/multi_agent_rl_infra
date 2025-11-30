from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import subprocess
import json

TASK_POOL_PATH = Path("task_cache/task_pool.json")
RESULTS_DIR = Path("results")
BUILD_SCRIPT = Path("scripts/build_pool.py")

app = FastAPI(title="Multi-Agent RL API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    tasks_per_difficulty: int = 2
    max_retries: int = 3

@app.get("/api/tasks")
def get_tasks():
    if not TASK_POOL_PATH.exists():
        return {}
    return json.loads(TASK_POOL_PATH.read_text())

@app.get("/api/results")
def list_results():
    files = sorted(RESULTS_DIR.glob("evaluation_*.json"))
    return [f.name for f in files]

@app.get("/api/results/{filename}")
def get_result(filename: str):
    path = RESULTS_DIR / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text())

@app.post("/api/generate")
def generate(req: GenerateRequest):
    cmd = [
        "python", str(BUILD_SCRIPT),
        "--tasks-per-difficulty", str(req.tasks_per_difficulty),
        "--max-retries", str(req.max_retries),
        "--output", TASK_POOL_PATH.name,
    ]
    subprocess.run(cmd, cwd=str(BUILD_SCRIPT.parent), check=True)
    return {"status": "ok"}

# Run with: uvicorn src.api.main:app --reload --port 8000
