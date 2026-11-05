"""Building one generation request: the per-slot user message and the API params.

The system prompt (prompts/generate.md) is identical for every slot and
cached; everything that varies lives in the user message.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..catalog import TYPE_LABELS, allowed_rubric_keys, criterion_label
from ..llm import anthropic_client, prompts
from .context import GenerationContext
from .planner import WEEKDAY_FR, DayPlan, SlotSpec

MAX_RECENT_TITLES = 40


def user_message(plan: DayPlan, spec: SlotSpec, ctx: GenerationContext) -> str:
    day: date = plan.day
    weak = ctx.weaknesses
    lines = [
        f"Date : {WEEKDAY_FR[day.weekday()]} {day.isoformat()}",
        f"Jour de la semaine : {WEEKDAY_FR[day.weekday()]}",
        f"Secteur imposé du jour : {plan.sector}",
        "",
        "Exercice à produire (1 seul, un objet JSON) :",
        f"- slot : {spec.slot}",
        f"- type : {spec.type} ({TYPE_LABELS[spec.type]})",
        f"- style : {spec.style}",
        f"- langue : {spec.language}",
        f"- difficulté : {spec.difficulty}/5",
        f"- secteur de cet exercice : {spec.sector}",
        f"- clés de rubric à utiliser : {', '.join(sorted(allowed_rubric_keys(spec.type, spec.style)))}",
    ]
    if spec.brief:
        lines.append(f"- consigne : {spec.brief}")
    if spec.parts:
        lines.append(f"- parties : exactement {spec.parts} questions successives dans `parts`")
    if spec.web_search:
        lines.append(
            f"- recherche web : autorisée, au plus {anthropic_client.WEB_SEARCH_MAX_USES} recherches, "
            "pour trouver 3 à 6 chiffres réels et leurs URLs"
        )
    else:
        lines.append("- recherche web : non nécessaire pour ce type, n'en fais pas")
    lines.append("")
    if weak:
        lines.append("Critères les plus faibles du candidat sur 14 jours :")
        lines += [f"- {w.key} ({criterion_label(w.key)}) : moyenne {w.average:.1f}/2" for w in weak]
        lines.append(
            "Cet exercice doit mettre ces critères sous pression et les lister dans targets_weakness."
            if spec.target_weakness
            else "Cet exercice n'a pas à cibler ces critères (targets_weakness peut rester vide)."
        )
    else:
        lines.append("Pas encore d'historique de notes : targets_weakness reste vide.")
    recent = ctx.recent_titles.get(spec.type, [])[-MAX_RECENT_TITLES:]
    if recent:
        lines.append("")
        lines.append(
            "Titres déjà utilisés ces 60 derniers jours pour ce type (ne pas reproduire) :"
        )
        lines += [f"- {t} ({s})" for t, s in recent]
    lines.append("")
    lines.append("Réponds avec un seul objet JSON dans un bloc ```json, sans rien après.")
    return "\n".join(lines)


def params(plan: DayPlan, spec: SlotSpec, ctx: GenerationContext) -> dict[str, Any]:
    """Keyword arguments for `messages.create` (also the `params` of a batch request)."""
    model = anthropic_client.MODEL
    out: dict[str, Any] = {
        "model": model,
        "max_tokens": anthropic_client.GENERATION_MAX_TOKENS,
        "system": anthropic_client.cached_system(prompts.load("generate")),
        "messages": [{"role": "user", "content": user_message(plan, spec, ctx)}],
        **anthropic_client.reasoning_params(model, effort=anthropic_client.GENERATION_EFFORT),
    }
    if spec.web_search and anthropic_client.WEB_SEARCH_MAX_USES > 0:
        out["tools"] = [anthropic_client.web_search_tool(model)]
    return out
