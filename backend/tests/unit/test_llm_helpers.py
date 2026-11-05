"""JSON extraction, final text, costs."""

import pytest

from app.llm import anthropic_client
from app.llm.cost_tracker import compute_cost_usd, prices_for, usage_of
from app.llm.messages import extract_json, final_text
from tests.fake_llm import message


def test_extract_json_fenced_braces_and_wrapper():
    assert extract_json('blabla ```json\n{"a": 1}\n``` fin') == {"a": 1}
    assert extract_json('voilà {"a": {"b": 2}} merci') == {"a": {"b": 2}}
    assert extract_json('```json\n{"exercises": [{"x": 1}]}\n```') == {"x": 1}
    with pytest.raises(ValueError):
        extract_json("rien")
    with pytest.raises(ValueError):
        extract_json('```json\n{"a": }\n```')


def test_final_text_skips_search_blocks():
    msg = message('{"a": 1}', searches=1)
    assert final_text(msg) == '{"a": 1}'


def test_prices_longest_prefix_and_unknown():
    assert prices_for("claude-sonnet-5-5") == (2.0, 10.0)
    assert prices_for("claude-sonnet-4-5-20250929") == (3.0, 15.0)
    assert prices_for("mystery") == (5.0, 25.0)


def test_cost_with_cache_batch_and_search():
    full = compute_cost_usd("claude-sonnet-4-5", input_tokens=1_000_000, output_tokens=0)
    assert full == pytest.approx(3.0)
    cached = compute_cost_usd(
        "claude-sonnet-4-5", input_tokens=0, output_tokens=0, cache_read_tokens=1_000_000
    )
    assert cached == pytest.approx(0.3)
    batch = compute_cost_usd(
        "claude-sonnet-4-5", input_tokens=0, output_tokens=1_000_000, web_searches=2, batch=True
    )
    assert batch == pytest.approx(7.5 + 0.02)  # tokens halved, searches not


def test_usage_of_message():
    u = usage_of(message("x", searches=2))
    assert (u.input_tokens, u.output_tokens, u.cache_read_tokens, u.web_searches) == (
        1000,
        2000,
        3000,
        2,
    )
    assert u.cost_usd == pytest.approx((1000 * 3 + 3000 * 0.3 + 2000 * 15) / 1e6 + 0.02)


def test_model_knobs():
    old = anthropic_client.web_search_tool("claude-sonnet-4-5")
    new = anthropic_client.web_search_tool("claude-sonnet-5-5")
    assert old["type"] == "web_search_20250305" and new["type"] == "web_search_20260209"
    assert anthropic_client.reasoning_params("claude-sonnet-4-5", effort="high") == {}
    assert anthropic_client.reasoning_params("claude-sonnet-5-5", effort="high")["thinking"] == {
        "type": "adaptive"
    }
