"""Oracle validator using single-step prediction for task validation"""

import json
from typing import Optional, Tuple
from src.models import Task, Action, PageState
from src.llm_client import LLMClient
from src.environment import WebEnvironment, ElementNotFoundError, PageTimeoutError


class OracleResult:
    """Result of oracle validation"""
    
    def __init__(
        self,
        valid: bool,
        steps_taken: int = 0,
        tokens_used: int = 0,
        reason: str = ""
    ):
        self.valid = valid
        self.steps_taken = steps_taken
        self.tokens_used = tokens_used
        self.reason = reason


class Oracle:
    """Single-step oracle agent for task validation"""
    
    def __init__(self, llm: LLMClient, base_url: str = "http://localhost:3000"):
        self.llm = llm
        self.base_url = base_url
    
    def validate(
        self,
        task: Task,
        env: WebEnvironment,
        max_steps: int = 10
    ) -> OracleResult:
        """
        Attempt to complete a task using single-step prediction.
        Returns validation result with ground truth difficulty.
        """
        
        url = f"{self.base_url}/{task.site}/"
        
        try:
            state = env.reset(url)
        except PageTimeoutError as e:
            return OracleResult(valid=False, reason=f"Page load failed: {e}")
        
        total_tokens = 0
        actions_taken = []
        
        for step in range(max_steps):
            # Oracle predicts single next action
            action, tokens = self._predict_action(state, task)
            total_tokens += tokens
            
            if action is None:
                # Oracle thinks task is complete or stuck
                break
            
            actions_taken.append(action)
            
            # Execute action
            try:
                state = env.step(action)
            except ElementNotFoundError:
                # Invalid action, oracle failed
                return OracleResult(
                    valid=False,
                    steps_taken=len(actions_taken),
                    tokens_used=total_tokens,
                    reason=f"Element not found: {action.element}"
                )
            except PageTimeoutError:
                return OracleResult(
                    valid=False,
                    steps_taken=len(actions_taken),
                    tokens_used=total_tokens,
                    reason="Page timeout during action"
                )
            
            # Check if task is complete
            if self._check_success(state, task):
                return OracleResult(
                    valid=True,
                    steps_taken=len(actions_taken),
                    tokens_used=total_tokens,
                    reason="Task completed successfully"
                )
        
        # Max steps exceeded
        return OracleResult(
            valid=False,
            steps_taken=len(actions_taken),
            tokens_used=total_tokens,
            reason=f"Max steps ({max_steps}) exceeded without completion"
        )
    
    def _predict_action(
        self,
        state: PageState,
        task: Task
    ) -> Tuple[Optional[Action], int]:
        """Predict single next action"""
        
        prompt = f"""You are a web agent completing a task.

Task: {task.description}

Current Page State:
{state.format_for_llm()}

What is the SINGLE next action to progress toward completing this task?

Available actions:
- {{"action": "click", "element": "<element name>"}}
- {{"action": "type", "element": "<element name>", "value": "<text to type>"}}
- {{"action": "clear", "element": "<element name>"}}
- {{"action": "select", "element": "<element name>", "value": "<option>"}}

If the task appears to be complete, return: {{"action": "done"}}

Return ONLY a single JSON object, no explanation."""

        response, tokens = self.llm.generate_with_tokens(prompt, temperature=0.3)
        
        # Parse action
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text.strip())
            
            if data.get("action") == "done":
                return None, tokens
            
            action = Action(
                action=data["action"],
                element=data["element"],
                value=data.get("value", "")
            )
            
            return action, tokens
            
        except Exception as e:
            print(f"Failed to parse oracle action: {e}")
            return None, tokens
    
    def _check_success(self, state: PageState, task: Task) -> bool:
        """Check if task success criteria are met"""
        
        # Only check task-specific hints — don't check generic "success" keyword
        # as it could false-positive on sites where "success" appears in other contexts
        if task.success_criteria.hints:
            text_lower = state.visible_text.lower()
            if any(hint.lower() in text_lower for hint in task.success_criteria.hints):
                return True
        
        # No obvious success indicators
        return False

