"""
base.py (LLM provider interface)

Every LLM backend (Groq, Ollama, and later OpenAI-compatible providers)
implements this exact interface. Nothing outside adapters/llm/ should
ever import groq/ollama-specific code directly — extraction, resolution,
and the agent orchestrator only ever call LLMProvider.complete() or
.complete_json().
"""

from abc import ABC, abstractmethod


class LLMProviderError(Exception):
    """Raised when the underlying LLM call fails after retries."""


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, temperature: float = 0.1, max_retries: int = 2) -> str:
        """Return raw text completion for a prompt."""
        raise NotImplementedError

    @abstractmethod
    def complete_json(self, prompt: str, temperature: float = 0.1) -> dict | list:
        """Return a parsed JSON object/list, with a self-repair retry on
        malformed output. Raises LLMProviderError if it still can't parse."""
        raise NotImplementedError
