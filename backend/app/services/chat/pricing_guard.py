"""Detect and refuse pricing-related user questions before calling Claude."""

from __future__ import annotations

import re

PRICING_REFUSAL = (
    "I can't help with pricing, costs, quotes, discounts, or dollar amounts. "
    "Ask about products, compatibility, AHRI matchups, or catalog details instead—"
    "or check with your sales channel for pricing."
)

_PRICE_PATTERNS = (
    r"\bprice[sd]?\b",
    r"\bpricing\b",
    r"\bcost[s]?\b",
    r"\bquote[sd]?\b",
    r"\bquot(?:e|ing|ation)\b",
    r"\bmsrp\b",
    r"\bdiscount[s]?\b",
    r"\bcheap(?:er|est)?\b",
    r"\bexpensive\b",
    r"\baffordable\b",
    r"\bbudget\b",
    r"\binvoice\s+total\b",
    r"\bhow\s+much\b",
    r"\bwhat(?:'s|s|\s+is|\s+are)?\s+(?:the\s+)?(?:price|cost|rate)\b",
    r"\$\s*\d",
    r"\bdollar[s]?\b",
    r"\bcents?\b",
)

_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in _PRICE_PATTERNS]


def is_pricing_intent(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    return any(pattern.search(text) for pattern in _COMPILED)
