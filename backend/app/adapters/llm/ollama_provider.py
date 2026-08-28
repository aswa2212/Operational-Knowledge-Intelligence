"""
ollama_provider.py

Local Ollama implementation of LLMProvider — zero-cost, no rate limit,
used as the fallback/bulk-extraction provider (see Risk 7 in the master
report: rate-limit mitigation).
"""

import json
import os

import httpx

from app.adapters.llm.base import LLMProvider, LLMProviderError


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "llama3")

    def complete(self, prompt: str, temperature: float = 0.1, max_retries: int = 2) -> str:
        last_error = None
        for _ in range(max_retries + 1):
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                }
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(f"{self.host}/api/generate", json=payload)
                    response.raise_for_status()
                    return response.json()["response"]
            except Exception as e:  # noqa: BLE001
                last_error = e
        raise LLMProviderError(f"Ollama call failed after retries: {last_error}")

    def complete_json(self, prompt: str, temperature: float = 0.1) -> dict | list:
        strict_prompt = prompt + "\n\nRespond with ONLY valid JSON. No preamble, no markdown fences."
        raw = self.complete(strict_prompt, temperature=temperature)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            repair_prompt = f"This was supposed to be valid JSON but failed to parse:\n{cleaned}\n\nReturn ONLY the corrected JSON."
            repaired = self.complete(repair_prompt, temperature=0.0)
            repaired_cleaned = repaired.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            try:
                return json.loads(repaired_cleaned)
            except json.JSONDecodeError as e:
                raise LLMProviderError(f"Could not parse Ollama response as JSON: {e}\nRaw: {raw}") from e


def get_llm_provider() -> LLMProvider:
    """
    Factory function — the ONLY place that decides Groq vs Ollama.
    Every caller elsewhere in the codebase should call this instead of
    importing GroqProvider/OllamaProvider directly, so swapping the
    default provider is a one-line change here, not a find-and-replace.
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "groq":
        from app.adapters.llm.groq_provider import GroqProvider
        return GroqProvider()
    elif provider == "ollama":
        return OllamaProvider()
    else:
        raise LLMProviderError(f"Unknown LLM_PROVIDER: {provider}")
