"""Data models for Multi-Step Web Agent Task Curriculum"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


# ============================================================
# Actions
# ============================================================

class ActionType(Enum):
    """Types of actions an agent can take"""
    CLICK = "click"
    TYPE = "type"
    CLEAR = "clear"
    SELECT = "select"
    SCROLL = "scroll"


@dataclass
class Action:
    """Single agent action"""
    action: str          # ActionType value
    element: str         # Accessible name from state
    value: str = ""      # For type, select, scroll
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "action": self.action,
            "element": self.element,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Action":
        return cls(
            action=data["action"],
            element=data["element"],
            value=data.get("value", "")
        )


# ============================================================
# Page State
# ============================================================

@dataclass
class InteractiveElement:
    """Single interactive element from accessibility tree"""
    role: str            # button, textbox, checkbox, etc.
    name: str            # Accessible name
    value: str = ""      # Current value (for inputs)
    checked: Optional[bool] = None  # For checkboxes
    disabled: bool = False
    
    def to_string(self) -> str:
        parts = [f"[{self.role}] {self.name}"]
        if self.value:
            parts.append(f'value="{self.value}"')
        if self.checked is not None:
            parts.append(f"checked={self.checked}")
        if self.disabled:
            parts.append("disabled")
        return " ".join(parts)


@dataclass
class PageState:
    """Current state of a web page"""
    url: str
    title: str
    interactive_elements: List[InteractiveElement]
    visible_text: str
    errors: List[str]
    
    def format_for_llm(self) -> str:
        """Format state for LLM consumption"""
        lines = [
            f"URL: {self.url}",
            f"Title: {self.title}",
            "",
            "Interactive Elements:"
        ]
        
        for el in self.interactive_elements:
            lines.append(f"  - {el.to_string()}")
        
        if self.errors:
            lines.append("")
            lines.append("Errors/Alerts:")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        lines.append("")
        lines.append("Visible Text (truncated):")
        lines.append(self.visible_text[:500])
        
        return "\n".join(lines)


# ============================================================
# Tasks
# ============================================================

@dataclass
class SuccessCriteria:
    """How to verify task completion"""
    description: str              # Human-readable for LLM judge
    hints: List[str] = field(default_factory=list)  # Keywords to look for


@dataclass
class Task:
    """A single task in the curriculum"""
    id: str
    site: str
    description: str
    success_criteria: SuccessCriteria
    
    # From LLM generation
    estimated_replans: int
    replan_reasoning: str
    
    # From oracle validation (set after validation)
    min_actions: Optional[int] = None
    oracle_tokens: Optional[int] = None
    validated: bool = False
    
    @property
    def expected_inference_calls(self) -> int:
        return max(1, self.estimated_replans)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "site": self.site,
            "description": self.description,
            "success_criteria": {
                "description": self.success_criteria.description,
                "hints": self.success_criteria.hints
            },
            "estimated_replans": self.estimated_replans,
            "replan_reasoning": self.replan_reasoning,
            "min_actions": self.min_actions,
            "oracle_tokens": self.oracle_tokens,
            "validated": self.validated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            site=data["site"],
            description=data["description"],
            success_criteria=SuccessCriteria(
                description=data["success_criteria"]["description"],
                hints=data["success_criteria"].get("hints", [])
            ),
            estimated_replans=data["estimated_replans"],
            replan_reasoning=data["replan_reasoning"],
            min_actions=data.get("min_actions"),
            oracle_tokens=data.get("oracle_tokens"),
            validated=data.get("validated", False)
        )


# ============================================================
# Results
# ============================================================

class EpisodeStatus(Enum):
    """Status of an episode"""
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass
class TokenUsage:
    """Token counts for an LLM call"""
    input_tokens: int
    output_tokens: int
    
    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class EpisodeResult:
    """Result of a single task attempt"""
    task_id: str
    difficulty: int
    status: EpisodeStatus
    
    # Actions
    actual_actions: int
    actual_inference_calls: int
    
    # Baseline (from oracle)
    min_actions: int
    expected_inference_calls: int
    
    # Tokens
    multi_step_tokens: int
    single_step_tokens: int  # Oracle baseline
    
    # Reward
    reward: float
    
    # Metadata
    failure_reason: Optional[str] = None
    action_history: List[Action] = field(default_factory=list)


@dataclass
class AggregatedResults:
    """Aggregated results for a difficulty level"""
    difficulty: int
    num_episodes: int
    
    # Success
    success_rate: float
    
    # Actions
    avg_actual_actions: float
    avg_min_actions: float
    
    # Inference calls
    avg_inference_calls: float
    avg_expected_calls: float
    
    # Tokens
    avg_multi_step_tokens: float
    avg_single_step_tokens: float
    token_reduction_percent: float
    
    # Reward
    avg_reward: float

