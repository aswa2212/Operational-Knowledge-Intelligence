"""
tfidf_retriever.py

scikit-learn TF-IDF cosine retriever. Implements BaseRetriever.
Used by decide_case.py for fuzzy rule matching when deterministic
condition evaluation fails to find a match.
"""

from __future__ import annotations

from app.adapters.retrieval.base import BaseRetriever


class TFIDFRetriever(BaseRetriever):
    def retrieve(self, query: str, rules: list[dict], top_k: int = 5) -> list[tuple[dict, float]]:
        """
        Return top_k (rule, score) pairs sorted by cosine similarity descending.
        Falls back gracefully if sklearn is unavailable or rules is empty.
        """
        if not rules:
            return []

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            # Degrade to returning all rules with score 0.5
            return [(r, 0.5) for r in rules[:top_k]]

        corpus = [
            f"{r.get('trigger_text', '')} {r.get('action', '')} {r.get('conditions_json', '')}"
            for r in rules
        ]

        try:
            vec = TfidfVectorizer(ngram_range=(1, 2), max_features=8000, sublinear_tf=True)
            matrix = vec.fit_transform(corpus + [query])
            scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
            ranked = sorted(
                zip(rules, scores.tolist()), key=lambda x: x[1], reverse=True
            )
            return [(r, float(s)) for r, s in ranked[:top_k] if s > 0.01]
        except Exception:
            return [(r, 0.5) for r in rules[:top_k]]
