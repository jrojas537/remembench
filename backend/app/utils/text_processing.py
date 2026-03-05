"""
Remembench — Text Processing Utilities

Helpers for semantic sequence matching and string structuring.
"""

from difflib import SequenceMatcher
from app.schemas import ImpactEventCreate

def deduplicate_semantically(
    events: list[ImpactEventCreate], 
    similarity_threshold: float = 0.85
) -> list[ImpactEventCreate]:
    """
    Performs global semantic deduplication across unstructured event sources.
    Uses difflib.SequenceMatcher ratio to check for text collisions.
    """
    unique_events = []
    seen_texts = []
    
    for ev in events:
        text_to_analyze = ev.raw_payload.get("content", ev.description) if ev.raw_payload else ev.description
        if not text_to_analyze:
            unique_events.append(ev)
            continue
            
        is_duplicate = False
        for seen in seen_texts:
            similarity = SequenceMatcher(None, text_to_analyze, seen).ratio()
            if similarity > similarity_threshold:
                is_duplicate = True
                break
                
        if not is_duplicate:
            seen_texts.append(text_to_analyze)
            unique_events.append(ev)
            
    return unique_events
