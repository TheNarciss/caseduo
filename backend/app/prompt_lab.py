"""Prompt lab: try an edited system prompt on real data, without touching the app's content.

    python -m app.prompt_lab generate --date 2026-11-06 [--slots case_cadrage,fit] [--out /app/prompt_lab]
    python -m app.prompt_lab grade --attempt <uuid> [--out …]
    python -m app.prompt_lab replace --date 2026-11-06

- `generate` regenerates slots of a day with the current prompts/generate.md
  and writes, per slot, what is stored today (`<slot>.stored.md`) next to
  the new version (`<slot>.new.md` + `.json`). Nothing is inserted.
- `grade` re-grades an existing attempt with the current prompts/grade.md
  and prints old vs new marks per criterion. Nothing is stored.
- `replace` deletes the day's exercises nobody answered and regenerates
  them for real (same as POST /api/admin/generate with force).

Every call is logged with its cost; it counts against the daily cap.
See docs/PROMPT_TUNING.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import delete, exists, select

from . import logging_config
from .auth import User
from .db import async_session_factory
from .db.models import Attempt, Exercise
from .generation import service
from .generation.sync import generate_slot
from .grading import service as grading
from .grading.parser import parse_complete
from .grading.scoring import parse_scores
from .llm import anthropic_client, cost_tracker
from .llm.cost_tracker import usage_of
from .llm.messages import final_text


def exercise_markdown(fields: dict[str, Any]) -> str:
    facts = "\n".join(
        f"- {f['label']} : {f['value']} ({f.get('source_url') or 'hypothèse'})"
        for f in fields.get("context_data", {}).get("facts", [])
    )
    rubric = "\n".join(
        f"- **{c['label']}** ({c['weight']}) — 0 : {c['levels']['0']} / 1 : {c['levels']['1']} / 2 : {c['levels']['2']}"
        for c in fields.get("rubric", [])
    )
    sources = "\n".join(f"- {s['title']} — {s['url']}" for s in fields.get("sources", []))
    return (
        f"# {fields['title']}\n\n"
        f"_{fields['type']} · {fields['style']} · {fields['language']} · difficulté {fields['difficulty']} · {fields['sector']}_\n\n"
        f"## Énoncé\n\n{fields['prompt']}\n\n## Données\n\n{facts or '(aucune)'}\n\n"
        f"## Corrigé\n\n{fields['model_answer']}\n\n## Rubric\n\n{rubric}\n\n## Sources\n\n{sources or '(aucune)'}\n"
    )


def _stored_fields(ex: Exercise) -> dict[str, Any]:
    return {
        c: getattr(ex, c)
        for c in (
            "title",
            "type",
            "style",
            "language",
            "difficulty",
            "sector",
            "prompt",
            "context_data",
            "model_answer",
            "rubric",
            "sources",
        )
    }


async def cmd_generate(day: date, slots: list[str] | None, out: Path) -> None:
    target = out / day.isoformat()
    target.mkdir(parents=True, exist_ok=True)
    async with async_session_factory() as session:
        plan, ctx = await service.plan_for(session, day)
        stored = {
            e.slot: e
            for e in (await session.execute(select(Exercise).where(Exercise.date == day))).scalars()
        }
        specs = [s for s in plan.slots if not slots or s.slot in slots]
        total = 0.0
        for spec in specs:
            result = await generate_slot(plan, spec, ctx)
            total += result.usage.cost_usd
            await cost_tracker.record_cost(session, result.usage.cost_usd)
            if spec.slot in stored:
                (target / f"{spec.slot}.stored.md").write_text(
                    exercise_markdown(_stored_fields(stored[spec.slot]))
                )
            if result.fields is None:
                (target / f"{spec.slot}.errors.json").write_text(
                    json.dumps(result.errors, ensure_ascii=False, indent=2)
                )
                print(f"✗ {spec.slot} : rejeté 3 fois — voir {spec.slot}.errors.json")
                continue
            (target / f"{spec.slot}.new.json").write_text(
                json.dumps(result.fields, ensure_ascii=False, indent=2)
            )
            (target / f"{spec.slot}.new.md").write_text(exercise_markdown(result.fields))
            print(f"✓ {spec.slot} : « {result.fields['title']} » (${result.usage.cost_usd:.4f})")
        print(f"\nFichiers dans {target} — coût total ${total:.4f}")
        print(f"Comparer : diff -u {target}/<slot>.stored.md {target}/<slot>.new.md")


async def cmd_grade(attempt_id: uuid.UUID, out: Path) -> None:
    async with async_session_factory() as session:
        attempt = await session.get(Attempt, attempt_id)
        if attempt is None:
            raise SystemExit("Tentative introuvable.")
        exercise = await session.get(Exercise, attempt.exercise_id)
        user = await session.get(User, attempt.user_id)
        parent = (
            await session.get(Attempt, attempt.parent_attempt_id)
            if attempt.parent_attempt_id
            else None
        )
        assert exercise is not None and user is not None
        body = grading.GradeRequest(
            exercise_id=exercise.id,
            kind=attempt.kind,  # type: ignore[arg-type]
            answer_text=attempt.answer_text,
            duration_seconds=attempt.duration_seconds,
            input_mode=attempt.input_mode,  # type: ignore[arg-type]
        )
        p = grading.Prepared(
            user=user,
            exercise=exercise,
            body=body,
            answer_text=attempt.answer_text,
            parent=parent,
            revealed_before=attempt.revealed_data,
        )
        if exercise.type == "fit":
            from .services.fit import fit_context

            p.fit_context = await fit_context(
                session, user.id, attempt.local_date, exclude_exercise=exercise.id
            )
        message = await anthropic_client.get_client().messages.create(**grading._params(p))
        usage = usage_of(message)
        await cost_tracker.record_cost(session, usage.cost_usd)
        sections = parse_complete(final_text(message))
        new_scores, new_total = parse_scores(sections.get("scores", "{}"), exercise.rubric)
        print(f"{exercise.title}\n")
        print(f"{'critère':<45} avant  après")
        old = {s["key"]: s["score"] for s in attempt.rubric_scores}
        for s in new_scores:
            print(f"{s['label'][:44]:<45} {old.get(s['key'], '-')!s:>5}  {s['score']:>5}")
        print(f"{'score':<45} {attempt.score:>5}  {new_total:>5}   (${usage.cost_usd:.4f})")
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"grade-{attempt_id}.md"
        path.write_text(
            f"# Avant ({attempt.score})\n\n{attempt.feedback}\n\nRelance : {attempt.follow_up}\n\n"
            f"# Après ({new_total})\n\n{sections.get('feedback', '')}\n\nRelance : {sections.get('follow_up', '')}\n"
        )
        print(f"\nFeedback avant/après : {path}")


async def cmd_replace(day: date) -> None:
    async with async_session_factory() as session:
        answered = exists().where(Attempt.exercise_id == Exercise.id)
        result = await session.execute(delete(Exercise).where(Exercise.date == day, ~answered))
        await session.commit()
        print(f"{result.rowcount} exercice(s) sans réponse supprimé(s) pour {day}")  # type: ignore[attr-defined]
        run = await service.generate_day_sync(session, day, job="sync")
        if run:
            print(f"{run.n_succeeded}/{run.n_requests} régénérés, ${run.cost_usd:.4f}")


def main() -> None:
    logging_config.configure("WARNING")
    parser = argparse.ArgumentParser(prog="python -m app.prompt_lab")
    sub = parser.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--date", type=date.fromisoformat, required=True)
    g.add_argument("--slots", help="liste séparée par des virgules (défaut : tous)")
    g.add_argument("--out", type=Path, default=Path("/tmp/prompt_lab"))
    r = sub.add_parser("grade")
    r.add_argument("--attempt", type=uuid.UUID, required=True)
    r.add_argument("--out", type=Path, default=Path("/tmp/prompt_lab"))
    x = sub.add_parser("replace")
    x.add_argument("--date", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    if args.cmd == "generate":
        slots = [s.strip() for s in args.slots.split(",")] if args.slots else None
        asyncio.run(cmd_generate(args.date, slots, args.out))
    elif args.cmd == "grade":
        asyncio.run(cmd_grade(args.attempt, args.out))
    else:
        asyncio.run(cmd_replace(args.date))


if __name__ == "__main__":
    main()
