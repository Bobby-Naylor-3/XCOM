# game/core/clock.py
from __future__ import annotations
import pygame
from dataclasses import dataclass
from game.settings import FIXED_DT, MAX_STEPS, DT_CLAMP

@dataclass
class FixedClock:
    """Fixed timestep accumulator clock.
    tick() -> (steps, alpha), where:
    - steps: how many fixed updates to run this frame (0..MAX_STEPS)
    - alpha: interpolation factor [0,1) for rendering between states
    """
    accumulator: float = 0.0

    def __post_init__(self) -> None:
        self._clock = pygame.time.Clock()

    def tick(self) -> tuple[int, float]:
        # Real elapsed time since last tick, in seconds (clamped)
        dt = min(self._clock.tick(), DT_CLAMP * 1000) / 1000.0
        self.accumulator += dt

        steps = 0
        while self.accumulator >= FIXED_DT and steps < MAX_STEPS:
            self.accumulator -= FIXED_DT
            steps += 1

        alpha = self.accumulator / FIXED_DT if FIXED_DT > 0 else 0.0
        return steps, alpha
