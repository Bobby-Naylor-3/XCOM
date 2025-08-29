# game/combat/hit.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Iterable, Optional
import math

from game import settings as S
from game.world.cover import compute_tile_cover
from game.world.los import los_clear, facing_side, Coord

@dataclass(slots=True)
class HitBreakdown:
    base: int
    terms: list[tuple[str, int]] = field(default_factory=list)
    total: int = 0
    los: bool = False
    flanked: bool = False
    cover_type: str = "none"
    distance_tiles: float = 0.0

    def as_text(self) -> str:
        pieces = [f"{self.base} base"] + [f"{'+' if v>=0 else ''}{v} {k}" for k, v in self.terms]
        return f"{self.total}%  (" + ", ".join(pieces) + ")"

def _range_modifier(dist_tiles: float, range_bands: list[tuple[float, float, int]]) -> int:
    for lo, hi, mod in range_bands:
        if lo <= dist_tiles < hi:
            return mod
    return 0

def clamp(p: int) -> int:
    return max(S.HIT_CLAMP_MIN, min(S.HIT_CLAMP_MAX, p))

def compute_hit(
    grid,
    shooter: Coord,
    target: Coord,
    *,
    base_aim: int | None = None,
    range_bands: list[tuple[float, float, int]] | None = None
) -> HitBreakdown:
    """Return a full hit breakdown from shooter->target."""
    base = int(S.BASE_AIM_PERCENT if base_aim is None else base_aim)
    dx = target[0] - shooter[0]
    dy = target[1] - shooter[1]
    dist = math.hypot(dx, dy)

    bd = HitBreakdown(base=base, distance_tiles=dist)

    # Line of Fire
    bd.los = los_clear(grid, shooter, target)
    if not bd.los:
        bd.total = 0
        return bd

    # Cover & flanking
    cv = compute_tile_cover(grid, target[0], target[1], oob_is_full=True)
    side = facing_side(shooter, target)
    cover_type = cv[side]
    bd.cover_type = cover_type
    flanked = cover_type == "none"
    bd.flanked = flanked

    total = base

    # Range
    rb = range_bands if range_bands is not None else S.RANGE_BANDS
    rng = _range_modifier(dist, rb)
    if rng:
        bd.terms.append(("range", rng))
        total += rng

    # Cover or flank
    if flanked:
        if S.FLANK_BONUS:
            bd.terms.append(("flank", S.FLANK_BONUS))
            total += S.FLANK_BONUS
    else:
        if cover_type == "half" and S.COVER_HALF_PENALTY:
            bd.terms.append(("half cover", S.COVER_HALF_PENALTY))
            total += S.COVER_HALF_PENALTY
        elif cover_type == "full" and S.COVER_FULL_PENALTY:
            bd.terms.append(("full cover", S.COVER_FULL_PENALTY))
            total += S.COVER_FULL_PENALTY

    bd.total = clamp(int(round(total)))
    return bd
