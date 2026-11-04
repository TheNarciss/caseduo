"""Weekly leagues with 5 named bots — pure, deterministic per (user, week).

One user for now: each week, five bots with realistic XP curves (steady,
weekend warrior, early burst, late sprint, irregular), scaled to the tier.
Promotion for the top 2, relegation for the bottom 2, on Sunday night.
Bots will be replaced by real users later; the shape of a member stays.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from datetime import date

from ..catalog import LEAGUES

BOT_NAMES = (
    "Camille", "Hugo", "Inès", "Lucas", "Mei", "Arjun", "Chloé", "Théo", "Wei Ling",
    "Sofia", "Raphaël", "Aiko", "Nathan", "Priya", "Jules", "Léa", "Marcus", "Zoé",
    "Ethan", "Nour", "Siddharth", "Manon", "Kenji", "Anaïs",
)  # fmt: skip
WEEKLY_RANGE = {"bronze": (120, 420), "silver": (280, 680), "gold": (480, 1000)}
PROFILES = {
    "steady": (1, 1, 1, 1, 1, 0.8, 0.8),
    "weekend": (0.4, 0.3, 0.5, 0.4, 0.6, 2.2, 2.6),
    "early": (2.0, 1.8, 1.4, 0.8, 0.5, 0.3, 0.2),
    "late": (0.2, 0.4, 0.6, 0.9, 1.4, 1.8, 2.1),
    "irregular": (1.6, 0, 1.8, 0, 1.5, 0.2, 1.4),
}
PROMOTE_TOP = 2
RELEGATE_BOTTOM = 2
SIZE = 6


@dataclass(frozen=True)
class Member:
    name: str
    xp: int
    is_me: bool
    rank: int = 0


def _rng(user_id: str, week_start: date) -> random.Random:
    seed = hashlib.sha256(f"{user_id}:{week_start.isoformat()}".encode()).hexdigest()
    return random.Random(int(seed[:16], 16))


def generate_bots(user_id: str, week_start: date, tier: str) -> list[dict]:
    rng = _rng(user_id, week_start)
    lo, hi = WEEKLY_RANGE[tier]
    names = rng.sample(BOT_NAMES, 5)
    profiles = rng.sample(list(PROFILES), 5)
    bots = []
    for name, profile in zip(names, profiles, strict=True):
        total = rng.randint(lo, hi)
        weights = [max(0.0, w * rng.uniform(0.6, 1.4)) for w in PROFILES[profile]]
        scale = total / (sum(weights) or 1)
        daily = [round(w * scale / 5) * 5 for w in weights]  # XP comes in multiples of 5
        bots.append({"name": name, "profile": profile, "daily_xp": daily})
    return bots


def bot_xp(bot: dict, day_index: int, fraction: float) -> int:
    """XP of a bot after `day_index` full days and `fraction` of the current day."""
    daily = bot["daily_xp"]
    if day_index >= 7:
        return sum(daily)
    done = sum(daily[:day_index])
    return done + int(daily[day_index] * min(1.0, max(0.0, fraction)) / 5) * 5


def standings(
    my_name: str, my_xp: int, bots: list[dict], day_index: int, fraction: float
) -> list[Member]:
    members = [Member(my_name, my_xp, True)] + [
        Member(b["name"], bot_xp(b, day_index, fraction), False) for b in bots
    ]
    # ties: the user first (a real person beats a bot at equal XP)
    ordered = sorted(members, key=lambda m: (-m.xp, not m.is_me, m.name))
    return [Member(m.name, m.xp, m.is_me, i + 1) for i, m in enumerate(ordered)]


def outcome(rank: int, tier: str) -> str:
    index = LEAGUES.index(tier)
    if rank <= PROMOTE_TOP and index < len(LEAGUES) - 1:
        return "promoted"
    if rank > SIZE - RELEGATE_BOTTOM and index > 0:
        return "relegated"
    return "stayed"


def next_tier(tier: str, result: str) -> str:
    index = LEAGUES.index(tier)
    if result == "promoted":
        return LEAGUES[min(index + 1, len(LEAGUES) - 1)]
    if result == "relegated":
        return LEAGUES[max(index - 1, 0)]
    return tier
