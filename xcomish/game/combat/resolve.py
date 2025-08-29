# game/combat/resolve.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
import random
import math

from game import settings as S
from game.combat.hit import compute_hit
from game.combat.weapons import Weapon
from game.world.los import facing_side, Coord
from game.world.cover import compute_tile_cover

Outcome = Literal["blocked", "miss", "graze", "hit", "crit"]

@dataclass(slots=True)
class ShotPreview:
    los: bool
    hit_chance: int
    crit_chance: int        # effective crit (capped by hit)
    graze_band: int
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

def _crit_for_context(hit_total: int, flanked: bool, cover_facing: str, distance_tiles: float, wpn: Weapon) -> int:
    crit = wpn.spec.base_crit
    if flanked:
        crit += S.CRIT_FLANK_BONUS
    if cover_facing == "half":
        crit += S.CRIT_HALF_COVER_PENALTY
    elif cover_facing == "full":
        crit += S.CRIT_FULL_COVER_PENALTY
    if distance_tiles < 2.0:
        crit += wpn.spec.crit_point_blank_bonus
    crit = max(0, min(100, int(round(crit))))
    return min(hit_total, crit)  # can’t crit on a miss

def preview_probabilities(grid, shooter: Coord, target: Coord, *, weapon: Weapon) -> ShotPreview:
    base_aim = S.BASE_AIM_PERCENT + weapon.spec.aim_bonus
    bd = compute_hit(grid, shooter, target, base_aim=base_aim, range_bands=weapon.spec.range_bands or S.RANGE_BANDS)
    if not bd.los:
        return ShotPreview(
            los=False, hit_chance=0, crit_chance=0, graze_band=0,
            flanked=False, cover_facing="full", distance_tiles=bd.distance_tiles,
            dmg_base_min=weapon.spec.dmg_min, dmg_base_max=weapon.spec.dmg_max,
            dmg_graze_min=max(1, int(round(weapon.spec.dmg_min * weapon.spec.graze_multiplier))),
            dmg_graze_max=max(1, int(round(weapon.spec.dmg_max * weapon.spec.graze_multiplier))),
            dmg_crit_min=weapon.spec.dmg_min + weapon.spec.crit_bonus_damage,
            dmg_crit_max=weapon.spec.dmg_max + weapon.spec.crit_bonus_damage,
        )

    crit = _crit_for_context(bd.total, bd.flanked, bd.cover_type, bd.distance_tiles, weapon)
    graze = max(0, min(100 - bd.total, S.GRAZE_BAND_PERCENT))
    return ShotPreview(
        los=True, hit_chance=bd.total, crit_chance=crit, graze_band=graze,
        flanked=bd.flanked, cover_facing=bd.cover_type, distance_tiles=bd.distance_tiles,
        dmg_base_min=weapon.spec.dmg_min, dmg_base_max=weapon.spec.dmg_max,
        dmg_graze_min=max(1, int(round(weapon.spec.dmg_min * weapon.spec.graze_multiplier))),
        dmg_graze_max=max(1, int(round(weapon.spec.dmg_max * weapon.spec.graze_multiplier))),
        dmg_crit_min=weapon.spec.dmg_min + weapon.spec.crit_bonus_damage,
        dmg_crit_max=weapon.spec.dmg_max + weapon.spec.crit_bonus_damage,
    )

def resolve_shot(grid, shooter: Coord, target: Coord, rng: random.Random, *, weapon: Weapon) -> ShotResult:
    pv = preview_probabilities(grid, shooter, target, weapon=weapon)
    if not pv.los:
        return ShotResult("blocked", roll=0, hit_chance=0, crit_chance=0, graze_band=0,
                          damage=0, flanked=False, cover_facing="full", distance_tiles=pv.distance_tiles)

    roll = rng.randint(1, 100)
    crit_th = pv.crit_chance
    hit_th  = pv.hit_chance
    graze_th = min(100, pv.hit_chance + pv.graze_band)

    # Base damage roll
    base = rng.randint(weapon.spec.dmg_min, weapon.spec.dmg_max)

    if roll <= crit_th:
        dmg = base + weapon.spec.crit_bonus_damage
        outcome: Outcome = "crit"
    elif roll <= hit_th:
        dmg = base
        outcome = "hit"
    elif roll <= graze_th:
        dmg = max(1, int(round(base * weapon.spec.graze_multiplier)))
        outcome = "graze"
    else:
        dmg = 0
        outcome = "miss"

    return ShotResult(outcome, roll, pv.hit_chance, pv.crit_chance, pv.graze_band,
                      dmg, pv.flanked, pv.cover_facing, pv.distance_tiles)
