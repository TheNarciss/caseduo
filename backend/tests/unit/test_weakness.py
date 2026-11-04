from app.game.weakness import criteria_stats, weakest_criteria


def scores(**kw):
    return [{"key": k, "score": v} for k, v in kw.items()]


def test_weakest_three_lowest_average_first():
    rows = [
        scores(structure=0, hypotheses=1, recommendation=2, reformulation=1),
        scores(structure=1, hypotheses=1, recommendation=2, business_sense=0),
        scores(structure=0, hypotheses=2),
    ]
    weak = weakest_criteria(rows)
    assert [w.key for w in weak] == ["business_sense", "structure", "reformulation"]
    assert weak[1].average == 1 / 3 and weak[1].count == 3


def test_ties_prefer_more_evidence_and_perfect_is_not_weak():
    rows = [scores(structure=1, hypotheses=1), scores(hypotheses=1), scores(recommendation=2)]
    assert [w.key for w in weakest_criteria(rows)] == ["hypotheses", "structure"]


def test_unknown_keys_and_bad_values_ignored():
    rows = [[{"key": "bogus", "score": 0}, {"key": "structure", "score": "x"}]]
    assert criteria_stats(rows) == []
