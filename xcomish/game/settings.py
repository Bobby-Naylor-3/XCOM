# game/settings.py
from __future__ import annotations

# Window / render
SCREEN_WIDTH: int = 1280
SCREEN_HEIGHT: int = 720
SCREEN_SIZE: tuple[int, int] = (SCREEN_WIDTH, SCREEN_HEIGHT)
WINDOW_TITLE: str = "XCOMish - Grid + Player (VS01)"

# Grid (tile size stays the same)
TILE_SIZE: int = 64

# WORLD DIMENSIONS (in tiles) — bigger than the screen so you can pan
WORLD_COLS: int = 60
WORLD_ROWS: int = 40

# Derive visible grid size from screen (used for quick calcs, not world bounds)
GRID_COLS: int = SCREEN_WIDTH // TILE_SIZE
GRID_ROWS: int = SCREEN_HEIGHT // TILE_SIZE

# Timestep (fixed update loop)
FIXED_DT: float = 1.0 / 60.0
MAX_STEPS: int = 5
DT_CLAMP: float = 0.25
EPS: float = max(1, TILE_SIZE // 64)

# Camera
CAMERA_PAN_SPEED: float = 800.0      # px/sec
CAMERA_FAST_MULT: float = 2.0        # hold Shift to go faster
MOUSE_DRAG_BUTTONS: tuple[int, ...] = (2, 3)  # middle or right

# Colors
BG_COLOR: tuple[int, int, int] = (15, 15, 20)
GRID_COLOR: tuple[int, int, int] = (45, 45, 60)
GRID_HILITE: tuple[int, int, int] = (70, 70, 100)
PLAYER_COLOR: tuple[int, int, int] = (220, 220, 40)

# Movement (tiles)
MOVE_RANGE_1: int = 8      # one action
MOVE_RANGE_2: int = 16     # dash (two actions)

# Overlay colors (RGBA for semi-transparency)
RANGE1_RGBA: tuple[int, int, int, int] = (0, 255, 255, 70)    # cyan
RANGE2_RGBA: tuple[int, int, int, int] = (255, 255, 0, 50)    # yellow
PATH_RGBA:   tuple[int, int, int, int] = (255, 255, 255, 220) # hover path
PLAN_RGBA:   tuple[int, int, int, int] = (0, 220, 180, 235)   # planned path (teal-ish)
SEL_RGBA:    tuple[int, int, int, int] = (0, 200, 255, 200)   # selection ring

# HUD / labels
HUD_BG_RGBA: tuple[int, int, int, int] = (0, 0, 0, 150)
HUD_TEXT_RGB: tuple[int, int, int] = (240, 240, 240)
HUD_FONT_SIZE: int = 20

# Turn / actions
ACTIONS_PER_TURN: int = 2

# Movement speed (tiles per second)
PLAYER_MOVE_SPEED_TPS: float = 8.0

# Obstacles (render)
OBSTACLE_RGBA: tuple[int, int, int, int] = (160, 40, 40, 160)  # filled red-ish w/ alpha
OBSTACLE_BORDER_RGB: tuple[int, int, int] = (220, 80, 80)

# HUD hint when editing obstacles
OBSTACLE_EDIT_HINT_RGBA: tuple[int, int, int, int] = (30, 30, 30, 180)

# Cover visuals
COVER_FULL_RGB: tuple[int, int, int] = (80, 220, 120)      # full (XCOM: green-ish)
COVER_HALF_RGB: tuple[int, int, int] = (255, 220, 0)       # half (XCOM: yellow-ish)
COVER_DIM_RGB:  tuple[int, int, int] = (160, 160, 160)     # dim for non-focused tiles
COVER_ALPHA:    int = 220
COVER_MARGIN:   int = 6     # inset from tile edge (px)
COVER_THICK:    int = 6     # thickness of the pip polygon (px)
COVER_OOB_IS_FULL: bool = True  # treat map edge as full cover on that side

# Enemies
ENEMY_COLOR: tuple[int, int, int] = (220, 60, 60)

# Line of Fire overlay
LOF_CLEAR_RGBA: tuple[int, int, int, int]  = (0, 255, 0, 180)
LOF_BLOCKED_RGBA: tuple[int, int, int, int] = (255, 60, 60, 180)

# Fog of War
SIGHT_RADIUS_TILES: int = 12
FOG_SOFT_RGBA: tuple[int, int, int, int] = (0, 0, 0, 140)  # explored-not-visible
FOG_HARD_RGBA: tuple[int, int, int, int] = (0, 0, 0, 220)  # never seen

# --- Combat / Aim ---
BASE_AIM_PERCENT: int = 65          # soldier's base aim
HIT_CLAMP_MIN: int = 5
HIT_CLAMP_MAX: int = 95

# Cover modifiers (to shooter's aim)
COVER_HALF_PENALTY: int = -20
COVER_FULL_PENALTY: int = -40
FLANK_BONUS: int = +30              # granted when target is flanked (cover side not facing shooter)

# Range bands (euclidean tiles). Each = (min_inclusive, max_exclusive, modifier)
RANGE_BANDS: list[tuple[float, float, int]] = [
    (0.0, 2.0, +10),   # point-blank nudge
    (2.0, 8.0, 0),     # optimal
    (8.0, 12.0, -10),  # far
    (12.0, 999.0, -25) # extreme
]

# --- Combat / Aim (existing from last step is fine) ---
# BASE_AIM_PERCENT, HIT_CLAMP_MIN/MAX, COVER_* penalties, FLANK_BONUS, RANGE_BANDS

# --- Combat / Crit & Graze ---
BASE_CRIT_PERCENT: int = 10
CRIT_HALF_COVER_PENALTY: int = -10
CRIT_FULL_COVER_PENALTY: int = -25
CRIT_FLANK_BONUS: int = +20
CRIT_POINT_BLANK_BONUS: int = +15   # distance < 2 tiles

GRAZE_BAND_PERCENT: int = 20        # band above hit% that counts as graze instead of a full miss

# --- Damage model ---
DAMAGE_BASE_MIN: int = 3
DAMAGE_BASE_MAX: int = 5
CRIT_BONUS_DAMAGE: int = 2          # added to rolled base on crit
GRAZE_MULTIPLIER: float = 0.5       # graze does 50% (min 1 dmg if >0 base)

# --- RNG (optional seed; None = random) ---
RNG_SEED: int | None = None

# --- Actions for combat ---
FIRE_ACTION_COST: int = 1
RELOAD_ACTION_COST: int = 1
