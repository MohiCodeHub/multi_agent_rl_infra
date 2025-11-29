"""Multi-step prediction agent"""

import json
from typing import List, Tuple
from src.models import Action, PageState
from src.llm_client import LLMClient


class MultiStepAgent:
    """Multi-step prediction agent"""
    
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.total_tokens = 0
        self.inference_calls = 0
    
    def reset(self):
        """Reset agent state for new episode"""
        self.total_tokens = 0
        self.inference_calls = 0
    
    def predict(
        self,
        state: PageState,
        task_description: str
    ) -> Tuple[List[Action], int]:
        """
        Predict all actions needed to complete the task from current state.
        Returns list of actions and token count for this call.
        """
        
        prompt = f"""You are a web agent completing a task.

Task: {task_description}

Current Page State:
{state.format_for_llm()}

Predict ALL actions needed to complete this task from the current state.

Available actions:
- {{"action": "click", "element": "<element name>"}}
- {{"action": "type", "element": "<element name>", "value": "<text to type>"}}
- {{"action": "clear", "element": "<element name>"}}
- {{"action": "select", "element": "<element name>", "value": "<option>"}}

Consider:
1. What sequence of actions will complete the task?
2. Are there any validation requirements to anticipate?
3. What values should be entered in form fields?

Return a JSON array of actions in order:
[
    {{"action": "type", "element": "Email", "value": "user@example.com"}},
    {{"action": "click", "element": "Submit"}}
]

Return ONLY the JSON array, no explanation."""

        response, tokens = self.llm.generate_with_tokens(prompt, temperature=0.5)
        
        self.total_tokens += tokens
        self.inference_calls += 1
        
        # Parse actions
        try:
            actions = self._parse_actions(response)
            return actions, tokens
        except Exception as e:
            print(f"Failed to parse agent actions: {e}")
            return [], tokens
    
    def _parse_actions(self, response: str) -> List[Action]:
        """Parse LLM response into action list"""
        
        text = response.strip()
        
        # Remove markdown code blocks
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
        
        # Parse JSON array
        data = json.loads(text.strip())
        
        if not isinstance(data, list):
            data = [data]
        
        actions = []
        for item in data:
            action = Action(
                action=item["action"],
                element=item["element"],
                value=item.get("value", "")
            )
            actions.append(action)
        
        return actions

