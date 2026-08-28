"""
base.py — Abstract retriever interface.

This abstraction means we can swap TF-IDF for a vector store later
without changing any caller in core/services/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseRetriever(ABC):
    @abstractmethod
    def retrieve(self, query: str, rules: list[dict], top_k: int = 5) -> list[tuple[dict, float]]:
        """
        Return the top_k most relevant rules for the given query,
        as (rule_dict, score) pairs sorted by score descending.
        """
        ...
