"""A fake Anthropic client for tests: answers a valid exercise for any slot."""

from __future__ import annotations

import json
import re
from types import SimpleNamespace
from typing import Any

from app.catalog import RUBRIC_KEYS

SEARCH_URL = "https://example.org/source"


def _field(text: str, name: str) -> str | None:
    m = re.search(rf"- {name} : (\S+)", text)
    return m.group(1) if m else None


def exercise_json(
    type_: str, style: str = "wavestone", parts: int | None = None, title: str | None = None
) -> dict[str, Any]:
    keys = list(RUBRIC_KEYS[type_]) + (["synthesis"] if style == "mbb" else [])
    weights = [100 // len(keys)] * len(keys)
    weights[0] += 100 - sum(weights)
    is_case = type_ in ("market_sizing", "cadrage", "business_case", "diagnostic", "cadrage_home")
    return {
        "title": title or f"Exercice {type_} de test",
        "type": type_,
        "style": style,
        "language": "fr",
        "difficulty": 3,
        "sector": "banque",
        "prompt": "Un client vous demande quelque chose de précis, voici le contexte détaillé. Que faites-vous ?",
        "parts": [{"question": f"Question {i + 1} ?", "data": None} for i in range(parts)]
        if parts
        else None,
        "context_data": {
            "facts": (
                [
                    {
                        "label": "Chiffre sourcé",
                        "value": "42 M€",
                        "source_url": SEARCH_URL,
                        "hypothesis": False,
                    },
                    {
                        "label": "Chiffre sans source",
                        "value": "10 %",
                        "source_url": None,
                        "hypothesis": False,
                    },
                    {"label": "Hypothèse", "value": "3", "source_url": None, "hypothesis": True},
                ]
                if is_case
                else []
            ),
            "constraints": [],
            "documents": (
                [{"title": "Doc 1", "body": "a"}, {"title": "Doc 2", "body": "b"}]
                if type_ == "cadrage_home"
                else []
            ),
        },
        "model_answer": "Reformulation. Plan en trois branches. Développement détaillé. " * 4,
        "rubric": [
            {"key": k, "label": k, "weight": w, "levels": {"0": "zéro", "1": "un", "2": "deux"}}
            for k, w in zip(keys, weights, strict=True)
        ],
        "sources": [{"url": SEARCH_URL, "title": "Source"}] if is_case else [],
        "targets_weakness": [],
        "estimated_minutes": 5,
    }


def message(
    text: str, *, searches: int = 0, stop_reason: str = "end_turn", model: str = "claude-sonnet-4-5"
) -> SimpleNamespace:
    content: list[Any] = []
    if searches:
        content.append(SimpleNamespace(type="server_tool_use", name="web_search"))
        content.append(
            SimpleNamespace(
                type="web_search_tool_result",
                content=[SimpleNamespace(type="web_search_result", url=SEARCH_URL, title="Source")],
            )
        )
    content.append(SimpleNamespace(type="text", text=text))
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        model=model,
        usage=SimpleNamespace(
            input_tokens=1000,
            output_tokens=2000,
            cache_read_input_tokens=3000,
            cache_creation_input_tokens=0,
            server_tool_use=SimpleNamespace(web_search_requests=searches),
        ),
    )


class FakeMessages:
    def __init__(self, owner: FakeClient) -> None:
        self.owner = owner

    async def create(self, **params: Any) -> SimpleNamespace:
        self.owner.calls.append(params)
        user = params["messages"][0]["content"]
        if self.owner.fail_slots and any(f"slot : {s}" in user for s in self.owner.fail_slots):
            return message("pas de JSON ici")
        type_ = _field(user, "type") or "fit"
        style = _field(user, "style") or "wavestone"
        m = re.search(r"exactement (\d+) questions", user)
        parts = int(m.group(1)) if m else None
        slot = _field(user, "slot") or "x"
        data = exercise_json(type_, style, parts, title=f"Titre {slot} {type_}")
        searches = 1 if "tools" in params else 0
        return message(
            "```json\n" + json.dumps(data, ensure_ascii=False) + "\n```", searches=searches
        )


class FakeClient:
    def __init__(self, fail_slots: set[str] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.fail_slots = fail_slots or set()
        self.messages = FakeMessages(self)


class FakeBatches:
    """messages.batches: create / retrieve / results / cancel, driven by the test."""

    def __init__(self, owner: FakeClient) -> None:
        self.owner = owner
        self.created: dict[str, list[Any]] = {}
        self.status: dict[str, str] = {}
        self.errored: set[str] = set()
        self.cancelled: list[str] = []

    async def create(self, requests: list[Any]) -> SimpleNamespace:
        batch_id = f"msgbatch_{len(self.created) + 1:03d}"
        self.created[batch_id] = list(requests)
        self.status[batch_id] = "in_progress"
        return SimpleNamespace(id=batch_id, processing_status="in_progress")

    async def retrieve(self, batch_id: str) -> SimpleNamespace:
        return SimpleNamespace(id=batch_id, processing_status=self.status[batch_id])

    async def cancel(self, batch_id: str) -> SimpleNamespace:
        self.cancelled.append(batch_id)
        self.status[batch_id] = "canceling"
        return SimpleNamespace(id=batch_id, processing_status="canceling")

    async def results(self, batch_id: str):
        requests = self.created[batch_id]
        owner = self.owner

        async def gen():
            for req in requests:
                cid = req["custom_id"]
                if any(cid.endswith(s) for s in self.errored):
                    yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="errored"))
                    continue
                msg = await FakeMessages(owner).create(**req["params"])
                yield SimpleNamespace(
                    custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg)
                )

        return gen()


def attach_batches(client: FakeClient) -> FakeBatches:
    client.messages.batches = FakeBatches(client)  # type: ignore[attr-defined]
    return client.messages.batches  # type: ignore[attr-defined]
