"""Unit tests for chat pricing guard and payload sanitization."""

from app.services.chat.pricing_guard import PRICING_REFUSAL, is_pricing_intent
from app.services.chat.sanitize import sanitize_for_chat


def test_pricing_intent_detects_common_phrases() -> None:
    assert is_pricing_intent("How much does this cost?")
    assert is_pricing_intent("What's the price?")
    assert is_pricing_intent("Need a quote for a 2 ton unit")
    assert is_pricing_intent("any discounts available?")
    assert not is_pricing_intent("2 ton heat pump SEER2 15 R-32")
    assert not is_pricing_intent("matchups for GSXN402410")


def test_sanitize_strips_price_fields() -> None:
    cleaned = sanitize_for_chat(
        {
            "title": "Unit",
            "price": "199.00",
            "compare_at_price": "249.00",
            "variants": [{"sku": "ABC", "price": "10", "unit_price": "10"}],
            "raw_json": "{}",
            "all_fields": {"x": "y"},
        }
    )
    assert cleaned["title"] == "Unit"
    assert "price" not in cleaned
    assert "compare_at_price" not in cleaned
    assert "raw_json" not in cleaned
    assert "all_fields" not in cleaned
    assert cleaned["variants"][0]["sku"] == "ABC"
    assert "price" not in cleaned["variants"][0]
    assert "unit_price" not in cleaned["variants"][0]
    assert "pricing" in PRICING_REFUSAL.lower()


if __name__ == "__main__":
    test_pricing_intent_detects_common_phrases()
    test_sanitize_strips_price_fields()
    print("ok")
