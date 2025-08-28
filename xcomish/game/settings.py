# game/settings.py
from __future__ import annotations

# Window / render
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
SCREEN_SIZE: tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOW_TITLE: str = "XCOMish - Grid + Player (VS01)"

# Grid
TILE_SIZE: int = 64
GRID_COLS: int = SCREEN_WIDTH // TILE_SIZE
GRID_ROWS: int = SCREEN_HEIGHT // TILE_SIZE

# Timestep (fixed update loop)
FIXED_DT: float = 1.0 / 60.0      # 60 Hz simulation
MAX_STEPS: int = 5                # prevent spiral of death
DT_CLAMP: float = 0.25            # clamp huge spikes (250ms)
EPS: float = max(1, TILE_SIZE // 64)  # epsilon tied to tile size

# Colors
BG_COLOR: tuple[int, int, int] = (15, 15, 20)
GRID_COLOR: tuple[int, int, int] = (45, 45, 60)
GRID_HILITE: tuple[int, int, int] = (70, 70, 100)
PLAYER_COLOR: tuple[int, int, int] = (220, 220, 40)
