"""The Parcours: content loading, the path's statuses, a lesson from start to finish, the XP,
the checkpoint with its oral item, the legendary threshold, the flag."""

import json
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models import PathItem, PathItemResult, PathProgress
from app.path import loader, schema
from app.path.loader import import_content
from tests.fake_llm import SEARCH_URL  # noqa: F401  (keeps the fake module importable)

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]


def choice(id_: str, skill: str, difficulty: int = 2, correct: str = "a") -> dict:
    return {
        "id": id_,
        "format": "choose_structure",
        "skill": skill,
        "difficulty": difficulty,
        "stem": "Quelle structure ?",
        "explanation": "La règle à retenir.",
        "payload": {
            "options": [
                {"id": "a", "text": "Revenus vs coûts"},
                {"id": "b", "text": "Forces / faiblesses", "why_wrong": "Descriptif."},
                {"id": "c", "text": "Clients / canaux", "why_wrong": "Deuxième niveau."},
            ],
            "correct": correct,
        },
    }


def concept(id_: str, skill: str) -> dict:
    return {
        "id": id_,
        "format": "concept_card",
        "skill": skill,
        "difficulty": 1,
        "payload": {"screens": [{"title": "L'idée", "body": "Reformuler d'abord."}]},
    }


def oral(id_: str, skill: str) -> dict:
    return {
        "id": id_,
        "format": "oral_prompt",
        "skill": skill,
        "difficulty": 3,
        "stem": "Ouvre ce case à voix haute.",
        "explanation": "Reformule, clarifie, annonce ton plan.",
        "payload": {
            "seconds": 60,
            "rubric": [
                {"key": "reformulation", "label": "Objectif reformulé", "weight": 2},
                {"key": "plan", "label": "Plan annoncé", "weight": 1},
            ],
            "model_answer": "Je reformule : … Je vois trois axes : …",
        },
    }


@pytest.fixture
def small_course(tmp_path):
    (tmp_path / "units").mkdir()
    (tmp_path / "items").mkdir()
    unit = {
        "code": "t1",
        "order": 1,
        "title": "Test",
        "nodes": [
            {
                "code": "t1.a",
                "kind": "lesson",
                "title": "A",
                "objective": "Apprendre A.",
                "items": 4,
            },
            {
                "code": "t1.b",
                "kind": "lesson",
                "title": "B",
                "objective": "Apprendre B.",
                "items": 4,
            },
            {
                "code": "t1.applied",
                "kind": "applied",
                "title": "En situation",
                "applied_type": "case",
            },
            {"code": "t1.check", "kind": "checkpoint", "title": "Bilan", "items": 4},
            {"code": "t1.legendary", "kind": "legendary", "title": "Légendaire", "items": 4},
        ],
    }
    (tmp_path / "units" / "01_t1.json").write_text(json.dumps(unit))
    items = [concept("t1.a.000", "t1.a")] + [
        choice(f"t1.a.{i:03d}", "t1.a", 1 + i % 3) for i in range(1, 8)
    ]
    items += [concept("t1.b.000", "t1.b")] + [
        choice(f"t1.b.{i:03d}", "t1.b", 1 + i % 3) for i in range(1, 8)
    ]
    items += [choice(f"t1.check.{i:03d}", "t1.check", 3) for i in range(1, 4)] + [
        oral("t1.check.010", "t1.check")
    ]
    items += [choice(f"t1.legendary.{i:03d}", "t1.legendary", 4) for i in range(1, 5)]
    (tmp_path / "items" / "t1.json").write_text(json.dumps(items, ensure_ascii=False))
    return tmp_path


async def test_repository_content_is_valid_and_loads(db):
    units = schema.load_units(ROOT.parent / "content" / "path" / "units")
    assert [u.code for u in units][:4] == ["u0", "u1", "u2", "u3"]
    items_dir = ROOT.parent / "content" / "path" / "items"
    items = schema.load_items(items_dir) if items_dir.exists() else []
    node_codes = {n.code for u in units for n in u.nodes}
    assert all(it.skill in node_codes for it in items)
    counts = await import_content(db, ROOT.parent / "content" / "path")
    assert counts["units"] == len(units)
    assert counts["changed"] == len(items)
    assert (await import_content(db, ROOT.parent / "content" / "path"))[
        "changed"
    ] == 0  # idempotent


async def test_path_statuses_lesson_flow_and_xp(
    user_client, db, small_course, fake_cli, monkeypatch
):
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "")  # no oral grading here
    client, _user = user_client
    await import_content(db, small_course)

    path = (await client.get("/api/path")).json()
    nodes = {n["code"]: n for u in path["units"] for n in u["nodes"]}
    assert path["active_node"] == "t1.a" and path["total"] == 3
    assert [
        nodes[c]["status"] for c in ("t1.a", "t1.b", "t1.applied", "t1.check", "t1.legendary")
    ] == [
        "active",
        "locked",
        "locked",
        "locked",
        "locked",
    ]
    assert (await client.post("/api/path/nodes/t1.b/start")).status_code == 409

    lesson = (await client.post("/api/path/nodes/t1.a/start", json={"seed": 1})).json()
    assert lesson["node"]["code"] == "t1.a" and lesson["xp"] == 10
    assert lesson["items"][0]["format"] == "concept_card"
    graded = lesson["items"][1:]
    assert (
        len(graded) == 3
        and [it["difficulty"] for it in graded][:2] == sorted(it["difficulty"] for it in graded)[:2]
    )
    assert graded[0]["payload"]["correct"] == "a"  # the key travels: grading happens on the phone

    results = [{"item_id": lesson["items"][0]["id"], "correct": True}]
    results += [
        {"item_id": it["id"], "correct": True, "first_try": i != 0, "ms": 4000}
        for i, it in enumerate(graded)
    ]
    done = (await client.post("/api/path/nodes/t1.a/complete", json={"results": results})).json()
    assert (
        done["passed"] and done["score"] == 67 and done["xp"] == 10 and done["next_node"] == "t1.b"
    )
    assert done["progress"]["xp_today"] == 10 and not done["unit_done"]
    assert (await db.execute(select(PathItemResult))).scalars().all().__len__() == 3

    path = (await client.get("/api/path")).json()
    nodes = {n["code"]: n for u in path["units"] for n in u["nodes"]}
    assert nodes["t1.a"]["status"] == "done" and nodes["t1.a"]["best_score"] == 67
    assert nodes["t1.b"]["status"] == "active" and nodes["t1.applied"]["status"] == "locked"

    # Second lesson: 30 % review from the first one, never-seen items first.
    lesson = (await client.post("/api/path/nodes/t1.b/start", json={"seed": 2})).json()
    skills = [it["skill"] for it in lesson["items"][1:]]
    assert skills.count("t1.a") == 1 and skills.count("t1.b") == 2
    seen = {r.item_id for r in (await db.execute(select(PathItemResult))).scalars()}
    assert not any(it["id"] in seen for it in lesson["items"] if it["skill"] == "t1.a")

    perfect = [{"item_id": it["id"], "correct": True} for it in lesson["items"]]
    done = (await client.post("/api/path/nodes/t1.b/complete", json={"results": perfect})).json()
    assert done["score"] == 100 and done["xp"] == 15  # perfect bonus
    replay = (await client.post("/api/path/nodes/t1.b/complete", json={"results": perfect})).json()
    assert replay["replay"] and replay["xp"] == 5
    progress = (
        await db.execute(select(PathProgress).where(PathProgress.node_code == "t1.b"))
    ).scalar_one()
    assert progress.times == 2 and progress.best_score == 100
    nodes = {
        n["code"]: n for u in (await client.get("/api/path")).json()["units"] for n in u["nodes"]
    }
    assert nodes["t1.applied"]["status"] == "available" and nodes["t1.check"]["status"] == "active"


async def test_checkpoint_with_oral_and_legendary_threshold(
    user_client, db, small_course, fake_cli
):
    client, _user = user_client
    await import_content(db, small_course)
    for code in ("t1.a", "t1.b"):
        lesson = (await client.post(f"/api/path/nodes/{code}/start")).json()
        await client.post(
            f"/api/path/nodes/{code}/complete",
            json={"results": [{"item_id": it["id"], "correct": True} for it in lesson["items"]]},
        )
    check = (await client.post("/api/path/nodes/t1.check/start")).json()
    assert check["pass_score"] == 60 and check["items"][-1]["format"] == "oral_prompt"
    oral_item = check["items"][-1]
    assert "payload" in oral_item and oral_item["payload"]["rubric"][0]["key"] == "reformulation"
    results = [{"item_id": it["id"], "correct": True} for it in check["items"][:-1]]
    results.append(
        {
            "item_id": oral_item["id"],
            "transcript": "Je reformule : le client veut doubler sa marge. Je vois trois axes.",
        }
    )
    done = (
        await client.post("/api/path/nodes/t1.check/complete", json={"results": results})
    ).json()
    assert done["passed"] and done["xp"] == 25
    assert done["oral"][0]["score"] == 100 and "Ce qui était bien" in done["oral"][0]["feedback"]
    assert [c["key"] for c in done["oral"][0]["criteria"]] == ["reformulation", "plan"]
    assert done["unit_done"]

    legendary = (await client.post("/api/path/nodes/t1.legendary/start")).json()
    assert legendary["pass_score"] == 75 and len(legendary["items"]) == 4
    half = [{"item_id": it["id"], "correct": i % 2 == 0} for i, it in enumerate(legendary["items"])]
    failed = (
        await client.post("/api/path/nodes/t1.legendary/complete", json={"results": half})
    ).json()
    assert not failed["passed"] and failed["xp"] == 0 and failed["score"] == 50
    full = [{"item_id": it["id"], "correct": True} for it in legendary["items"]]
    won = (
        await client.post("/api/path/nodes/t1.legendary/complete", json={"results": full})
    ).json()
    assert won["passed"] and won["xp"] == 40

    nodes = {
        n["code"]: n for u in (await client.get("/api/path")).json()["units"] for n in u["nodes"]
    }
    assert nodes["t1.legendary"]["status"] == "done" and nodes["t1.check"]["status"] == "done"


async def test_flag_retires_after_three(user_client, db, small_course):
    client, _ = user_client
    await import_content(db, small_course)
    for _i in range(2):
        resp = await client.post("/api/path/items/t1.a.001/flag", json={"note": "ambigu"})
        assert resp.status_code == 200 and not resp.json()["retired"]
    resp = await client.post("/api/path/items/t1.a.001/flag")
    assert resp.json() == {"id": "t1.a.001", "flag_count": 3, "retired": True}
    item = await db.get(PathItem, "t1.a.001")
    await db.refresh(item)
    assert item.retired and item.flag_note == "ambigu"
    assert (await client.post("/api/path/items/nope/flag")).status_code == 404


def test_validator_refuses_what_the_app_must_never_see(tmp_path):
    bad = choice("t1.a.001", "t1.a")
    bad["payload"]["options"][0]["text"] = (
        "Une bonne réponse beaucoup, beaucoup, beaucoup plus longue que les autres pour aider"
    )
    with pytest.raises(ValueError, match="plus longue"):
        schema.Item.model_validate(bad)
    bad = choice("t1.a.002", "t1.a")
    bad["payload"]["options"][1].pop("why_wrong")
    with pytest.raises(ValueError, match="why_wrong"):
        schema.Item.model_validate(bad)
    assert loader.item_hash(
        schema.Item.model_validate(choice("t1.a.003", "t1.a"))
    ) == loader.item_hash(schema.Item.model_validate(choice("t1.a.003", "t1.a")))
