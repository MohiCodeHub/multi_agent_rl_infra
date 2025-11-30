"""Task curriculum management and pool sampling"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional
from src.models import Task
from src.generator import TaskGenerator
from src.oracle import Oracle, OracleResult
from src.environment import WebEnvironment
from src.llm_client import LLMClient


class TaskCurriculum:
    """Manages task pool and sampling"""
    
    def __init__(
        self,
        llm: LLMClient,
        base_url: str = "http://localhost:3000",
        cache_dir: str = "task_cache"
    ):
        self.generator = TaskGenerator(llm, base_url)
        self.oracle = Oracle(llm, base_url)
        self.base_url = base_url
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Task pool organized by difficulty
        self.pool: Dict[int, List[Task]] = {}
    
    def build_pool(
        self,
        sites: List[str],
        difficulties: List[int],
        tasks_per_difficulty: int,
        env: WebEnvironment,
        max_retries: int = 3
    ):
        """Generate and validate task pool"""
        def normalize_task(task: Task) -> tuple:
            td = task.to_dict()
            desc = td.get("description", "").strip().lower()
            site = td.get("site", "").strip().lower()
            actions = td.get("expected_actions") or []
            return (
                site,
                desc,
                tuple(
                    (a.get("action"), (a.get("element") or "").strip().lower(), a.get("value", ""))
                    for a in actions
                )
            )

        for difficulty in difficulties:
            # Don't reset if pool already has tasks for this difficulty
            if difficulty not in self.pool:
                self.pool[difficulty] = []
            
            # Build seen_keys from existing tasks to avoid duplicates
            seen_keys = {normalize_task(t) for t in self.pool[difficulty]}
            
            print(f"\nGenerating difficulty {difficulty} tasks...")
            
            attempts = 0
            max_attempts = tasks_per_difficulty * max_retries
            
            while len(self.pool[difficulty]) < tasks_per_difficulty and attempts < max_attempts:
                attempts += 1
                
                # Pick random site
                site = random.choice(sites)
                
                # Generate task, passing existing pool to avoid duplicates
                existing_for_site = [t for t in self.pool.get(difficulty, []) if t.site == site]
                task = self.generator.generate(site, difficulty, env, existing_tasks=existing_for_site)
                
                if task is None:
                    continue

                # Skip exact duplicates before spending validation time
                key = normalize_task(task)
                if key in seen_keys:
                    # Already have an identical task plan; try generating another
                    continue
                
                # Validate with oracle
                result = self.oracle.validate(
                    task, env,
                    max_steps=difficulty * 2
                )
                
                if result.valid:
                    # Check difficulty is acceptable
                    # Only accept exact match OR +1 overshoot (not undershoot)
                    # This ensures difficulty label accurately reflects minimum actions
                    if difficulty <= result.steps_taken <= difficulty + 1:
                        task.min_actions = result.steps_taken
                        task.oracle_tokens = result.tokens_used
                        task.validated = True
                        
                        self.pool[difficulty].append(task)
                        seen_keys.add(key)
                        print(f"  ✓ Task {task.id}: {result.steps_taken} steps")
                    else:
                        print(f"  ✗ Difficulty mismatch: wanted {difficulty}, got {result.steps_taken}")
                else:
                    print(f"  ✗ Validation failed: {result.reason}")
            
            print(f"  Generated {len(self.pool[difficulty])}/{tasks_per_difficulty} tasks")
    
    def sample(self, difficulty: int) -> Optional[Task]:
        """Sample a task at given difficulty"""
        
        if difficulty not in self.pool or not self.pool[difficulty]:
            return None
        
        return random.choice(self.pool[difficulty])
    
    def save(self, filename: str = "task_pool.json"):
        """Save task pool to cache"""
        def normalize_task_dict(td: Dict) -> tuple:
            desc = td.get("description", "").strip().lower()
            site = td.get("site", "").strip().lower()
            actions = td.get("expected_actions") or []
            return (
                site,
                desc,
                tuple(
                    (a.get("action"), (a.get("element") or "").strip().lower(), a.get("value", ""))
                    for a in actions
                )
            )

        seen = set()
        deduped_serializable: Dict[str, List[Dict]] = {}
        for difficulty, tasks in self.pool.items():
            unique_task_dicts: List[Dict] = []
            for task in tasks:
                td = task.to_dict()
                key = normalize_task_dict(td)
                if key in seen:
                    continue
                seen.add(key)
                unique_task_dicts.append(td)
            deduped_serializable[str(difficulty)] = unique_task_dicts

        path = self.cache_dir / filename
        path.write_text(json.dumps(deduped_serializable, indent=2))
        print(f"Saved task pool to {path}")
    
    def load(self, filename: str = "task_pool.json") -> bool:
        """Load task pool from cache"""
        
        path = self.cache_dir / filename
        
        if not path.exists():
            return False
        
        try:
            data = json.loads(path.read_text())
            
            self.pool = {}
            for difficulty_str, tasks_data in data.items():
                difficulty = int(difficulty_str)
                self.pool[difficulty] = [Task.from_dict(t) for t in tasks_data]
            
            print(f"Loaded task pool from {path}")
            return True
            
        except Exception as e:
            print(f"Failed to load task pool: {e}")
            return False
    
    def stats(self) -> Dict:
        """Get pool statistics"""
        
        return {
            difficulty: {
                "count": len(tasks),
                "avg_min_actions": sum(t.min_actions for t in tasks) / len(tasks) if tasks else 0,
                "avg_expected_calls": sum(t.expected_inference_calls for t in tasks) / len(tasks) if tasks else 0
            }
            for difficulty, tasks in self.pool.items()
        }

