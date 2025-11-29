"""LLM client wrapper for API calls"""

import os
from typing import Optional, Tuple
import anthropic
from src.token_counter import TokenCounter


# ============================================================
# API Configuration
# ============================================================
# Model configuration
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class LLMClient:
    """
    Wrapper for LLM API calls.
    
    This client is used throughout the system for different roles:
    - Task Generator (temp=0.7): Creative task generation
    - Oracle Validator (temp=0.3): Deterministic single-step prediction
    - Multi-Step Agent (temp=0.5): Action sequence prediction
    - Verifier (temp=0.1): Consistent success judgment
    - Site Generator (temp=0.7): Mock website HTML generation
    
    API Key Priority:
    1. --api-key command line argument
    2. ANTHROPIC_API_KEY environment variable
    3. Raises error if neither is set
    """
    
    def __init__(self, model: str = DEFAULT_MODEL, api_key: str = None):
        # Use provided key or env var (NO HARDCODED DEFAULT)
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        
        if not resolved_key:
            raise ValueError(
                "Anthropic API key required. Provide via:\n"
                "  1. --api-key command-line argument, or\n"
                "  2. ANTHROPIC_API_KEY environment variable"
            )
        
        self.client = anthropic.Anthropic(api_key=resolved_key)
        self.model = model
        self.token_counter = TokenCounter()
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> str:
        """Generate a response from the LLM"""
        
        messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        if system:
            kwargs["system"] = system
        
        if temperature != 1.0:
            kwargs["temperature"] = temperature
        
        response = self.client.messages.create(**kwargs)
        
        return response.content[0].text
    
    def generate_with_tokens(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None
    ) -> Tuple[str, int]:
        """Generate a response and return token count"""
        
        response_text = self.generate(prompt, max_tokens, temperature, system)
        
        # Count tokens
        input_tokens = self.token_counter.count(prompt)
        if system:
            input_tokens += self.token_counter.count(system)
        output_tokens = self.token_counter.count(response_text)
        
        total_tokens = input_tokens + output_tokens
        
        return response_text, total_tokens

