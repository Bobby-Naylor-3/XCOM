# game/scenes/tactical.py
from __future__ import annotations
import pygame
from dataclasses import dataclass, field
from game import settings
from game.world.grid import Grid
from game.entities.player import Player

@dataclass
class TacticalScene:
    """Simple tactical scene: renders grid + a single Player."""
    screen: pygame.Surface
    grid: Grid = field(default_factory=Grid)
    player: Player = field(init=False)

    def __post_init__(self) -> None:
        self.player = Player(self.grid)

    # Input is stubbed for future turns (movement, selection, etc.)
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def update(self, dt: float) -> None:
        # Future: resolve queued commands, animations, fog, pathing, etc.
        pass

    def draw(self, surface: pygame.Surface, alpha: float) -> None:
        surface.fill(settings.BG_COLOR)
        self.grid.draw_lines(surface)
        self.player.draw(surface, alpha=alpha)

        # Optional mouse tile highlight
        self.grid.draw_highlight(surface, pygame.mouse.get_pos())
