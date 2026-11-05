"""What to generate for a given day — pure, deterministic, tested.

The spec, rule by rule:
- 5 cases: market_sizing, cadrage (data/AI project at a client), business_case
  (ROI), diagnostic (data maturity), and one more at a higher difficulty.
  Thursday's extra case is the weekly tech_screen.
- 2 brainteasers on weekdays, 3 on the weekend (logic, quick estimate, mental math).
- 1 fit question every day; PEI flavours (leadership, personal impact,
  difficult situation) on Tuesday, Thursday and Saturday.
- Friday: + 1 cadrage_home (5 text slides, due Sunday night).
- Difficulty: Mon–Tue 2–3, Wed–Thu 3–4, Fri 4–5, weekend 1–2; capped at 2
  during the owner's first week (easy wins).
- MBB style for 1 case in 5 from Wednesday to Friday.
- Sectors rotate over the week; Tuesday is industry/defence/aero.
- ~70 % French, ~30 % English, decided by a stable hash of (date, slot).
- At least 2 of the 5 cases put the owner's weakest criteria under pressure.
- Sunday: the mock interview's exercises (1 fit, 1 market sizing, 1 cadrage);
  one Sunday in four it is MBB style (PEI + a 4-part interviewer-led case,
  in English one time in two). Saturday of even ISO weeks: the 6-question
  fit mock (15 min).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

from ..catalog import CASE_TYPES, SECTORS

WEEKDAY_FR = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

DIFFICULTY_BANDS = {0: (2, 3), 1: (2, 3), 2: (3, 4), 3: (3, 4), 4: (4, 5), 5: (1, 2), 6: (1, 2)}
EASY_CAP = 2
MOCK_DIFFICULTY = 3

BRAINTEASER_KINDS = ("logique", "estimation rapide", "calcul mental")
FIT_BRIEFS = (
    "question de motivation : ton parcours en 2 minutes, et pourquoi le conseil",
    "question PEI (style McKinsey) sur le leadership : une fois où tu as entraîné une équipe sans autorité hiérarchique",
    "question de motivation : pourquoi nous, et pourquoi quitter un grand groupe industriel",
    "question PEI (style McKinsey) sur l'impact personnel : une fois où tu as changé l'avis de quelqu'un d'important",
    "question comportementale : un échec ou un conflit, ce que tu en as tiré",
    "question PEI (style McKinsey) sur une situation difficile : une décision sous pression avec des informations incomplètes",
    "question de motivation : pourquoi la data et l'IA côté conseil plutôt que côté produit, et pourquoi Singapour ou Paris",
)
WEB_SEARCH_TYPES = frozenset({*CASE_TYPES, "cadrage_home"})
ESTIMATED_MINUTES = {
    "market_sizing": 6,
    "cadrage": 8,
    "business_case": 8,
    "diagnostic": 7,
    "brainteaser": 4,
    "fit": 3,
    "tech_screen": 6,
    "cadrage_home": 120,
}


@dataclass(frozen=True)
class SlotSpec:
    """One exercise to produce."""

    slot: str
    type: str
    difficulty: int
    language: str
    style: str
    sector: str
    web_search: bool
    target_weakness: bool = False
    brief: str = ""
    parts: int | None = None
    is_mock: bool = False
    estimated_minutes: int = 5


@dataclass(frozen=True)
class DayPlan:
    day: date
    sector: str
    slots: tuple[SlotSpec, ...] = field(default_factory=tuple)

    def slot(self, name: str) -> SlotSpec | None:
        return next((s for s in self.slots if s.slot == name), None)


def iso_week(day: date) -> int:
    return day.isocalendar()[1]


def is_english(day: date, slot: str) -> bool:
    """~30 % English, stable for a given (date, slot)."""
    digest = hashlib.sha1(f"{day.isoformat()}:{slot}".encode()).hexdigest()
    return int(digest[:8], 16) % 10 < 3


def mock_kind(day: date) -> str | None:
    """`full` on Sundays, `fit` on Saturdays of even ISO weeks, else None."""
    if day.weekday() == 6:
        return "full"
    if day.weekday() == 5 and iso_week(day) % 2 == 0:
        return "fit"
    return None


def mock_is_mbb(day: date) -> bool:
    return day.weekday() == 6 and iso_week(day) % 4 == 0


def mock_language(day: date) -> str:
    """MBB mocks are in English one time in two; the regular mock is in French."""
    return "en" if mock_is_mbb(day) and iso_week(day) % 8 == 0 else "fr"


def _lang(day: date, slot: str) -> str:
    return "en" if is_english(day, slot) else "fr"


def plan_day(day: date, *, easy_mode: bool = False, has_weaknesses: bool = False) -> DayPlan:
    w = day.weekday()
    lo, hi = DIFFICULTY_BANDS[w]
    extra_difficulty = min(5, hi + 1)

    def cap(d: int) -> int:
        return min(d, EASY_CAP) if easy_mode else d

    sector = SECTORS[w]  # Tuesday → industrie/défense, by construction of SECTORS

    def sector_at(offset: int) -> str:
        return SECTORS[(w + offset) % len(SECTORS)]

    extra_type = "tech_screen" if w == 3 else CASE_TYPES[day.toordinal() % len(CASE_TYPES)]
    mbb_slot = {2: "case_extra", 3: "case_business_case", 4: "case_extra"}.get(w)
    # Two case slots carry the weaknesses; which two rotates with the day.
    weak_candidates = [
        "case_cadrage",
        "case_business_case",
        "case_diagnostic",
        "case_market_sizing",
    ]
    first = day.toordinal() % len(weak_candidates)
    weak_slots = {weak_candidates[first], weak_candidates[(first + 1) % len(weak_candidates)]}

    def case(slot: str, type_: str, difficulty: int, sector_name: str, brief: str = "") -> SlotSpec:
        style = "mbb" if slot == mbb_slot else "wavestone"
        if style == "mbb":
            brief = (brief + " " if brief else "") + (
                "Style MBB : énoncé plus long avec les données chiffrées dès le départ, "
                "une question précise à la fois, synthèse finale en 30 secondes exigée."
            )
        return SlotSpec(
            slot=slot,
            type=type_,
            difficulty=cap(difficulty),
            language=_lang(day, slot),
            style=style,
            sector=sector_name,
            web_search=type_ in WEB_SEARCH_TYPES,
            target_weakness=has_weaknesses and slot in weak_slots,
            brief=brief,
            estimated_minutes=ESTIMATED_MINUTES[type_] + (3 if style == "mbb" else 0),
        )

    slots: list[SlotSpec] = []
    n_brainteasers = 3 if w >= 5 else 2
    for i in range(n_brainteasers):
        kind = BRAINTEASER_KINDS[(day.toordinal() + i) % len(BRAINTEASER_KINDS)]
        slot = f"brainteaser_{i + 1}"
        slots.append(
            SlotSpec(
                slot=slot,
                type="brainteaser",
                difficulty=cap(lo),
                language=_lang(day, slot),
                style="wavestone",
                sector="général",
                web_search=False,
                brief=f"Brainteaser de type {kind}, 3 à 5 minutes.",
                estimated_minutes=ESTIMATED_MINUTES["brainteaser"],
            )
        )
    slots.append(
        SlotSpec(
            slot="fit",
            type="fit",
            difficulty=cap(lo),
            language=_lang(day, "fit"),
            style="wavestone",
            sector="général",
            web_search=False,
            brief=FIT_BRIEFS[w],
            estimated_minutes=ESTIMATED_MINUTES["fit"],
        )
    )
    slots += [
        case(
            "case_market_sizing",
            "market_sizing",
            lo,
            sector_at(4),
            "Décomposition top-down OU bottom-up, pas les deux.",
        ),
        case(
            "case_cadrage",
            "cadrage",
            hi,
            sector,
            "Note de cadrage d'un projet data/IA chez un client du secteur.",
        ),
        case(
            "case_business_case",
            "business_case",
            hi,
            sector_at(2),
            "ROI chiffré d'un projet data/IA.",
        ),
        case(
            "case_diagnostic",
            "diagnostic",
            lo,
            sector,
            "Diagnostic de maturité data/IA : par où commencer.",
        ),
        case(
            "case_extra",
            extra_type,
            extra_difficulty,
            sector if extra_type == "tech_screen" else sector_at(6),
            "Le case « au choix » du jour, d'un cran plus difficile."
            + (
                " Question technique data/IA telle que QuantumBlack ou BCG X la pose, à répondre à l'oral."
                if extra_type == "tech_screen"
                else ""
            ),
        ),
    ]

    if w == 4:
        slots.append(
            SlotSpec(
                slot="cadrage_home",
                type="cadrage_home",
                difficulty=cap(hi),
                language="fr",
                style="wavestone",
                sector=sector_at(1),
                web_search=True,
                brief=(
                    "Étude de cas à préparer à la maison pendant le week-end, rendue en 5 slides-texte "
                    "avant dimanche soir et présentée à un associé de la practice Data & IA."
                ),
                estimated_minutes=ESTIMATED_MINUTES["cadrage_home"],
            )
        )

    mock = mock_kind(day)
    if mock == "full":
        slots += _sunday_mock(day, cap)
    elif mock == "fit":
        slots.append(
            SlotSpec(
                slot="mock_fit_set",
                type="fit",
                difficulty=cap(MOCK_DIFFICULTY),
                language="fr",
                style="wavestone",
                sector="général",
                web_search=False,
                brief=(
                    "Mock fit complet : 6 questions enchaînées en 15 minutes (parcours, pourquoi le conseil, "
                    "pourquoi nous, un échec, une question PEI leadership, une question PEI situation difficile)."
                ),
                parts=6,
                is_mock=True,
                estimated_minutes=15,
            )
        )
    return DayPlan(day=day, sector=sector, slots=tuple(slots))


def _sunday_mock(day: date, cap) -> list[SlotSpec]:
    lang = mock_language(day)
    if mock_is_mbb(day):
        return [
            SlotSpec(
                slot="mock_pei",
                type="fit",
                difficulty=cap(MOCK_DIFFICULTY),
                language=lang,
                style="mbb",
                sector="général",
                web_search=False,
                brief="Mock MBB : une question PEI (McKinsey) avec relances, réponse STAR chiffrée.",
                is_mock=True,
                estimated_minutes=6,
            ),
            SlotSpec(
                slot="mock_case_mbb",
                type="business_case",
                difficulty=cap(MOCK_DIFFICULTY + 1),
                language=lang,
                style="mbb",
                sector=SECTORS[iso_week(day) % len(SECTORS)],
                web_search=True,
                brief=(
                    "Mock MBB : case mené par l'interviewer de 25 minutes, découpé en 4 questions successives "
                    "avec les données fournies à chaque étape ; la 4e partie demande la synthèse finale en 30 secondes."
                ),
                parts=4,
                is_mock=True,
                estimated_minutes=25,
            ),
        ]
    return [
        SlotSpec(
            slot="mock_fit",
            type="fit",
            difficulty=cap(MOCK_DIFFICULTY),
            language=lang,
            style="wavestone",
            sector="général",
            web_search=False,
            brief="Mock entretien : la question de fit d'ouverture.",
            is_mock=True,
            estimated_minutes=5,
        ),
        SlotSpec(
            slot="mock_market_sizing",
            type="market_sizing",
            difficulty=cap(MOCK_DIFFICULTY),
            language=lang,
            style="wavestone",
            sector=SECTORS[(iso_week(day) + 2) % len(SECTORS)],
            web_search=True,
            brief="Mock entretien : market sizing à l'oral, suivi d'une relance.",
            is_mock=True,
            estimated_minutes=8,
        ),
        SlotSpec(
            slot="mock_cadrage",
            type="cadrage",
            difficulty=cap(MOCK_DIFFICULTY),
            language=lang,
            style="wavestone",
            sector=SECTORS[iso_week(day) % len(SECTORS)],
            web_search=True,
            brief="Mock entretien : note de cadrage à l'oral, suivie d'une relance.",
            is_mock=True,
            estimated_minutes=10,
        ),
    ]
