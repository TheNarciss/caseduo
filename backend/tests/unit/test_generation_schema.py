"""Validation of generated JSON before insertion."""

import pytest

from app.generation.planner import SlotSpec
from app.generation.schema import GenerationInvalid, is_duplicate, validate
from tests.fake_llm import SEARCH_URL, exercise_json


def spec(type_="cadrage", style="wavestone", parts=None, web_search=True, target=False):
    return SlotSpec(
        slot=f"case_{type_}",
        type=type_,
        difficulty=3,
        language="fr",
        style=style,
        sector="banque",
        web_search=web_search,
        target_weakness=target,
        parts=parts,
    )


def test_valid_case_passes_and_repairs_unsourced_fact():
    fields = validate(exercise_json("cadrage"), spec(), search_urls={SEARCH_URL.lower()})
    facts = fields["context_data"]["facts"]
    assert facts[1]["hypothesis"] is True and facts[1]["source_url"] is None
    assert fields["sources"][0]["verified"] is True
    assert sum(c["weight"] for c in fields["rubric"]) == 100
    assert fields["rubric"][0]["label"] == "Reformulation et cadrage"


def test_planned_fields_win():
    data = exercise_json("cadrage")
    data["difficulty"] = 5
    data["language"] = "en"
    fields = validate(data, spec())
    assert fields["difficulty"] == 3 and fields["language"] == "fr"


def test_wrong_type_is_rejected():
    with pytest.raises(GenerationInvalid):
        validate(exercise_json("fit"), spec("cadrage"))


def test_weights_must_sum_to_100():
    data = exercise_json("cadrage")
    data["rubric"][0]["weight"] += 5
    with pytest.raises(GenerationInvalid, match="poids"):
        validate(data, spec())


def test_unknown_or_missing_criteria_are_rejected():
    data = exercise_json("cadrage")
    data["rubric"][0]["key"] = "storyline"
    with pytest.raises(GenerationInvalid):
        validate(data, spec())


def test_mbb_adds_synthesis():
    fields = validate(exercise_json("business_case", "mbb"), spec("business_case", "mbb"))
    assert "synthesis" in {c["key"] for c in fields["rubric"]}


def test_case_needs_three_to_six_facts():
    data = exercise_json("cadrage")
    data["context_data"]["facts"] = data["context_data"]["facts"][:2]
    with pytest.raises(GenerationInvalid, match="chiffres"):
        validate(data, spec())


def test_parts_count_enforced():
    with pytest.raises(GenerationInvalid, match="parties"):
        validate(exercise_json("fit", parts=5), spec("fit", parts=6, web_search=False))
    fields = validate(exercise_json("fit", parts=6), spec("fit", parts=6, web_search=False))
    assert len(fields["parts"]) == 6


def test_invented_sources_rejected_when_search_returned_others():
    with pytest.raises(GenerationInvalid, match="source"):
        validate(exercise_json("cadrage"), spec(), search_urls={"https://other.org/page"})


def test_targets_filled_from_weaknesses_when_targeted():
    fields = validate(exercise_json("cadrage"), spec(target=True), weaknesses=["structure"])
    assert fields["targets_weakness"] == ["structure"]


def test_duplicate_title_same_sector():
    recent = [("Cadrer l'IA générative chez un assureur", "banque")]
    assert is_duplicate("Cadrer l’IA générative chez un assureur !", "banque", recent)
    assert not is_duplicate("Cadrer l'IA générative chez un assureur", "santé", recent)
    data = exercise_json("cadrage", title="Cadrer l'IA générative chez un assureur")
    with pytest.raises(GenerationInvalid, match="doublon"):
        validate(data, spec(), recent_titles=recent)


def test_starter_pack_is_valid():
    from app.catalog import allowed_rubric_keys
    from app.content.starter_pack import exercises

    for _, fields in exercises():
        assert sum(c["weight"] for c in fields["rubric"]) == 100
        assert {c["key"] for c in fields["rubric"]} <= allowed_rubric_keys(
            fields["type"], fields["style"]
        )
