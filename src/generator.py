"""Task generation via LLM based on site state"""

import json
import uuid
from typing import Optional, List, Dict, Any
from src.models import Task, SuccessCriteria, PageState
from src.llm_client import LLMClient
from src.environment import WebEnvironment


# Site-specific action templates that guarantee exact action counts
# Each template specifies exactly which elements to interact with
SITE_ACTION_TEMPLATES: Dict[str, Dict[int, List[Dict[str, Any]]]] = {
    "signup": {
        1: [
            {"actions": [{"action": "click", "element": "Sign Up"}], 
             "task": "Click the Sign Up button to trigger validation (will show email required error)",
             "success_hints": ["Email must contain"]},
        ],
        2: [
            {"actions": [{"action": "type", "element": "Email", "value": "test@example.com"},
                        {"action": "click", "element": "Sign Up"}],
             "task": "Enter email 'test@example.com' and click Sign Up (will show password required)",
             "success_hints": ["Password must be at least"]},
        ],
        3: [
            {"actions": [{"action": "type", "element": "Email", "value": "test@example.com"},
                        {"action": "type", "element": "Password", "value": "password123"},
                        {"action": "click", "element": "Sign Up"}],
             "task": "Fill in email 'test@example.com' and password 'password123', then click Sign Up (will show confirm password error)",
             "success_hints": ["Password and Confirm Password must match"]},
        ],
        4: [
            {"actions": [{"action": "type", "element": "Email", "value": "test@example.com"},
                        {"action": "type", "element": "Password", "value": "password123"},
                        {"action": "type", "element": "Confirm Password", "value": "password123"},
                        {"action": "click", "element": "Sign Up"}],
             "task": "Create an account with email 'test@example.com', password 'password123', confirm password, and click Sign Up",
             "success_hints": ["Account created successfully"]},
        ],
    },
    "todo": {
        1: [
            {"actions": [{"action": "click", "element": "Add Todo"}],
             "task": "Click the Add Todo button (it will show an error for empty input)",
             "success_hints": ["empty", "error", "cannot"]},
        ],
        2: [
            {"actions": [{"action": "type", "element": "New Todo", "value": "Buy groceries"},
                        {"action": "click", "element": "Add Todo"}],
             "task": "Add a new todo item with the text 'Buy groceries'",
             "success_hints": ["Buy groceries", "todo", "Total"]},
        ],
        3: [
            {"actions": [{"action": "type", "element": "New Todo", "value": "First task"},
                        {"action": "click", "element": "Add Todo"},
                        {"action": "click", "element": "Complete"}],
             "task": "Add a todo item called 'First task' and then mark it as complete",
             "success_hints": ["Completed", "1", "First task"]},
        ],
        4: [
            {"actions": [{"action": "type", "element": "New Todo", "value": "Task one"},
                        {"action": "click", "element": "Add Todo"},
                        {"action": "type", "element": "New Todo", "value": "Task two"},
                        {"action": "click", "element": "Add Todo"}],
             "task": "Add two todo items: 'Task one' and 'Task two'",
             "success_hints": ["Task one", "Task two", "Total: 2"]},
        ],
        5: [
            {"actions": [{"action": "type", "element": "New Todo", "value": "Important task"},
                        {"action": "click", "element": "Add Todo"},
                        {"action": "click", "element": "Complete"},
                        {"action": "type", "element": "New Todo", "value": "Another task"},
                        {"action": "click", "element": "Add Todo"}],
             "task": "Add 'Important task', mark it complete, then add 'Another task'",
             "success_hints": ["Important task", "Another task", "Completed: 1"]},
        ],
    },
    "cart": {
        1: [
            {"actions": [{"action": "click", "element": "Checkout"}],
             "task": "Click the Checkout button (cart is empty, will show error)",
             "success_hints": ["empty", "error", "must not"]},
        ],
        2: [
            {"actions": [{"action": "click", "element": "Add to Cart Product A"},
                        {"action": "click", "element": "Checkout"}],
             "task": "Add Product A to cart and proceed to checkout",
             "success_hints": ["confirmed", "Order", "thank"]},
        ],
        3: [
            {"actions": [{"action": "click", "element": "Add to Cart Product A"},
                        {"action": "click", "element": "Add to Cart Product B"},
                        {"action": "click", "element": "Checkout"}],
             "task": "Add Product A and Product B to cart, then checkout",
             "success_hints": ["confirmed", "Order", "thank"]},
        ],
        4: [
            {"actions": [{"action": "click", "element": "Add to Cart Product A"},
                        {"action": "type", "element": "Coupon Code", "value": "SAVE10"},
                        {"action": "click", "element": "Apply Coupon"},
                        {"action": "click", "element": "Checkout"}],
             "task": "Add Product A to cart, apply coupon code SAVE10, then checkout",
             "success_hints": ["confirmed", "discount", "10%"]},
        ],
        5: [
            {"actions": [{"action": "click", "element": "Add to Cart Product A"},
                        {"action": "click", "element": "Add to Cart Product B"},
                        {"action": "type", "element": "Coupon Code", "value": "SAVE10"},
                        {"action": "click", "element": "Apply Coupon"},
                        {"action": "click", "element": "Checkout"}],
             "task": "Add Product A and Product B to cart, apply coupon SAVE10, then checkout",
             "success_hints": ["confirmed", "discount", "Order"]},
        ],
    },
    "settings": {
        1: [
            {"actions": [{"action": "click", "element": "Dark Mode"}],
             "task": "Toggle the Dark Mode setting on (just click the toggle, don't save)",
             "success_hints": []},
        ],
        2: [
            {"actions": [{"action": "click", "element": "Dark Mode"},
                        {"action": "click", "element": "Save Settings"}],
             "task": "Enable Dark Mode and save the settings",
             "success_hints": ["Settings saved successfully"]},
        ],
        3: [
            {"actions": [{"action": "click", "element": "SMS Notifications"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "click", "element": "Save Settings"}],
             "task": "Enable SMS Notifications and Dark Mode, then click Save Settings",
             "success_hints": ["Settings saved successfully"]},
        ],
        4: [
            {"actions": [{"action": "click", "element": "SMS Notifications"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "select", "element": "Language", "value": "Spanish"},
                        {"action": "click", "element": "Save Settings"}],
             "task": "Enable SMS Notifications, Dark Mode, change language to Spanish, and click Save Settings",
             "success_hints": ["Settings saved successfully"]},
        ],
        5: [
            {"actions": [{"action": "click", "element": "Email Notifications"},
                        {"action": "click", "element": "SMS Notifications"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "select", "element": "Language", "value": "French"},
                        {"action": "click", "element": "Save Settings"}],
             "task": "Toggle Email Notifications off, enable SMS and Dark Mode, change language to French, and click Save Settings",
             "success_hints": ["Settings saved successfully"]},
        ],
    },
    "wizard": {
        1: [
            {"actions": [{"action": "click", "element": "Next"}],
             "task": "Click the Next button (will show validation errors)",
             "success_hints": ["required", "error", "First name"]},
        ],
        2: [
            {"actions": [{"action": "type", "element": "First Name", "value": "John"},
                        {"action": "click", "element": "Next"}],
             "task": "Enter first name 'John' and click Next (will show last name required)",
             "success_hints": ["required", "Last name", "error"]},
        ],
        3: [
            {"actions": [{"action": "type", "element": "First Name", "value": "John"},
                        {"action": "type", "element": "Last Name", "value": "Doe"},
                        {"action": "click", "element": "Next"}],
             "task": "Complete step 1 by entering first name 'John' and last name 'Doe', then proceed to step 2",
             "success_hints": ["Contact", "Email", "Step 2"]},
        ],
        4: [
            {"actions": [{"action": "type", "element": "First Name", "value": "John"},
                        {"action": "type", "element": "Last Name", "value": "Doe"},
                        {"action": "click", "element": "Next"},
                        {"action": "type", "element": "Email", "value": "john@example.com"}],
             "task": "Complete step 1 with name 'John Doe', go to step 2, and enter email",
             "success_hints": ["john@example.com", "Contact", "Phone"]},
        ],
        5: [
            {"actions": [{"action": "type", "element": "First Name", "value": "John"},
                        {"action": "type", "element": "Last Name", "value": "Doe"},
                        {"action": "click", "element": "Next"},
                        {"action": "type", "element": "Email", "value": "john@example.com"},
                        {"action": "click", "element": "Next"}],
             "task": "Complete steps 1 and 2 of the wizard with name 'John Doe' and email 'john@example.com'",
             "success_hints": ["Review", "John", "Doe", "john@example.com"]},
        ],
        6: [
            {"actions": [{"action": "type", "element": "First Name", "value": "John"},
                        {"action": "type", "element": "Last Name", "value": "Doe"},
                        {"action": "click", "element": "Next"},
                        {"action": "type", "element": "Email", "value": "john@example.com"},
                        {"action": "click", "element": "Next"},
                        {"action": "click", "element": "Submit"}],
             "task": "Complete the entire wizard: enter name 'John Doe', email 'john@example.com', and submit",
             "success_hints": ["success", "submitted", "thank"]},
        ],
    },
}


class TaskGenerator:
    """Generates tasks via LLM based on site state"""
    
    # Few-shot examples by difficulty level (kept for LLM-based generation fallback)
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
        env: WebEnvironment,
        use_templates: bool = True
    ) -> Optional[Task]:
        """Generate a task for a given site and difficulty.
        
        Args:
            site: The site to generate a task for
            target_difficulty: The target number of actions
            env: The web environment
            use_templates: If True, use predefined templates for guaranteed action counts.
                          If False or no template available, fall back to LLM generation.
        
        Returns:
            A Task object or None if generation failed
        """
        
        # Try template-based generation first (guarantees exact action count)
        if use_templates:
            task = self._generate_from_template(site, target_difficulty)
            if task is not None:
                return task
        
        # Fall back to LLM-based generation
        return self._generate_from_llm(site, target_difficulty, env)
    
    def _generate_from_template(
        self,
        site: str,
        target_difficulty: int
    ) -> Optional[Task]:
        """Generate a task from predefined templates.
        
        Templates guarantee exact action counts because they specify
        the exact sequence of actions required.
        """
        import random
        
        # Check if we have templates for this site and difficulty
        if site not in SITE_ACTION_TEMPLATES:
            return None
        
        site_templates = SITE_ACTION_TEMPLATES[site]
        if target_difficulty not in site_templates:
            return None
        
        # Pick a random template for variety
        templates = site_templates[target_difficulty]
        template = random.choice(templates)
        
        # Create task from template
        task = Task(
            id=str(uuid.uuid4())[:8],
            site=site,
            description=template["task"],
            success_criteria=SuccessCriteria(
                description=f"Task requires exactly {target_difficulty} actions: {template['task']}",
                hints=template.get("success_hints", [])
            ),
            estimated_replans=1 if target_difficulty <= 2 else 2,
            replan_reasoning=f"Template-based task with {target_difficulty} predefined actions"
        )
        
        # Store the expected actions for validation
        task.expected_actions = template["actions"]
        
        return task
    
    def _generate_from_llm(
        self,
        site: str,
        target_difficulty: int,
        env: WebEnvironment
    ) -> Optional[Task]:
        """Generate a task using LLM (fallback when no template available)."""
        
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

