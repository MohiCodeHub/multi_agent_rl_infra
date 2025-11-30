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
            {"actions": [{"action": "type", "element": "Password", "value": "pass"},
                        {"action": "click", "element": "Sign Up"}],
             "task": "Enter a short password 'pass' and click Sign Up (will show password length error)",
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
        5: [
            {"actions": [{"action": "type", "element": "Email", "value": "user@example.com"},
                        {"action": "type", "element": "Password", "value": "securepass"},
                        {"action": "type", "element": "Confirm Password", "value": "wrongpass"},
                        {"action": "click", "element": "Sign Up"},
                        {"action": "type", "element": "Confirm Password", "value": "securepass"}],
             "task": "Enter email 'user@example.com', password 'securepass', wrong confirm password, click Sign Up to see error, then fix confirm password",
             "success_hints": ["Password and Confirm Password must match", "securepass"]},
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
            {"actions": [{"action": "click", "element": "Email Alerts"}],
             "task": "Toggle Email Alerts on (no save)",
             "success_hints": []},
        ],
        2: [
            {"actions": [{"action": "click", "element": "Dark Mode"},
                        {"action": "click", "element": "Save"}],
             "task": "Enable Dark Mode and click Save",
             "success_hints": ["Settings saved successfully"]},
        ],
        3: [
            {"actions": [{"action": "click", "element": "SMS Alerts"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "click", "element": "Save"}],
             "task": "Enable SMS Alerts and Dark Mode, then click Save",
             "success_hints": ["Settings saved successfully"]},
        ],
        4: [
            {"actions": [{"action": "click", "element": "SMS Alerts"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "select", "element": "Language", "value": "Spanish"},
                        {"action": "click", "element": "Save"}],
             "task": "Enable SMS Alerts, Dark Mode, change language to Spanish, and click Save",
             "success_hints": ["Settings saved successfully"]},
        ],
        5: [
            {"actions": [{"action": "click", "element": "Email Alerts"},
                        {"action": "click", "element": "SMS Alerts"},
                        {"action": "click", "element": "Dark Mode"},
                        {"action": "select", "element": "Language", "value": "English"},
                        {"action": "click", "element": "Save"}],
             "task": "Toggle Email Alerts, enable SMS Alerts and Dark Mode, set language to English, then Save",
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
        use_templates: bool = True,
        existing_tasks: List[Task] = None
    ) -> Optional[Task]:
        """Generate a task for a given site and difficulty.
        
        Args:
            site: The site to generate a task for
            target_difficulty: The target number of actions
            env: The web environment
            use_templates: If True, use predefined templates for guaranteed action counts.
                          If False or no template available, fall back to LLM generation.
            existing_tasks: List of already-generated tasks to avoid duplicates
        
        Returns:
            A Task object or None if generation failed
        """
        
        # Try template-based generation first (guarantees exact action count)
        if use_templates:
            task = self._generate_from_template(site, target_difficulty, existing_tasks or [])
            if task is not None:
                return task
            
            # Try chaining multiple templates to reach target difficulty
            # This reduces LLM inference calls by reusing existing templates
            chained_task = self._generate_by_chaining(site, target_difficulty, existing_tasks or [])
            if chained_task is not None:
                return chained_task
        
        # Fall back to LLM-based generation
        return self._generate_from_llm(site, target_difficulty, env, existing_tasks or [])
    
    def _generate_from_template(
        self,
        site: str,
        target_difficulty: int,
        existing_tasks: List[Task]
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
        
        # Collect descriptions of existing tasks to avoid repeats
        existing_descriptions = set()
        for t in existing_tasks:
            if t.site == site:
                existing_descriptions.add(t.description.strip().lower())
        
        # Filter out templates that match existing tasks
        templates = site_templates[target_difficulty]
        available_templates = [
            tmpl for tmpl in templates
            if tmpl["task"].strip().lower() not in existing_descriptions
        ]
        
        # If all templates used, return None to signal no new tasks available
        if not available_templates:
            return None
        
        # Pick a random template for variety
        template = random.choice(available_templates)
        
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
    
    def _generate_by_chaining(
        self,
        site: str,
        target_difficulty: int,
        existing_tasks: List[Task]
    ) -> Optional[Task]:
        """Generate a task by chaining multiple templates together.
        
        This reduces LLM inference calls by combining existing templates
        to reach higher difficulty levels. For example, a difficulty 7 task
        can be created by chaining a difficulty 4 template with a difficulty 3 template.
        
        KEY INSIGHT: Chained tasks require 0 additional LLM calls for generation
        since they're built from known templates. The oracle still validates them,
        but the expected_inference_calls is pre-computed from the template actions.
        
        Args:
            site: The site to generate a task for
            target_difficulty: The target number of actions
            existing_tasks: List of already-generated tasks to avoid duplicates
            
        Returns:
            A chained Task object or None if no valid combination found
        """
        import random
        
        # Chaining works for all sites that have templates
        if site not in SITE_ACTION_TEMPLATES:
            return None
        
        site_templates = SITE_ACTION_TEMPLATES[site]
        
        # Get available template difficulties
        available_difficulties = sorted(site_templates.keys(), reverse=True)
        
        # Find ALL valid combinations that sum to target_difficulty
        # This is more robust than greedy approach
        valid_combinations = self._find_template_combinations(
            site_templates, target_difficulty, max_templates=3
        )
        
        if not valid_combinations:
            return None
        
        # Shuffle combinations to get variety
        random.shuffle(valid_combinations)
        
        # Try each combination until we find one not already used
        existing_descriptions = {t.description.strip().lower() for t in existing_tasks if t.site == site}
        
        for combination in valid_combinations:
            # Build the chained task from this combination
            combined_actions = []
            combined_hints = []
            descriptions = []
            template_ids = []
            
            for diff, template in combination:
                combined_actions.extend(template["actions"])
                combined_hints.extend(template.get("success_hints", []))
                descriptions.append(template["task"])
                template_ids.append(f"{site}-d{diff}")
            
            # Create a natural chained description
            chained_description = self._build_chained_description(descriptions)
            
            # Skip if already exists
            if chained_description.strip().lower() in existing_descriptions:
                continue
            
            # Deduplicate hints, keeping final state hints (last 3-4)
            seen_hints = set()
            unique_hints = []
            for hint in combined_hints:
                if hint not in seen_hints:
                    seen_hints.add(hint)
                    unique_hints.append(hint)
            
            # For chained tasks, prefer final state hints
            if len(unique_hints) > 4:
                unique_hints = unique_hints[-4:]
            
            task = Task(
                id=str(uuid.uuid4())[:8],
                site=site,
                description=chained_description,
                success_criteria=SuccessCriteria(
                    description=f"Complete {len(combination)} subtasks in sequence ({target_difficulty} total actions)",
                    hints=unique_hints
                ),
                estimated_replans=len(combination),  # One replan per subtask boundary
                replan_reasoning=f"Chained from {len(combination)} templates: {' + '.join(f'd{d}' for d, _ in combination)}",
                is_chained=True,
                chained_from=template_ids
            )
            
            # Store the expected actions for validation
            task.expected_actions = combined_actions
            
            return task
        
        return None
    
    def _find_template_combinations(
        self,
        site_templates: Dict[int, List[Dict]],
        target: int,
        max_templates: int = 3
    ) -> List[List[tuple]]:
        """Find all valid combinations of templates that sum to target difficulty.
        
        Args:
            site_templates: Dict of difficulty -> list of templates
            target: Target total actions
            max_templates: Maximum number of templates to chain
            
        Returns:
            List of valid combinations, where each combination is a list of (difficulty, template) tuples
        """
        import random
        
        available_difficulties = sorted(site_templates.keys())
        combinations = []
        
        def find_combos(remaining: int, current: List[tuple], start_diff: int, depth: int):
            if remaining == 0 and len(current) >= 2:
                combinations.append(list(current))
                return
            if remaining < 0 or depth >= max_templates:
                return
            
            for diff in available_difficulties:
                if diff > remaining:
                    continue
                templates = site_templates[diff]
                # Pick a random template for this difficulty
                template = random.choice(templates)
                current.append((diff, template))
                find_combos(remaining - diff, current, diff, depth + 1)
                current.pop()
        
        find_combos(target, [], min(available_difficulties), 0)
        return combinations
    
    def _build_chained_description(self, descriptions: List[str]) -> str:
        """Build a natural language description for a chained task."""
        if len(descriptions) == 2:
            return f"First, {descriptions[0].lower()}. Then, {descriptions[1].lower()}."
        
        parts = []
        for i, desc in enumerate(descriptions):
            desc_lower = desc.lower()
            # Remove leading articles/words that don't fit in sequence
            if desc_lower.startswith("click the "):
                desc_lower = "click the " + desc_lower[10:]
            
            if i == 0:
                parts.append(f"First, {desc_lower}")
            elif i == len(descriptions) - 1:
                parts.append(f"Finally, {desc_lower}")
            else:
                parts.append(f"Then, {desc_lower}")
        
        return ". ".join(parts) + "."
    
    def _generate_from_llm(
        self,
        site: str,
        target_difficulty: int,
        env: WebEnvironment,
        existing_tasks: List[Task]
    ) -> Optional[Task]:
        """Generate a task using LLM (fallback when no template available)."""
        
        # Get current site state
        url = f"{self.base_url}/{site}/"
        state = env.reset(url)
        
        # Generate task via LLM, passing existing tasks to avoid duplicates
        prompt = self._build_generation_prompt(site, target_difficulty, state, existing_tasks)
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
        state: PageState,
        existing_tasks: List[Task] = None
    ) -> str:
        """Build the prompt for task generation"""
        
        # Get few-shot examples for this difficulty
        examples = self._get_few_shot_examples(target_difficulty)
        
        # Build list of existing task descriptions to avoid
        avoid_list = ""
        if existing_tasks:
            task_descriptions = [f'  - "{t.description}"' for t in existing_tasks]
            if task_descriptions:
                avoid_list = f"""\nDO NOT generate any of these existing tasks:
{chr(10).join(task_descriptions)}

Generate a DIFFERENT task that requires {target_difficulty} actions.
"""
        
        return f"""You are generating tasks for training web agents.

Website: {site}
Target Difficulty: {target_difficulty} actions (EXACTLY {target_difficulty} sequential user actions required){avoid_list}

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

