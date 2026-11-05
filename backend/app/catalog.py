"""The vocabulary of CaseDuo: exercise types, rubric criteria, sectors, leagues.

One place for every closed list, so the generator's JSON schema, the
grader, the weakness computation and the API labels all agree.
"""

from __future__ import annotations

# ── Exercise types ──────────────────────────────────────────────────────────

CASE_TYPES = ("market_sizing", "cadrage", "business_case", "diagnostic")
EXERCISE_TYPES = (
    *CASE_TYPES,
    "brainteaser",
    "fit",
    "cadrage_home",
    "tech_screen",
)

TYPE_LABELS: dict[str, str] = {
    "market_sizing": "Market sizing",
    "cadrage": "Note de cadrage",
    "business_case": "Business case",
    "diagnostic": "Diagnostic",
    "brainteaser": "Brainteaser",
    "fit": "Fit",
    "cadrage_home": "Cadrage à domicile",
    "tech_screen": "Tech screen",
}

STYLES = ("wavestone", "mbb")
LANGUAGES = ("fr", "en")
ATTEMPT_KINDS = ("main", "retry_2min", "follow_up")

# ── Sectors (rotate over the week; Tuesday is always industry/defence/aero) ──

SECTORS = (
    "banque",
    "industrie/défense",
    "assurance",
    "énergie",
    "santé",
    "retail",
    "secteur public",
)
TUESDAY_SECTOR = "industrie/défense"

# ── Rubric criteria ─────────────────────────────────────────────────────────
# Canonical keys: the generator must use them, so that weaknesses can be
# averaged across days and exercises.

CRITERIA: dict[str, str] = {
    # cases (the five the spec requires)
    "reformulation": "Reformulation et cadrage",
    "structure": "Structure annoncée avant le déroulé",
    "hypotheses": "Hypothèses explicites et chiffrage décomposé",
    "business_sense": "Sens business et pertinence sectorielle",
    "recommendation": "Recommandation claire et assumée",
    # MBB style
    "synthesis": "Synthèse finale en 30 secondes (so what)",
    # fit / PEI
    "concrete": "Concret et chiffré",
    "coherence": "Cohérence avec le parcours",
    "motivation": "Motivation crédible pour le conseil",
    "concision": "Concision",
    "no_self_deprecation": "Absence de dévalorisation",
    # tech screen
    "rigor": "Rigueur technique",
    "tradeoffs": "Trade-offs explicites",
    "vulgarisation": "Vulgarisation pour un partner",
    # brainteaser
    "accuracy": "Bonne réponse ou bon ordre de grandeur",
    "sanity_check": "Vérification de cohérence",
    # cadrage à domicile
    "storyline": "Storyline et titres-messages",
}

# Which criteria a rubric of each type is built from (4 to 6, weights sum to 100).
RUBRIC_KEYS: dict[str, tuple[str, ...]] = {
    "market_sizing": (
        "reformulation",
        "structure",
        "hypotheses",
        "business_sense",
        "recommendation",
    ),
    "cadrage": ("reformulation", "structure", "hypotheses", "business_sense", "recommendation"),
    "business_case": (
        "reformulation",
        "structure",
        "hypotheses",
        "business_sense",
        "recommendation",
    ),
    "diagnostic": ("reformulation", "structure", "hypotheses", "business_sense", "recommendation"),
    "brainteaser": ("structure", "hypotheses", "accuracy", "sanity_check", "concision"),
    "fit": ("concrete", "coherence", "motivation", "concision", "no_self_deprecation"),
    "cadrage_home": ("storyline", "structure", "hypotheses", "business_sense", "recommendation"),
    "tech_screen": ("structure", "rigor", "tradeoffs", "vulgarisation", "recommendation"),
}
MBB_EXTRA_KEY = "synthesis"


def allowed_rubric_keys(exercise_type: str, style: str) -> set[str]:
    keys = set(RUBRIC_KEYS[exercise_type])
    if style == "mbb":
        keys.add(MBB_EXTRA_KEY)
    return keys


def criterion_label(key: str) -> str:
    return CRITERIA.get(key, key)


# ── Leagues ─────────────────────────────────────────────────────────────────

LEAGUES = ("bronze", "silver", "gold")
LEAGUE_LABELS = {"bronze": "Bronze", "silver": "Argent", "gold": "Or"}
