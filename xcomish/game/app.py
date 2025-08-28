# game/app.py
from __future__ import annotations
import pygame
from game import settings
from game.core.clock import FixedClock
from game.scenes.tactical import TacticalScene

def main() -> None:
    pygame.init()
    pygame.display.set_caption(settings.WINDOW_TITLE)
    screen = pygame.display.set_mode(settings.SCREEN_SIZE)
    clock = FixedClock()

    scene = TacticalScene(screen)

    running = True
    while running:
        # -- Input --
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                scene.handle_event(event)

        # -- Fixed updates --
        steps, alpha = clock.tick()
        for _ in range(steps):
            scene.update(settings.FIXED_DT)

        # -- Render (interpolated) --
        scene.draw(screen, alpha)
        pygame.display.flip()

    pygame.quit()
