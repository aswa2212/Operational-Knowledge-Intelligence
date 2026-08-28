"""
groq_provider.py

Groq (hosted, free-tier) implementation of LLMProvider. This is the
primary provider for interactive use (fast inference).
"""

import json
import os

import httpx
from dotenv import load_dotenv
from pathlib import Path

_ENV_PATH = Path(__file__).parent.parent.parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
load_dotenv()

from app.adapters.llm.base import LLMProvider, LLMProviderError


class GroqProvider(LLMProvider):
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        if not self.api_key:
            raise LLMProviderError("GROQ_API_KEY is not set in .env")

    def complete(self, prompt: str, temperature: float = 0.1, max_retries: int = 4) -> str:
        import time
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(self.base_url, headers=headers, json=payload)
                    if response.status_code == 429:
                        retry_after = 2.0
                        try:
                            retry_after = float(response.headers.get("retry-after", 2.0))
                        except Exception:
                            pass
                        time.sleep(max(retry_after, float(2 ** attempt + 2)))
                        last_error = httpx.HTTPStatusError("429 Too Many Requests", request=response.request, response=response)
                        continue
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:  # noqa: BLE001
                last_error = e
                if attempt < max_retries:
                    time.sleep(2 ** attempt + 1)
        raise LLMProviderError(f"Groq call failed after retries: {last_error}")

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
                raise LLMProviderError(f"Could not parse Groq response as JSON: {e}\nRaw: {raw}") from e
