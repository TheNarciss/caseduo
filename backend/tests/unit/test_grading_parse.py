"""Streaming parser and server-side scoring."""

import json
import random

import pytest

from app.grading.parser import TaggedStreamParser, parse_complete
from app.grading.scoring import ScoresInvalid, parse_scores, weighted_score
from tests.fake_llm import grade_text

RUBRIC = [
    {"key": "reformulation", "label": "R", "weight": 20},
    {"key": "structure", "label": "S", "weight": 30},
    {"key": "recommendation", "label": "Rec", "weight": 50},
]


def run_chunks(text: str, size_picker):
    parser = TaggedStreamParser()
    events = []
    i = 0
    while i < len(text):
        n = size_picker()
        events += parser.feed(text[i : i + n])
        i += n
    events += parser.close()
    return events


@pytest.mark.parametrize("seed", range(20))
def test_any_chunking_gives_the_same_sections(seed):
    rng = random.Random(seed)
    text = grade_text(["reformulation", "structure", "recommendation"], [1, 0, 2])
    events = run_chunks(text, lambda: rng.randint(1, 12))
    kinds = [e.kind for e in events]
    assert kinds[0] == "scores" and kinds[-1] == "follow_up"
    feedback = "".join(e.text for e in events if e.kind == "feedback")
    assert feedback.strip() == parse_complete(text)["feedback"]
    assert "Ce qui était bien" in feedback and "</feedback" not in feedback
    assert json.loads(events[0].text)["score"] == 99


def test_scores_event_before_feedback_finishes():
    parser = TaggedStreamParser()
    text = grade_text(["structure"])
    cut = text.index("### À corriger")
    events = parser.feed(text[:cut])
    assert next(e.kind for e in events) == "scores"
    assert any(e.kind == "feedback" for e in events)


def test_unclosed_feedback_is_kept_on_close():
    parser = TaggedStreamParser()
    parser.feed("<scores>{}</scores><feedback>début du feedback")
    events = parser.close()
    assert "".join(e.text for e in events if e.kind == "feedback").endswith("feedback")


def test_server_side_score_ignores_model_total():
    raw = json.dumps(
        {
            "rubric_scores": [
                {"key": "reformulation", "score": 2},
                {"key": "structure", "score": 1},
                {"key": "recommendation", "score": 0},
            ],
            "score": 99,
        }
    )
    scores, score = parse_scores(raw, RUBRIC)
    assert score == 20 + 15 + 0
    assert [s["weight"] for s in scores] == [20, 30, 50]


def test_missing_criterion_counts_zero_and_marks_are_clamped():
    raw = json.dumps({"rubric_scores": [{"key": "structure", "score": 7}]})
    scores, score = parse_scores(raw, RUBRIC)
    assert scores[1]["score"] == 2 and scores[0]["score"] == 0
    assert scores[0]["justification"] == "Critère non évalué."
    assert score == 30


def test_invalid_scores_raise():
    with pytest.raises(ScoresInvalid):
        parse_scores("pas du json", RUBRIC)
    with pytest.raises(ScoresInvalid):
        parse_scores('{"rubric_scores": []}', RUBRIC)


def test_weighted_score_normalizes_weights():
    assert weighted_score([{"score": 2, "weight": 50}, {"score": 1, "weight": 50}]) == 75
