"""Generate the Mirai War Room — office-styled zones with diverse furniture."""
import json
import random

COLS = 45
ROWS = 35
VOID = 255
WALL = 0
FLOOR_INVESTOR = 7   # warm beige
FLOOR_CUSTOMER = 1   # blue
FLOOR_OPERATOR = 3   # green
FLOOR_ANALYST = 9    # gray
FLOOR_CONTRARIAN = 5 # warm

def make_grid():
    grid = [[VOID] * COLS for _ in range(ROWS)]
    for r in range(ROWS):
        for c in range(COLS):
            if r == 0 or r == ROWS-1 or c == 0 or c == COLS-1:
                grid[r][c] = WALL
            elif r == 16:
                grid[r][c] = WALL
            elif r < 16 and c == 15:
                grid[r][c] = WALL
            elif r < 16 and c == 30:
                grid[r][c] = WALL
            elif r > 16 and c == 22:
                grid[r][c] = WALL

    # Fill zone floors
    for r in range(1, 16):
        for c in range(1, 15): grid[r][c] = FLOOR_INVESTOR
    for r in range(1, 16):
        for c in range(16, 30): grid[r][c] = FLOOR_CUSTOMER
    for r in range(1, 16):
        for c in range(31, COLS-1): grid[r][c] = FLOOR_OPERATOR
    for r in range(17, ROWS-1):
        for c in range(1, 22): grid[r][c] = FLOOR_ANALYST
    for r in range(17, ROWS-1):
        for c in range(23, COLS-1): grid[r][c] = FLOOR_CONTRARIAN

    # Doorways
    for c in [7, 8]: grid[16][c] = FLOOR_INVESTOR
    for c in [22, 23]: grid[16][c] = FLOOR_CUSTOMER
    for c in [37, 38]: grid[16][c] = FLOOR_OPERATOR
    for r in [5, 6, 10, 11]:
        grid[r][15] = FLOOR_INVESTOR
        grid[r][30] = FLOOR_CUSTOMER
    for r in [22, 23, 28, 29]:
        grid[r][22] = FLOOR_ANALYST

    return grid

def add_workstation(furn, col, row, variant=0):
    """Add a desk + chair + PC workstation with variety."""
    desk_types = ["DESK_FRONT", "SMALL_TABLE_FRONT", "DESK_SIDE"]
    chair_types = ["CUSHIONED_CHAIR_FRONT", "WOODEN_CHAIR_FRONT", "CUSHIONED_BENCH"]

    if variant % 3 == 0:
        # Desk facing front + chair + PC
        furn.append({"type": "DESK_FRONT", "col": col, "row": row, "rotation": 0})
        furn.append({"type": random.choice(["CUSHIONED_CHAIR_FRONT", "WOODEN_CHAIR_FRONT"]), "col": col + 1, "row": row + 2, "rotation": 0})
        furn.append({"type": random.choice(["PC_FRONT_OFF", "PC_FRONT_ON_1", "PC_FRONT_ON_2"]), "col": col, "row": row, "rotation": 0})
    elif variant % 3 == 1:
        # Small table + bench
        furn.append({"type": "SMALL_TABLE_FRONT", "col": col, "row": row, "rotation": 0})
        furn.append({"type": "CUSHIONED_BENCH", "col": col, "row": row + 2, "rotation": 0})
    else:
        # Side desk + side chair
        furn.append({"type": "DESK_SIDE", "col": col, "row": row, "rotation": 0})
        furn.append({"type": random.choice(["WOODEN_CHAIR_SIDE", "CUSHIONED_CHAIR_SIDE"]), "col": col + 1, "row": row + 1, "rotation": 0})

def add_zone_decor(furn, zone_col_start, zone_col_end, zone_row_start, zone_row_end, zone_name):
    """Add decorative furniture to a zone for office atmosphere."""
    mid_col = (zone_col_start + zone_col_end) // 2

    # Bookshelves on top wall
    furn.append({"type": "DOUBLE_BOOKSHELF", "col": zone_col_start + 1, "row": zone_row_start, "rotation": 0})
    furn.append({"type": "BOOKSHELF", "col": zone_col_end - 3, "row": zone_row_start, "rotation": 0})

    # Paintings
    furn.append({"type": random.choice(["SMALL_PAINTING", "SMALL_PAINTING_2", "LARGE_PAINTING"]),
                 "col": mid_col, "row": zone_row_start, "rotation": 0})

    # Plants in corners
    furn.append({"type": random.choice(["PLANT", "PLANT_2", "LARGE_PLANT", "CACTUS"]),
                 "col": zone_col_start + 1, "row": zone_row_end - 2, "rotation": 0})
    furn.append({"type": random.choice(["PLANT", "PLANT_2", "HANGING_PLANT"]),
                 "col": zone_col_end - 2, "row": zone_row_start + 1, "rotation": 0})

    # Coffee/bin
    furn.append({"type": "COFFEE", "col": zone_col_end - 2, "row": zone_row_end - 2, "rotation": 0})
    furn.append({"type": "BIN", "col": zone_col_start + 1, "row": zone_row_end - 1, "rotation": 0})

def add_lounge_area(furn, col, row):
    """Add a sofa + coffee table lounge area."""
    furn.append({"type": "SOFA_FRONT", "col": col, "row": row, "rotation": 0})
    furn.append({"type": "COFFEE_TABLE", "col": col, "row": row + 1, "rotation": 0})
    furn.append({"type": "SOFA_BACK", "col": col, "row": row + 3, "rotation": 0})

def generate_layout():
    random.seed(42)  # Deterministic for reproducibility
    grid = make_grid()
    furn = []

    # ── Zone 1: INVESTORS (top-left, cols 1-14, rows 1-15) ──
    # 10 workstations in 2 columns
    for i in range(4):
        add_workstation(furn, 3, 2 + i * 3, variant=i)
    add_lounge_area(furn, 3, 13)  # Lounge instead of 5th desk
    for i in range(5):
        add_workstation(furn, 9, 2 + i * 3, variant=i + 4)
    # 9 workstations + 1 sofa seating = 10 seats
    furn.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 4, "row": 12, "rotation": 0})  # Extra chair near lounge
    add_zone_decor(furn, 1, 14, 1, 15, "Investors")

    # ── Zone 2: CUSTOMERS (top-middle, cols 16-29, rows 1-15) ──
    for i in range(5):
        add_workstation(furn, 17, 2 + i * 3, variant=i + 2)
    for i in range(4):
        add_workstation(furn, 24, 2 + i * 3, variant=i + 7)
    # Meeting table in corner
    furn.append({"type": "TABLE_FRONT", "col": 24, "row": 13, "rotation": 0})
    furn.append({"type": "WOODEN_CHAIR_FRONT", "col": 25, "row": 12, "rotation": 0})
    add_zone_decor(furn, 16, 29, 1, 15, "Customers")
    furn.append({"type": "WHITEBOARD", "col": 21, "row": 1, "rotation": 0})

    # ── Zone 3: OPERATORS (top-right, cols 31-43, rows 1-15) ──
    for i in range(5):
        add_workstation(furn, 32, 2 + i * 3, variant=i + 1)
    for i in range(4):
        add_workstation(furn, 38, 2 + i * 3, variant=i + 6)
    add_lounge_area(furn, 38, 13)
    furn.append({"type": "CUSHIONED_BENCH", "col": 39, "row": 12, "rotation": 0})
    add_zone_decor(furn, 31, 43, 1, 15, "Operators")
    furn.append({"type": "CLOCK", "col": 36, "row": 1, "rotation": 0})

    # ── Zone 4: ANALYSTS (bottom-left, cols 1-21, rows 17-33) ──
    for i in range(5):
        add_workstation(furn, 3, 18 + i * 3, variant=i + 3)
    for i in range(5):
        add_workstation(furn, 11, 18 + i * 3, variant=i + 8)
    add_zone_decor(furn, 1, 21, 17, 33, "Analysts")
    furn.append({"type": "WHITEBOARD", "col": 16, "row": 17, "rotation": 0})
    furn.append({"type": "POT", "col": 8, "row": 17, "rotation": 0})

    # ── Zone 5: CONTRARIANS (bottom-right, cols 23-43, rows 17-33) ──
    for i in range(4):
        add_workstation(furn, 24, 18 + i * 3, variant=i + 5)
    add_lounge_area(furn, 24, 30)
    furn.append({"type": "CUSHIONED_CHAIR_FRONT", "col": 25, "row": 29, "rotation": 0})
    for i in range(5):
        add_workstation(furn, 33, 18 + i * 3, variant=i + 10)
    add_zone_decor(furn, 23, 43, 17, 33, "Contrarians")
    furn.append({"type": "CLOCK", "col": 38, "row": 17, "rotation": 0})

    # ── Central corridor decorations ──
    furn.append({"type": "LARGE_PLANT", "col": 1, "row": 16, "rotation": 0})
    furn.append({"type": "PLANT_2", "col": 14, "row": 16, "rotation": 0})
    furn.append({"type": "CACTUS", "col": 29, "row": 16, "rotation": 0})
    furn.append({"type": "LARGE_PLANT", "col": COLS-2, "row": 16, "rotation": 0})

    tiles = []
    for row in grid:
        tiles.extend(row)

    layout = {
        "version": 1,
        "cols": COLS,
        "rows": ROWS,
        "tiles": tiles,
        "furniture": furn,
    }
    return layout

if __name__ == "__main__":
    layout = generate_layout()
    path = "public/assets/default-layout-2.json"
    with open(path, "w") as f:
        json.dump(layout, f)

    chairs = sum(1 for f in layout["furniture"] if "CHAIR" in f["type"] or "BENCH" in f["type"] or "SOFA" in f["type"])
    print(f"Generated: {COLS}x{ROWS}, {len(layout['furniture'])} items, ~{chairs} seats")
    print(f"Furniture mix: desks, PCs, sofas, coffee tables, plants, bookshelves, paintings, whiteboards, clocks")
    print(f"Saved to: {path}")
