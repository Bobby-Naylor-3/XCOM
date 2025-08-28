# game/entities/player.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game import settings
from game.world.grid import Grid
from game.world.camera import Camera2D

@dataclass(slots=True)
class Player:
    grid: Grid
    col: int = 3
    row: int = 3
    radius_px: int = max(6, settings.TILE_SIZE // 3)

    def draw(self, surface: pygame.Surface, camera: Camera2D, alpha: float = 0.0) -> None:
        cx_w, cy_w = self.grid.center_px(self.col, self.row)
        cx_s, cy_s = camera.world_to_screen(cx_w, cy_w)
        pygame.draw.circle(surface, settings.PLAYER_COLOR, (cx_s, cy_s), self.radius_px)

    # game/entities/player.py  (add this method)
    def draw_selected(self, surface: pygame.Surface, camera, alpha: float = 0.0) -> None:
        cx_w, cy_w = self.grid.center_px(self.col, self.row)
        cx_s, cy_s = camera.world_to_screen(cx_w, cy_w)
        ring_radius = int(self.radius_px * 1.1)
        # Draw a soft ring (two outlines)
        import pygame
        pygame.draw.circle(surface, (0, 200, 255), (cx_s, cy_s), ring_radius, width=2)
        pygame.draw.circle(surface, (0, 120, 200), (cx_s, cy_s), ring_radius + 3, width=1)

