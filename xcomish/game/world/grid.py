# game/world/grid.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game import settings

@dataclass(slots=True)
class Grid:
    cols: int = settings.GRID_COLS
    rows: int = settings.GRID_ROWS
    tile_size: int = settings.TILE_SIZE

    def to_px(self, col: int, row: int) -> tuple[int, int]:
        """Top-left pixel of a tile."""
        return col * self.tile_size, row * self.tile_size

    def center_px(self, col: int, row: int) -> tuple[int, int]:
        x, y = self.to_px(col, row)
        half = self.tile_size // 2
        return x + half, y + half

    def from_px(self, x: int, y: int) -> tuple[int, int]:
        return x // self.tile_size, y // self.tile_size

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def draw_lines(self, surface: pygame.Surface) -> None:
        w, h = surface.get_size()
        color = settings.GRID_COLOR
        ts = self.tile_size

        # Verticals
        for c in range(0, w + 1, ts):
            pygame.draw.line(surface, color, (c, 0), (c, h), 1)

        # Horizontals
        for r in range(0, h + 1, ts):
            pygame.draw.line(surface, color, (0, r), (w, r), 1)

    def draw_highlight(self, surface: pygame.Surface, mouse_pos: tuple[int, int]) -> None:
        col, row = self.from_px(*mouse_pos)
        if not self.in_bounds(col, row):
            return
        x, y = self.to_px(col, row)
        rect = pygame.Rect(x, y, self.tile_size, self.tile_size)
        pygame.draw.rect(surface, settings.GRID_HILITE, rect, width=2)
