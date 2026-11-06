"""Grading an oral item of the Parcours: the transcript against the item's rubric.

Same tagged output as the exercise grader (`<scores>` then `<feedback>`), same engines
(Claude Code on the subscription, else the API). Without either, the item counts as done
and the score is None: the course never blocks on grading.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..db.models import PathItem
from ..grading.parser import TaggedStreamParser
from ..grading.service import provider
from ..llm import anthropic_client, claude_code
from ..llm.cost_tracker import usage_of

logger = logging.getLogger(__name__)

SYSTEM = """Tu es l'interviewer d'un cabinet de conseil. Tu notes la réponse orale d'un candidat (transcription automatique, ne pénalise pas la forme orale) à une question courte d'entraînement, selon une rubric de critères notés 0, 1 ou 2.

Réponds avec exactement deux blocs balisés, dans cet ordre, et rien d'autre :
<scores>
{"rubric_scores": [{"key": "…", "score": 0, "justification": "une phrase", "quote": "citation courte ou vide"}]}
</scores>
<feedback>
Deux ou trois phrases, dans la langue du candidat : ce qui était bien, puis la phrase qu'il aurait dû dire.
</feedback>

Le JSON des notes tient sur une ligne, avec une entrée par critère de la rubric, dans l'ordre, avec la clé exacte."""


def user_message(item: PathItem, transcript: str) -> str:
    rubric = item.payload.get("rubric", [])
    lines = ["## Question", item.stem, "", "### Rubric"]
    for c in rubric:
        lines.append(f"- `{c['key']}` ({c['label']}), poids {c['weight']}")
    lines += ["", "### Réponse attendue (repère)", item.payload.get("model_answer", ""), ""]
    lines += ["### Réponse du candidat", transcript.strip() or "(vide)"]
    return "\n".join(lines)


def score_from(scores_json: str, rubric: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    data = json.loads(scores_json.strip().strip("`").removeprefix("json").strip())
    by_key = {str(s.get("key")): s for s in data.get("rubric_scores", []) if isinstance(s, dict)}
    total_weight = sum(int(c["weight"]) for c in rubric) or 1
    earned = 0.0
    lines = []
    for c in rubric:
        s = by_key.get(c["key"], {})
        mark = max(0, min(2, int(s.get("score", 0) or 0)))
        earned += mark / 2 * int(c["weight"])
        lines.append(
            {
                "key": c["key"],
                "label": c["label"],
                "weight": c["weight"],
                "score": mark,
                "justification": str(s.get("justification", ""))[:300],
            }
        )
    return round(100 * earned / total_weight), lines


async def grade(item: PathItem, transcript: str) -> dict[str, Any]:
    """`{"score": 0-100 | None, "feedback": str, "criteria": [...]}`."""
    if len(transcript.strip()) < 10:
        return {"score": 0, "feedback": "Réponse vide ou trop courte.", "criteria": []}
    rubric = item.payload.get("rubric", [])
    engine = provider()
    text = ""
    try:
        if engine == "claude_code":
            run = claude_code.Run()
            await claude_code.ask(SYSTEM, user_message(item, transcript), run)
            text = run.final_text or run.text
        elif engine == "api":
            client = anthropic_client.get_client()
            message = await client.messages.create(
                model=anthropic_client.MODEL,
                max_tokens=1500,
                system=SYSTEM,
                messages=[{"role": "user", "content": user_message(item, transcript)}],
            )
            usage_of(message)
            text = "".join(getattr(b, "text", "") for b in message.content)
        else:
            return {
                "score": None,
                "feedback": "Notation non configurée : réponse enregistrée.",
                "criteria": [],
            }
        parser = TaggedStreamParser()
        parser.feed(text)
        parser.close()
        score, criteria = score_from(parser.sections.get("scores", ""), rubric)
        return {
            "score": score,
            "feedback": parser.sections.get("feedback", "").strip(),
            "criteria": criteria,
        }
    except Exception as exc:  # the course never blocks on grading
        logger.warning("Oral item %s not graded: %s", item.id, exc)
        return {
            "score": None,
            "feedback": "La notation n'a pas abouti, réponse enregistrée.",
            "criteria": [],
        }
