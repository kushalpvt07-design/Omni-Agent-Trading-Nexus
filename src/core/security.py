"""
src.core.security — Input sanitization utilities.

Provides functions to clean, validate, and truncate untrusted user input
before it reaches any LLM or execution pipeline.
"""

import re


def sanitize_raw_input(raw_text: str) -> str:
    """Sanitize untrusted user input by removing control characters,
    normalizing whitespace, and enforcing a max length of 500 chars."""
    if not raw_text:
        return ""
    clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', raw_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text[:500]
