"""Generate the Mirai War Room — 7 zones in the style of original pixel-agents.

Uses the original's dense furniture placement style with mirrored variants,
PC_SIDE, SMALL_TABLE_SIDE, SOFA arrangements, and per-tile color tinting.
"""
import json
import random

COLS = 52
ROWS = 35
VOID = 255
WALL = 0
FLOOR_INVESTOR = 7
FLOOR_CUSTOMER = 1
FLOOR_OPERATOR = 3
FLOOR_ANALYST = 9
FLOOR_CONTRARIAN = 5
FLOOR_WILDCARD = 11
FLOOR_COUNCIL = 13

def make_grid():
    grid = [[VOID] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            if r == 0 or r == ROWS-1 or c == 0 or c == COLS-1:
                grid[r][c] = WALL
            elif r == 16:
                grid[r][c] = WALL
            elif r < 16 and c == 13: grid[r][c] = WALL
            elif r < 16 and c == 26: grid[r][c] = WALL
            elif r < 16 and c == 39: grid[r][c] = WALL
            elif r > 16 and c == 13: grid[r][c] = WALL
            elif r > 16 and c == 26: grid[r][c] = WALL

    for r in range(1, 16):
        for c in range(1, 13): grid[r][c] = FLOOR_INVESTOR
        for c in range(14, 26): grid[r][c] = FLOOR_CUSTOMER
        for c in range(27, 39): grid[r][c] = FLOOR_OPERATOR
        for c in range(40, COLS-1): grid[r][c] = FLOOR_COUNCIL
    for r in range(17, ROWS-1):
        for c in range(1, 13): grid[r][c] = FLOOR_ANALYST
        for c in range(14, 26): grid[r][c] = FLOOR_CONTRARIAN
        for c in range(27, COLS-1): grid[r][c] = FLOOR_WILDCARD

    # Doorways
    for r in [5, 6, 10, 11]:
        grid[r][13] = FLOOR_INVESTOR
        grid[r][26] = FLOOR_CUSTOMER
        grid[r][39] = FLOOR_OPERATOR
    for r in [22, 23, 28, 29]:
        grid[r][13] = FLOOR_ANALYST
        grid[r][26] = FLOOR_CONTRARIAN
    return grid


def tile_colors(grid):
    """Per-tile color tinting like the original."""
    hues = {
        FLOOR_INVESTOR: {"h": 35, "s": 25, "b": 8, "c": 35},
        FLOOR_CUSTOMER: {"h": 210, "s": 20, "b": 6, "c": 30},
        FLOOR_OPERATOR: {"h": 130, "s": 18, "b": 6, "c": 30},
        FLOOR_ANALYST: {"h": 0, "s": 0, "b": 4, "c": 25},
        FLOOR_CONTRARIAN: {"h": 15, "s": 22, "b": 8, "c": 35},
        FLOOR_WILDCARD: {"h": 275, "s": 15, "b": 6, "c": 28},
        FLOOR_COUNCIL: {"h": 42, "s": 28, "b": 10, "c": 40},
        WALL: {"h": 214, "s": 30, "b": -100, "c": -55},
    }
    colors = []
    for r, row in enumerate(grid):
        for tile in row:
            if tile in hues:
                b = hues[tile]
                colors.append({"h": b["h"]+random.randint(-4,4), "s": b["s"]+random.randint(-3,3), "b": b["b"]+random.randint(-2,2), "c": b["c"]+random.randint(-4,4)})
            else:
                colors.append(None)
    return colors


def gen():
    random.seed(42)
    grid = make_grid()
    f = []

    # ── Helper: original-style desk pair (facing each other) ──
    def desk_pair(col, row):
        f.append({"type": "WOODEN_CHAIR_SIDE", "col": col, "row": row, "rotation": 0})
        f.append({"type": "PC_SIDE", "col": col+1, "row": row, "rotation": 0})
        f.append({"type": "WOODEN_CHAIR_SIDE:left", "col": col+4, "row": row, "rotation": 0})
        f.append({"type": "PC_SIDE:left", "col": col+3, "row": row, "rotation": 0})

    def desk_row(col, row):
        f.append({"type": "DESK_FRONT", "col": col, "row": row, "rotation": 0})
        f.append({"type": "PC_FRONT_OFF", "col": col, "row": row, "rotation": 0})
        f.append({"type": "CUSHIONED_BENCH", "col": col, "row": row+2, "rotation": 0})

    def sofa_corner(col, row):
        f.append({"type": "SOFA_SIDE", "col": col, "row": row, "rotation": 0})
        f.append({"type": "SOFA_FRONT", "col": col+1, "row": row-1, "rotation": 0})
        f.append({"type": "COFFEE_TABLE", "col": col+1, "row": row, "rotation": 0})
        f.append({"type": "SOFA_SIDE:left", "col": col+3, "row": row, "rotation": 0})
        f.append({"type": "SOFA_BACK", "col": col+1, "row": row+1, "rotation": 0})

    # ═══ INVESTORS (1-12, 1-15) ═══
    desk_pair(2, 3)
    desk_pair(2, 5)
    desk_row(2, 8)
    desk_row(7, 8)
    sofa_corner(3, 13)
    f.append({"type": "DOUBLE_BOOKSHELF", "col": 1, "row": 1, "rotation": 0})
    f.append({"type": "DOUBLE_BOOKSHELF", "col": 7, "row": 1, "rotation": 0})
    f.append({"type": "HANGING_PLANT", "col": 5, "row": 1, "rotation": 0})
    f.append({"type": "LARGE_PAINTING", "col": 10, "row": 1, "rotation": 0})
    f.append({"type": "COFFEE", "col": 11, "row": 14, "rotation": 0})
    f.append({"type": "PLANT_2", "col": 1, "row": 14, "rotation": 0})

    # ═══ CUSTOMERS (14-25, 1-15) ═══
    desk_pair(15, 3)
    desk_pair(15, 5)
    desk_row(15, 8)
    desk_row(20, 8)
    f.append({"type": "TABLE_FRONT", "col": 18, "row": 12, "rotation": 0})
    f.append({"type": "WOODEN_CHAIR_SIDE", "col": 17, "row": 13, "rotation": 0})
    f.append({"type": "WOODEN_CHAIR_SIDE:left", "col": 20, "row": 13, "rotation": 0})
    f.append({"type": "WHITEBOARD", "col": 17, "row": 1, "rotation": 0})
    f.append({"type": "WHITEBOARD", "col": 22, "row": 1, "rotation": 0})
    f.append({"type": "HANGING_PLANT", "col": 14, "row": 1, "rotation": 0})
    f.append({"type": "SMALL_PAINTING", "col": 20, "row": 1, "rotation": 0})
    f.append({"type": "BIN", "col": 24, "row": 14, "rotation": 0})
    f.append({"type": "PLANT", "col": 24, "row": 1, "rotation": 0})

    # ═══ OPERATORS (27-38, 1-15) ═══
    desk_pair(28, 3)
    desk_pair(28, 5)
    desk_pair(28, 7)
    desk_pair(28, 9)
    f.append({"type": "SMALL_TABLE_FRONT", "col": 33, "row": 3, "rotation": 0})
    f.append({"type": "CUSHIONED_BENCH", "col": 33, "row": 5, "rotation": 0})
    f.append({"type": "SMALL_TABLE_FRONT", "col": 33, "row": 7, "rotation": 0})
    f.append({"type": "CUSHIONED_BENCH", "col": 33, "row": 9, "rotation": 0})
    f.append({"type": "CLOCK", "col": 32, "row": 1, "rotation": 0})
    f.append({"type": "COFFEE", "col": 37, "row": 1, "rotation": 0})
    f.append({"type": "PLANT_2", "col": 27, "row": 1, "rotation": 0})
    f.append({"type": "SMALL_PAINTING_2", "col": 35, "row": 1, "rotation": 0})
    f.append({"type": "BIN", "col": 37, "row": 14, "rotation": 0})

    # ═══ COUNCIL (40-50, 1-15) ═══
    f.append({"type": "TABLE_FRONT", "col": 43, "row": 5, "rotation": 0})
    f.append({"type": "TABLE_FRONT", "col": 43, "row": 8, "rotation": 0})
    f.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 42, "row": 7, "rotation": 0})
    f.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 45, "row": 7, "rotation": 0})
    f.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 42, "row": 9, "rotation": 0})
    f.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 45, "row": 9, "rotation": 0})
    sofa_corner(41, 13)
    f.append({"type": "LARGE_PAINTING", "col": 44, "row": 1, "rotation": 0})
    f.append({"type": "DOUBLE_BOOKSHELF", "col": 40, "row": 1, "rotation": 0})
    f.append({"type": "SMALL_PAINTING_2", "col": 48, "row": 1, "rotation": 0})
    f.append({"type": "LARGE_PLANT", "col": 49, "row": 1, "rotation": 0})
    f.append({"type": "PLANT_2", "col": 40, "row": 14, "rotation": 0})

    # ═══ ANALYSTS (1-12, 17-33) ═══
    desk_pair(2, 19)
    desk_pair(2, 21)
    desk_row(2, 24)
    desk_row(7, 24)
    f.append({"type": "CUSHIONED_BENCH", "col": 2, "row": 31, "rotation": 0})
    f.append({"type": "DOUBLE_BOOKSHELF", "col": 1, "row": 17, "rotation": 0})
    f.append({"type": "BOOKSHELF", "col": 5, "row": 17, "rotation": 0})
    f.append({"type": "DOUBLE_BOOKSHELF", "col": 8, "row": 17, "rotation": 0})
    f.append({"type": "SMALL_PAINTING", "col": 4, "row": 17, "rotation": 0})
    f.append({"type": "PLANT_2", "col": 1, "row": 32, "rotation": 0})
    f.append({"type": "LARGE_PLANT", "col": 11, "row": 32, "rotation": 0})
    f.append({"type": "COFFEE", "col": 11, "row": 18, "rotation": 0})
    f.append({"type": "POT", "col": 6, "row": 32, "rotation": 0})

    # ═══ CONTRARIANS (14-25, 17-33) ═══
    f.append({"type": "TABLE_FRONT", "col": 18, "row": 20, "rotation": 0})
    f.append({"type": "WOODEN_CHAIR_SIDE", "col": 17, "row": 21, "rotation": 0})
    f.append({"type": "WOODEN_CHAIR_SIDE:left", "col": 20, "row": 21, "rotation": 0})
    desk_pair(15, 24)
    desk_pair(15, 26)
    desk_row(15, 29)
    desk_row(21, 29)
    f.append({"type": "WHITEBOARD", "col": 16, "row": 17, "rotation": 0})
    f.append({"type": "WHITEBOARD", "col": 22, "row": 17, "rotation": 0})
    f.append({"type": "CLOCK", "col": 19, "row": 17, "rotation": 0})
    f.append({"type": "BIN", "col": 14, "row": 32, "rotation": 0})

    # ═══ WILD CARD (27-50, 17-33) ═══
    desk_pair(28, 19)
    desk_pair(28, 21)
    desk_pair(35, 19)
    desk_pair(35, 21)
    desk_row(28, 25)
    desk_row(34, 25)
    desk_row(40, 25)
    sofa_corner(42, 30)
    f.append({"type": "SMALL_TABLE_FRONT", "col": 28, "row": 30, "rotation": 0})
    f.append({"type": "COFFEE", "col": 28, "row": 31, "rotation": 0})
    f.append({"type": "LARGE_PAINTING", "col": 36, "row": 17, "rotation": 0})
    f.append({"type": "BOOKSHELF", "col": 46, "row": 17, "rotation": 0})
    f.append({"type": "HANGING_PLANT", "col": 38, "row": 17, "rotation": 0})
    f.append({"type": "SMALL_PAINTING_2", "col": 32, "row": 17, "rotation": 0})
    f.append({"type": "CACTUS", "col": 49, "row": 18, "rotation": 0})
    f.append({"type": "PLANT", "col": 27, "row": 32, "rotation": 0})
    f.append({"type": "PLANT_2", "col": 49, "row": 32, "rotation": 0})
    f.append({"type": "BIN", "col": 49, "row": 30, "rotation": 0})
    f.append({"type": "SMALL_PAINTING", "col": 43, "row": 17, "rotation": 0})

    tiles = []
    for row in grid:
        tiles.extend(row)

    return {
        "version": 1,
        "cols": COLS,
        "rows": ROWS,
        "tiles": tiles,
        "furniture": f,
        "tileColors": tile_colors(grid),
    }


if __name__ == "__main__":
    layout = gen()
    path = "public/assets/default-layout-2.json"
    with open(path, "w") as f:
        json.dump(layout, f)

    chairs = sum(1 for x in layout["furniture"] if "CHAIR" in x["type"] or "BENCH" in x["type"] or "SOFA" in x["type"])
    print(f"Generated: {COLS}x{ROWS}, {len(layout['furniture'])} items, ~{chairs} seats")
    print(f"tileColors: {sum(1 for c in layout['tileColors'] if c)} colored tiles")
    print(f"Saved to: {path}")
