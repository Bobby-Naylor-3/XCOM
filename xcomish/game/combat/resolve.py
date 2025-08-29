# game/combat/resolve.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional
import random
import math

from game import settings as S
from game.combat.hit import compute_hit
from game.world.cover import compute_tile_cover
from game.world.los import facing_side, Coord

Outcome = Literal["blocked", "miss", "graze", "hit", "crit"]

@dataclass(slots=True)
class ShotPreview:
    los: bool
    hit_chance: int
    crit_chance: int        # effective crit (capped by hit)
    graze_band: int         # percent window above hit that becomes graze
    flanked: bool
    cover_facing: str       # "none"|"half"|"full"
    distance_tiles: float
    dmg_base_min: int
    dmg_base_max: int
    dmg_graze_min: int
    dmg_graze_max: int
    dmg_crit_min: int
    dmg_crit_max: int

@dataclass(slots=True)
class ShotResult:
    outcome: Outcome
    roll: int
    hit_chance: int
    crit_chance: int
    graze_band: int
    damage: int
    flanked: bool
    cover_facing: str
    distance_tiles: float

def _crit_for_context(hit_total: int, flanked: bool, cover_facing: str, distance_tiles: float) -> int:
    crit = S.BASE_CRIT_PERCENT
    if flanked:
        crit += S.CRIT_FLANK_BONUS
    if cover_facing == "half":
        crit += S.CRIT_HALF_COVER_PENALTY
    elif cover_facing == "full":
        crit += S.CRIT_FULL_COVER_PENALTY
    if distance_tiles < 2.0:
        crit += S.CRIT_POINT_BLANK_BONUS
    crit = max(0, min(100, int(round(crit))))
    # Don't let crit exceed the actual hit chance (can’t crit on a miss)
    return min(hit_total, crit)

def preview_probabilities(grid, shooter: Coord, target: Coord) -> ShotPreview:
    bd = compute_hit(grid, shooter, target, base_aim=S.BASE_AIM_PERCENT)
    if not bd.los:
        return ShotPreview(
            los=False, hit_chance=0, crit_chance=0, graze_band=0,
            flanked=False, cover_facing="full", distance_tiles=bd.distance_tiles,
            dmg_base_min=S.DAMAGE_BASE_MIN, dmg_base_max=S.DAMAGE_BASE_MAX,
            dmg_graze_min=max(1, int(round(S.DAMAGE_BASE_MIN * S.GRAZE_MULTIPLIER))),
            dmg_graze_max=max(1, int(round(S.DAMAGE_BASE_MAX * S.GRAZE_MULTIPLIER))),
            dmg_crit_min=S.DAMAGE_BASE_MIN + S.CRIT_BONUS_DAMAGE,
            dmg_crit_max=S.DAMAGE_BASE_MAX + S.CRIT_BONUS_DAMAGE,
        )

    crit = _crit_for_context(bd.total, bd.flanked, bd.cover_type, bd.distance_tiles)
    graze = max(0, min(100 - bd.total, S.GRAZE_BAND_PERCENT))
    return ShotPreview(
        los=True, hit_chance=bd.total, crit_chance=crit, graze_band=graze,
        flanked=bd.flanked, cover_facing=bd.cover_type, distance_tiles=bd.distance_tiles,
        dmg_base_min=S.DAMAGE_BASE_MIN, dmg_base_max=S.DAMAGE_BASE_MAX,
        dmg_graze_min=max(1, int(round(S.DAMAGE_BASE_MIN * S.GRAZE_MULTIPLIER))),
        dmg_graze_max=max(1, int(round(S.DAMAGE_BASE_MAX * S.GRAZE_MULTIPLIER))),
        dmg_crit_min=S.DAMAGE_BASE_MIN + S.CRIT_BONUS_DAMAGE,
        dmg_crit_max=S.DAMAGE_BASE_MAX + S.CRIT_BONUS_DAMAGE,
    )

def resolve_shot(grid, shooter: Coord, target: Coord, rng: random.Random) -> ShotResult:
    pv = preview_probabilities(grid, shooter, target)
    if not pv.los:
        return ShotResult("blocked", roll=0, hit_chance=0, crit_chance=0, graze_band=0,
                          damage=0, flanked=False, cover_facing="full", distance_tiles=pv.distance_tiles)

    roll = rng.randint(1, 100)
    # Thresholds: crit <= hit <= hit+graze
    crit_th = pv.crit_chance
    hit_th  = pv.hit_chance
    graze_th = min(100, pv.hit_chance + pv.graze_band)

    # Base damage roll
    base = rng.randint(S.DAMAGE_BASE_MIN, S.DAMAGE_BASE_MAX)

    if roll <= crit_th:
        dmg = base + S.CRIT_BONUS_DAMAGE
        outcome: Outcome = "crit"
    elif roll <= hit_th:
        dmg = base
        outcome = "hit"
    elif roll <= graze_th:
        dmg = max(1, int(round(base * S.GRAZE_MULTIPLIER)))
        outcome = "graze"
    else:
        dmg = 0
        outcome = "miss"

    return ShotResult(outcome, roll, pv.hit_chance, pv.crit_chance, pv.graze_band,
                      dmg, pv.flanked, pv.cover_facing, pv.distance_tiles)
