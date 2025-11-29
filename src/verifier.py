"""LLM-based task completion verifier"""

import json
from src.models import Task, PageState
from src.llm_client import LLMClient


class Verifier:
    """LLM-based task completion verifier"""
    
    def __init__(self, llm: LLMClient):
        self.llm = llm
    
    def verify(self, task: Task, state: PageState) -> bool:
        """Check if task was completed successfully"""
        
        # Fast path: check hints first (success takes priority)
        # Don't fast-fail on errors — the agent might have recovered from
        # an error in a previous step, and the final state could show both
        # old errors and success indicators.
        if task.success_criteria.hints:
            text_lower = state.visible_text.lower()
            for hint in task.success_criteria.hints:
                if hint.lower() in text_lower:
                    return True
        
        # LLM judgment (errors are passed to LLM as context, not as auto-fail)
        return self._llm_judge(task, state)
    
    def _llm_judge(self, task: Task, state: PageState) -> bool:
        """Use LLM to judge task completion"""
        
        prompt = f"""You are judging whether a web agent successfully completed a task.

Task: {task.description}

Success Criteria: {task.success_criteria.description}

Final Page State:
URL: {state.url}
Title: {state.title}

Visible Text:
{state.visible_text[:1000]}

Errors on Page: {state.errors if state.errors else "None"}

Was the task completed successfully?

Return JSON:
{{"success": true/false, "reason": "brief explanation"}}

Return ONLY the JSON object."""

        response = self.llm.generate(prompt, temperature=0.1)
        
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            
            data = json.loads(text.strip())
            return data.get("success", False)
            
        except Exception as e:
            print(f"Verifier parse error: {e}")
            return False

