"""Task generation via LLM based on site state"""

import json
import uuid
from typing import Optional
from src.models import Task, SuccessCriteria, PageState
from src.llm_client import LLMClient
from src.environment import WebEnvironment


class TaskGenerator:
    """Generates tasks via LLM based on site state"""
    
    # Few-shot examples by difficulty level
    FEW_SHOT_EXAMPLES = {
        1: [
            {
                "site": "todo",
                "task": "Click the 'Add Todo' button",
                "actions": ["click Add Todo button"],
                "why": "Single button click = 1 action"
            },
            {
                "site": "settings",
                "task": "Toggle the Dark Mode setting on",
                "actions": ["click Dark Mode checkbox"],
                "why": "Single toggle = 1 action"
            }
        ],
        2: [
            {
                "site": "todo",
                "task": "Add a todo item with the text 'Buy milk'",
                "actions": ["type 'Buy milk' in New Todo field", "click Add Todo button"],
                "why": "Type + click = 2 actions"
            },
            {
                "site": "settings",
                "task": "Change the language to Spanish and save",
                "actions": ["select Spanish in Language dropdown", "click Save Settings"],
                "why": "Select + click = 2 actions"
            }
        ],
        3: [
            {
                "site": "signup",
                "task": "Fill in an email address, enter a password, and click Sign Up",
                "actions": ["type email in Email field", "type password in Password field", "click Sign Up button"],
                "why": "Type + type + click = 3 actions"
            },
            {
                "site": "cart",
                "task": "Add Product A to cart with quantity 2, then go to checkout",
                "actions": ["type '2' in Quantity field", "click Add to Cart", "click Checkout"],
                "why": "Type + click + click = 3 actions"
            }
        ],
        4: [
            {
                "site": "signup",
                "task": "Create an account with email, password, and password confirmation",
                "actions": ["type email", "type password", "type confirm password", "click Sign Up"],
                "why": "Type + type + type + click = 4 actions"
            },
            {
                "site": "wizard",
                "task": "Complete step 1 of the wizard by entering first and last name, then proceed",
                "actions": ["type First Name", "type Last Name", "click Next", "verify on step 2"],
                "why": "Type + type + click + verify = 4 actions"
            }
        ],
        5: [
            {
                "site": "wizard",
                "task": "Complete the first two steps of the wizard with your personal and contact info",
                "actions": ["type First Name", "type Last Name", "click Next", "type Email", "click Next"],
                "why": "5 sequential actions across wizard steps"
            },
            {
                "site": "cart",
                "task": "Add Product A and Product B to cart, apply coupon code SAVE10, then checkout",
                "actions": ["click Add to Cart (A)", "click Add to Cart (B)", "type coupon", "click Apply", "click Checkout"],
                "why": "5 actions: 2 adds + type + 2 clicks"
            }
        ]
    }
    
    def __init__(self, llm: LLMClient, base_url: str = "http://localhost:3000"):
        self.llm = llm
        self.base_url = base_url
    
    def generate(
        self,
        site: str,
        target_difficulty: int,
        env: WebEnvironment
    ) -> Optional[Task]:
        """Generate a task for a given site and difficulty"""
        
        # Get current site state
        url = f"{self.base_url}/{site}/"
        state = env.reset(url)
        
        # Generate task via LLM
        prompt = self._build_generation_prompt(site, target_difficulty, state)
        response = self.llm.generate(prompt, temperature=0.7)
        
        # Parse response
        try:
            task_data = self._parse_response(response)
        except Exception as e:
            print(f"Failed to parse task generation response: {e}")
            return None
        
        # Create task object
        task = Task(
            id=str(uuid.uuid4())[:8],
            site=site,
            description=task_data["description"],
            success_criteria=SuccessCriteria(
                description=task_data["success_criteria"],
                hints=task_data.get("success_hints", [])
            ),
            estimated_replans=task_data["estimated_replans"],
            replan_reasoning=task_data["replan_reasoning"]
        )
        
        return task
    
    def _build_generation_prompt(
        self,
        site: str,
        target_difficulty: int,
        state: PageState
    ) -> str:
        """Build the prompt for task generation"""
        
        # Get few-shot examples for this difficulty
        examples = self._get_few_shot_examples(target_difficulty)
        
        return f"""You are generating tasks for training web agents.

Website: {site}
Target Difficulty: {target_difficulty} actions (EXACTLY {target_difficulty} sequential user actions required)

{examples}

Current Page State:
{state.format_for_llm()}

Generate a task for the "{site}" website that requires EXACTLY {target_difficulty} sequential actions to complete.

CRITICAL REQUIREMENTS:
1. The task MUST require exactly {target_difficulty} distinct actions (clicks, types, selects)
2. Each action = one user interaction (one click, one field typed, one selection made)
3. Multi-step tasks should span multiple form fields or multiple buttons
4. DO NOT create tasks that can be completed in fewer actions

Consider what combination of {target_difficulty} actions makes sense:
- 2 actions: type one field + click button, OR select dropdown + click button
- 3 actions: fill 2 fields + click, OR type + select + click
- 4 actions: fill 3 fields + click, OR navigate multi-step form
- 5 actions: complete multi-step workflow, OR fill entire form

Return a JSON object with this exact structure:
{{
    "description": "Natural language description requiring exactly {target_difficulty} actions",
    "success_criteria": "How to verify the task is complete",
    "success_hints": ["keyword1", "keyword2"],
    "estimated_replans": <number 1-3>,
    "replan_reasoning": "Why replanning might be needed (or 'Simple task, no replanning expected')"
}}

Return ONLY the JSON object, no markdown or explanation."""
    
    def _get_few_shot_examples(self, target_difficulty: int) -> str:
        """Get formatted few-shot examples for the target difficulty"""
        
        examples = self.FEW_SHOT_EXAMPLES.get(target_difficulty, [])
        
        if not examples:
            # Fall back to closest difficulty
            available = sorted(self.FEW_SHOT_EXAMPLES.keys())
            closest = min(available, key=lambda x: abs(x - target_difficulty))
            examples = self.FEW_SHOT_EXAMPLES[closest]
        
        lines = [f"EXAMPLES OF {target_difficulty}-ACTION TASKS:"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"""
Example {i} ({ex['site']} site):
  Task: "{ex['task']}"
  Actions needed: {', '.join(ex['actions'])}
  Why {target_difficulty} actions: {ex['why']}""")
        
        return "\n".join(lines)
    
    def _parse_response(self, response: str) -> dict:
        """Parse LLM response into task data"""
        
        # Clean up response
        text = response.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        # Parse JSON
        data = json.loads(text.strip())
        
        # Validate required fields
        required = ["description", "success_criteria", "estimated_replans", "replan_reasoning"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        return data

