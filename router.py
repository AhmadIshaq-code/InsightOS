"""
InsightOS Router Layer.
Delegates to ReasoningBrain as the single unified orchestration layer.
"""

from typing import Optional
from reasoning_brain import ReasoningBrain

_BRAIN = ReasoningBrain()

def classify_query(query: str, api_key: Optional[str] = None) -> str:
    """Classifies user query into DATA, DOCS, HYBRID, or GENERAL using ReasoningBrain."""
    res = _BRAIN.classify_intent(query, api_key=api_key)
    return res.get("intent", "GENERAL")

def main_chat_interface(
    query: str,
    api_key: Optional[str] = None,
    dataset_id: Optional[str] = None,
    document_id: Optional[str] = None
) -> dict:
    """
    Main orchestration router returning a structured dictionary for the Web UI.
    Delegates to ReasoningBrain for deterministic data facts and grounded knowledge retrieval.
    """
    return _BRAIN.process_question(
        question=query,
        dataset_id=dataset_id,
        document_id=document_id,
        api_key=api_key
    )

