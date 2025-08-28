# game/entities/player.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game import settings
from game.world.grid import Grid

@dataclass(slots=True)
class Player:
    """Grid-locked player placeholder. No movement yet; just render-ready."""
    grid: Grid
    col: int = 3
    row: int = 3
    radius_px: int = max(6, settings.TILE_SIZE // 3)

    def draw(self, surface: pygame.Surface, alpha: float = 0.0) -> None:
        # Future: use alpha for interpolating between last/next positions.
        cx, cy = self.grid.center_px(self.col, self.row)
        pygame.draw.circle(surface, settings.PLAYER_COLOR, (cx, cy), self.radius_px)
