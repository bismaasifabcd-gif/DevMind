from __future__ import annotations

from typing import Any


class Evaluation:
    """Ragas-like evaluation interface for answer quality checks."""

    def __init__(self, dataset: list[dict[str, Any]] | None = None):
        self.dataset = dataset or []

    def evaluate(self, answer: str, context: list[str] | None = None) -> dict[str, Any]:
        context = context or []
        score = 1.0 if answer and context else 0.0
        return {
            "score": score,
            "grounded": bool(answer and context),
            "details": {"context_items": len(context)},
        }
