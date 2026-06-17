import re
import logging

logger = logging.getLogger("pulse-quote-validator")

def _normalize_for_matching(text: str) -> str:
    """Normalizes whitespace and punctuation for robust matching."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return " ".join(text.split())

def validate_quotes(quotes: list[str], cluster_reviews: list[dict], full_corpus: list[dict]) -> list[str]:
    """
    Verifies that each quote is an exact (or punctuation/whitespace-normalized)
    substring of at least one review in the cluster (or full corpus fallback).
    """
    valid_quotes = []
    
    cluster_normalized = [_normalize_for_matching(r.get("content", "")) for r in cluster_reviews]
    full_normalized = [_normalize_for_matching(r.get("content", "")) for r in full_corpus]
    
    for quote in quotes:
        quote = quote.strip()
        if not quote:
            continue
            
        # Handle ellipsis truncation
        parts = [p.strip() for p in re.split(r'\.\.\.|\u2026', quote) if p.strip()]
        if not parts:
            continue
            
        all_parts_matched = True
        for part in parts:
            normalized_part = _normalize_for_matching(part)
            if len(normalized_part) < 4:
                continue
                
            matched_in_cluster = any(normalized_part in r_text for r_text in cluster_normalized)
            if matched_in_cluster:
                continue
                
            matched_in_corpus = any(normalized_part in r_text for r_text in full_normalized)
            if not matched_in_corpus:
                logger.warning(f"Quote validation failed for: '{part}' (from quote: '{quote}')")
                all_parts_matched = False
                break
                
        if all_parts_matched:
            valid_quotes.append(quote)
            
    return valid_quotes
