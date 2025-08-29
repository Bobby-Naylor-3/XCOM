# game/entities/enemy.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D

@dataclass(slots=True)
class Enemy:
    grid: Grid
    col: int
    row: int
    max_hp: int = 6
    hp: int = 6
    radius_px: int = max(6, settings.TILE_SIZE // 3)

    def is_dead(self) -> bool:
        return self.hp <= 0

    def apply_damage(self, dmg: int) -> None:
        self.hp = max(0, self.hp - max(0, int(dmg)))

    def draw(self, surface: pygame.Surface, camera: Camera2D, *, draw_hp_bar: bool = True) -> None:
        cx_w, cy_w = self.grid.center_px(self.col, self.row)
        cx_s, cy_s = camera.world_to_screen(cx_w, cy_w)
        pygame.draw.circle(surface, settings.ENEMY_COLOR, (int(cx_s), int(cy_s)), self.radius_px)

        if draw_hp_bar:
            # simple bar above the unit
            w = self.radius_px * 2
            h = 6
            x = int(cx_s - w // 2)
            y = int(cy_s - self.radius_px - 12)
            # back
            pygame.draw.rect(surface, (50, 15, 15), pygame.Rect(x, y, w, h))
            # fill
            if self.max_hp > 0:
                frac = self.hp / self.max_hp
            else:
                frac = 0
            fw = int(w * frac)
            pygame.draw.rect(surface, (220, 60, 60), pygame.Rect(x, y, fw, h))
            # border
            pygame.draw.rect(surface, (180, 180, 180), pygame.Rect(x, y, w, h), width=1)
