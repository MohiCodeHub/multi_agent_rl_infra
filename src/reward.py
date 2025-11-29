"""Reward calculation based on efficiency"""

import math
from dataclasses import dataclass


@dataclass
class RewardConfig:
    """Configuration for reward calculation"""
    action_weight: float = 0.6
    inference_weight: float = 0.4
    action_deviation_penalty: float = 0.15
    inference_deviation_penalty: float = 0.05


class RewardCalculator:
    """Calculate reward based on efficiency"""
    
    def __init__(self, config: RewardConfig = None):
        self.config = config or RewardConfig()
    
    def compute(
        self,
        success: bool,
        actual_actions: int,
        actual_inference_calls: int,
        min_actions: int,
        expected_inference_calls: int
    ) -> float:
        """
        Compute reward for an episode.
        
        Reward is based on:
        - Action efficiency (strict, we have ground truth)
        - Inference efficiency (lenient, this is estimated)
        
        Returns reward in range [0, 1]
        """
        
        if not success:
            return 0.0
        
        c = self.config
        
        # Action efficiency (strict)
        action_efficiency = min(1.0, min_actions / actual_actions) if actual_actions > 0 else 0.0
        extra_actions = max(0, actual_actions - min_actions)
        action_penalty = math.exp(-c.action_deviation_penalty * extra_actions)
        
        # Inference efficiency (lenient)
        inference_efficiency = min(1.0, expected_inference_calls / actual_inference_calls) if actual_inference_calls > 0 else 0.0
        extra_calls = max(0, actual_inference_calls - expected_inference_calls)
        inference_penalty = math.exp(-c.inference_deviation_penalty * extra_calls)
        
        # Weighted base score
        base = (
            c.action_weight * action_efficiency +
            c.inference_weight * inference_efficiency
        )
        
        # Apply penalties
        penalty = action_penalty * inference_penalty
        
        return base * penalty

