"""Reading Anthropic messages: final text, search URLs, JSON extraction."""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def final_text(message: Any) -> str:
    """The text the model wrote after its last tool use (search results excluded)."""
    blocks = list(getattr(message, "content", []) or [])
    last_tool = -1
    for i, block in enumerate(blocks):
        if getattr(block, "type", "") in ("server_tool_use", "web_search_tool_result"):
            last_tool = i
    texts = [
        getattr(b, "text", "") for b in blocks[last_tool + 1 :] if getattr(b, "type", "") == "text"
    ]
    if not "".join(texts).strip():  # the JSON may sit before a trailing tool block
        texts = [getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text"]
    return "".join(texts)


def search_urls(message: Any) -> set[str]:
    """Every URL web search returned in this message."""
    urls: set[str] = set()
    for block in getattr(message, "content", []) or []:
        if getattr(block, "type", "") != "web_search_tool_result":
            continue
        content = getattr(block, "content", None)
        if isinstance(content, list):
            for item in content:
                url = getattr(item, "url", None)
                if url:
                    urls.add(normalize_url(url))
    return urls


def normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def extract_json(text: str) -> dict[str, Any]:
    """The JSON object of an answer: the last ```json block, else the outermost braces."""
    candidates = _FENCE.findall(text)
    if candidates:
        raw = candidates[-1]
    else:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("aucun objet JSON dans la réponse")
        raw = text[start : end + 1]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON invalide : {exc}") from exc
    if isinstance(data, dict) and isinstance(data.get("exercises"), list) and data["exercises"]:
        data = data["exercises"][0]
    if not isinstance(data, dict):
        raise ValueError("le JSON n'est pas un objet")
    return data
