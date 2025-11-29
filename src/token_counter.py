"""Token counting utilities using tiktoken"""

import tiktoken


class TokenCounter:
    """Count tokens using tiktoken"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoder = tiktoken.get_encoding(encoding_name)
    
    def count(self, text: str) -> int:
        """Count tokens in a string"""
        return len(self.encoder.encode(text))
    
    def count_messages(self, prompt: str, response: str) -> dict:
        """Count tokens for a prompt-response pair"""
        input_tokens = self.count(prompt)
        output_tokens = self.count(response)
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }

