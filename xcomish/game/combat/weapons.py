# game/combat/weapons.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional
from game import settings as S

RangeBand = Tuple[float, float, int]  # (min_inclusive, max_exclusive, modifier)

@dataclass(slots=True)
class WeaponSpec:
    key: str
    name: str
    aim_bonus: int = 0
    base_crit: int = 10
    range_bands: List[RangeBand] | None = None
    dmg_min: int = 3
    dmg_max: int = 5
    crit_bonus_damage: int = 2
    graze_multiplier: float = S.GRAZE_MULTIPLIER
    mag_size: int = 5
    crit_point_blank_bonus: int = S.CRIT_POINT_BLANK_BONUS

@dataclass(slots=True)
class Weapon:
    spec: WeaponSpec
    ammo: int

    @property
    def name(self) -> str: return self.spec.name
    @property
    def mag_size(self) -> int: return self.spec.mag_size

    def can_fire(self) -> bool:
        return self.ammo > 0

    def consume_round(self, n: int = 1) -> None:
        self.ammo = max(0, self.ammo - n)

    def reload_full(self) -> None:
        self.ammo = self.spec.mag_size

def _default_bands() -> List[RangeBand]:
    return list(S.RANGE_BANDS)

# Example blueprints
ASSAULT_RIFLE = WeaponSpec(
    key="ar", name="Assault Rifle",
    aim_bonus=0,
    base_crit=12,
    range_bands=_default_bands(),        # uses global defaults
    dmg_min=3, dmg_max=5,
    crit_bonus_damage=2,
    graze_multiplier=S.GRAZE_MULTIPLIER,
    mag_size=5,
)

SHOTGUN = WeaponSpec(
    key="sg", name="Shotgun",
    aim_bonus=-5,
    base_crit=20,
    range_bands=[(0.0, 2.0, +20), (2.0, 6.0, +5), (6.0, 9.0, -20), (9.0, 999.0, -45)],
    dmg_min=4, dmg_max=6,
    crit_bonus_damage=3,
    graze_multiplier=S.GRAZE_MULTIPLIER,
    mag_size=4,
    crit_point_blank_bonus=S.CRIT_POINT_BLANK_BONUS + 10,
)

WEAPON_INDEX: dict[str, WeaponSpec] = {
    "assault_rifle": ASSAULT_RIFLE,
    "shotgun": SHOTGUN,
}

def make_weapon(key: str = "assault_rifle") -> Weapon:
    spec = WEAPON_INDEX.get(key, ASSAULT_RIFLE)
    return Weapon(spec=spec, ammo=spec.mag_size)
