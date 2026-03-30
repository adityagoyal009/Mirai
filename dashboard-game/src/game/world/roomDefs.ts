// ---------------------------------------------------------------------------
// roomDefs.ts — Data-driven room definitions for the Mirai War Room
// ---------------------------------------------------------------------------
// All spatial values are in tiles. One tile = 32 px.
// LINEAR left-to-right layout: Lobby -> Library -> Council -> Marketplace
//   -> Time Room -> Archive, connected by horizontal corridors.
// ---------------------------------------------------------------------------

export const TILE = 32;

// ---- Directional helpers --------------------------------------------------

export type Direction = 'up' | 'down' | 'left' | 'right';

// ---- Sub-definition interfaces --------------------------------------------

export interface DoorDef {
  /** Tile coordinate of the left-most (or top-most) door tile in local room space. */
  localTile: { x: number; y: number };
  /** Room id this door leads to. */
  targetRoomId: string;
  /** Tile the player should appear at when entering the target room. */
  targetTile: { x: number; y: number };
  /** Width of the door opening measured in tiles (usually 4 for horizontal doors). */
  width: number;
  /** Which wall the door sits on. */
  direction: Direction;
}

export interface NpcSpawnDef {
  id: string;
  /** Spritesheet key, e.g. 'char_001'. */
  skin: string;
  /** Tile position inside the room (local coords). */
  tile: { x: number; y: number };
  type: 'static' | 'dynamic';
  caption?: string;
  dialogId?: string;
  facing?: Direction;
}

export interface FurnitureDef {
  /** Top-left tile of the furniture piece (local coords). */
  tile: { x: number; y: number };
  /** Key used in Phaser image loader, e.g. 'DESK_FRONT'. */
  spriteKey: string;
  /** Whether the player collides with this piece. */
  collidable: boolean;
  /** Display scale (default 2: 16px source -> 32px rendered). */
  scale?: number;
  /** Render depth (default 3). */
  depth?: number;
}

export interface RoomDef {
  id: string;
  label: string;
  /** Room dimensions in tiles. */
  width: number;
  height: number;
  /** Top-left corner of the room in the world tile grid. */
  worldOffset: { x: number; y: number };
  /** Hex colour used to fill the floor area (fallback). */
  floorColor: number;
  /** Hex colour used to draw walls (fallback). */
  wallColor: number;
  /** Sprite key for repeating floor tile, e.g. 'floor_0'. */
  floorTile?: string;
  doors: DoorDef[];
  staticNpcs: NpcSpawnDef[];
  furniture: FurnitureDef[];
  /** Maps this room to a Mirai pipeline phase (used by WorldScene). */
  phase?: string;
  /** Default player spawn point in local tile coords. */
  spawnPoint?: { x: number; y: number };
}

// ---------------------------------------------------------------------------
// LINEAR room layout — all rooms placed left to right at y = 0
// ---------------------------------------------------------------------------
//
//  x:  0         16 19          39 42       58 61              85 88       104 107      123
//      +----------+--+-----------+--+--------+--+---------------+--+--------+--+---------+
//  y=0 |  LOBBY   |C1| LIBRARY   |C2| COUNCIL|C3| MARKETPLACE   |C4|TIME_RM |C5| ARCHIVE |
//      | 16x16    |  | 20x16     |  | 16x16  |  | 24x16         |  | 16x16  |  | 16x16   |
//      +----------+--+-----------+--+--------+--+---------------+--+--------+--+---------+
//
// Corridors are 3 tiles wide, 4 tiles tall, vertically centered (y offset = 6).
// ---------------------------------------------------------------------------

// ---- Corridor: Lobby <-> Library ------------------------------------------

const corridor_lobby_library: RoomDef = {
  id: 'corridor_lobby_library',
  label: '',
  width: 3,
  height: 4,
  worldOffset: { x: 16, y: 6 },
  floorColor: 0x2c2c3e,
  wallColor: 0x444466,
  floorTile: 'floor_0',
  doors: [
    {
      localTile: { x: 0, y: 0 },
      targetRoomId: 'lobby',
      targetTile: { x: 14, y: 7 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 2, y: 0 },
      targetRoomId: 'library',
      targetTile: { x: 1, y: 7 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [],
};

// ---- Corridor: Library <-> Council ----------------------------------------

const corridor_library_council: RoomDef = {
  id: 'corridor_library_council',
  label: '',
  width: 3,
  height: 4,
  worldOffset: { x: 39, y: 6 },
  floorColor: 0x2c2c3e,
  wallColor: 0x444466,
  floorTile: 'floor_0',
  doors: [
    {
      localTile: { x: 0, y: 0 },
      targetRoomId: 'library',
      targetTile: { x: 18, y: 7 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 2, y: 0 },
      targetRoomId: 'council',
      targetTile: { x: 1, y: 7 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [],
};

// ---- Corridor: Council <-> Marketplace ------------------------------------

const corridor_council_marketplace: RoomDef = {
  id: 'corridor_council_marketplace',
  label: '',
  width: 3,
  height: 4,
  worldOffset: { x: 58, y: 6 },
  floorColor: 0x2c2c3e,
  wallColor: 0x444466,
  floorTile: 'floor_0',
  doors: [
    {
      localTile: { x: 0, y: 0 },
      targetRoomId: 'council',
      targetTile: { x: 14, y: 7 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 2, y: 0 },
      targetRoomId: 'marketplace',
      targetTile: { x: 1, y: 7 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [],
};

// ---- Corridor: Marketplace <-> Time Room ----------------------------------

const corridor_marketplace_timeroom: RoomDef = {
  id: 'corridor_marketplace_timeroom',
  label: '',
  width: 3,
  height: 4,
  worldOffset: { x: 85, y: 6 },
  floorColor: 0x2c2c3e,
  wallColor: 0x444466,
  floorTile: 'floor_0',
  doors: [
    {
      localTile: { x: 0, y: 0 },
      targetRoomId: 'marketplace',
      targetTile: { x: 22, y: 7 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 2, y: 0 },
      targetRoomId: 'time_room',
      targetTile: { x: 1, y: 7 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [],
};

// ---- Corridor: Time Room <-> Archive --------------------------------------

const corridor_timeroom_archive: RoomDef = {
  id: 'corridor_timeroom_archive',
  label: '',
  width: 3,
  height: 4,
  worldOffset: { x: 104, y: 6 },
  floorColor: 0x2c2c3e,
  wallColor: 0x444466,
  floorTile: 'floor_0',
  doors: [
    {
      localTile: { x: 0, y: 0 },
      targetRoomId: 'time_room',
      targetTile: { x: 14, y: 7 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 2, y: 0 },
      targetRoomId: 'archive',
      targetTile: { x: 1, y: 7 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [],
};

// ---------------------------------------------------------------------------
// Main rooms
// ---------------------------------------------------------------------------

const lobby: RoomDef = {
  id: 'lobby',
  label: 'Lobby',
  width: 16,
  height: 16,
  worldOffset: { x: 0, y: 0 },
  floorColor: 0x3b3b5c,
  wallColor: 0x555577,
  floorTile: 'floor_1',
  spawnPoint: { x: 8, y: 10 },
  doors: [
    {
      // right wall -> corridor to library
      localTile: { x: 15, y: 6 },
      targetRoomId: 'corridor_lobby_library',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [
    {
      id: 'npc_intake_desk',
      skin: 'char_001',
      tile: { x: 8, y: 3 },
      type: 'static',
      caption: 'Intake Clerk',
      dialogId: 'intake_welcome',
      facing: 'down',
    },
  ],
  furniture: [
    // -- Reception desk (wide, NPC sits behind it) --
    { tile: { x: 7, y: 4 }, spriteKey: 'DESK_FRONT', collidable: true },
    { tile: { x: 9, y: 4 }, spriteKey: 'DESK_FRONT', collidable: true },
    { tile: { x: 10, y: 4 }, spriteKey: 'PC_FRONT_ON_1', collidable: true },
    // -- Visitor chair facing the desk --
    { tile: { x: 8, y: 6 }, spriteKey: 'CUSHIONED_CHAIR_BACK', collidable: false },
    // -- Waiting area (left side: sofas + coffee table) --
    { tile: { x: 2, y: 5 }, spriteKey: 'SOFA_FRONT', collidable: true },
    { tile: { x: 2, y: 7 }, spriteKey: 'COFFEE_TABLE', collidable: true },
    { tile: { x: 2, y: 9 }, spriteKey: 'SOFA_FRONT', collidable: true },
    { tile: { x: 3, y: 7 }, spriteKey: 'COFFEE', collidable: false },
    // -- Plants along left wall --
    { tile: { x: 1, y: 4 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 1, y: 10 }, spriteKey: 'PLANT_2', collidable: false },
    // -- Wall decorations (top) --
    { tile: { x: 3, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 7, y: 1 }, spriteKey: 'SMALL_PAINTING', collidable: false },
    { tile: { x: 10, y: 1 }, spriteKey: 'SMALL_PAINTING_2', collidable: false },
    { tile: { x: 13, y: 1 }, spriteKey: 'CLOCK', collidable: false },
    // -- Right side decor --
    { tile: { x: 14, y: 2 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 14, y: 12 }, spriteKey: 'LARGE_PLANT', collidable: true },
    // -- Bottom waiting benches --
    { tile: { x: 4, y: 13 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 8, y: 13 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    // -- Bottom corners --
    { tile: { x: 1, y: 13 }, spriteKey: 'POT', collidable: false },
    { tile: { x: 13, y: 13 }, spriteKey: 'BIN', collidable: false },
    { tile: { x: 12, y: 1 }, spriteKey: 'CACTUS', collidable: false },
  ],
  phase: 'intake',
};

const library: RoomDef = {
  id: 'library',
  label: 'Library',
  width: 20,
  height: 16,
  worldOffset: { x: 19, y: 0 },
  floorColor: 0x2e3d2e,
  wallColor: 0x4a5e4a,
  floorTile: 'floor_3',
  doors: [
    {
      localTile: { x: 0, y: 6 },
      targetRoomId: 'corridor_lobby_library',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'left',
    },
    {
      localTile: { x: 19, y: 6 },
      targetRoomId: 'corridor_library_council',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [
    // -- Left wall: bookshelf column (clear of door at y=6-9) --
    { tile: { x: 1, y: 2 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 4 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 11 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 13 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    // -- Right wall: bookshelf column (clear of door at y=6-9) --
    { tile: { x: 18, y: 2 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    { tile: { x: 18, y: 4 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 18, y: 11 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    { tile: { x: 18, y: 13 }, spriteKey: 'BOOKSHELF', collidable: true },
    // -- Center reading area: 2 study desks with PCs --
    { tile: { x: 7, y: 3 }, spriteKey: 'TABLE_FRONT', collidable: true },
    { tile: { x: 8, y: 3 }, spriteKey: 'PC_FRONT_ON_1', collidable: true },
    { tile: { x: 7, y: 11 }, spriteKey: 'TABLE_FRONT', collidable: true },
    { tile: { x: 8, y: 11 }, spriteKey: 'PC_FRONT_ON_2', collidable: true },
    // -- Reading chairs at the desks --
    { tile: { x: 7, y: 5 }, spriteKey: 'WOODEN_CHAIR_FRONT', collidable: false },
    { tile: { x: 7, y: 13 }, spriteKey: 'WOODEN_CHAIR_FRONT', collidable: false },
    // -- Middle aisle bookshelf (island) — research agents walk around this --
    { tile: { x: 12, y: 3 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    { tile: { x: 12, y: 11 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    // -- Cozy touches --
    { tile: { x: 5, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 14, y: 1 }, spriteKey: 'SMALL_PAINTING', collidable: false },
    { tile: { x: 10, y: 7 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 5, y: 14 }, spriteKey: 'PLANT_2', collidable: false },
    { tile: { x: 14, y: 14 }, spriteKey: 'POT', collidable: false },
    { tile: { x: 10, y: 1 }, spriteKey: 'HANGING_PLANT', collidable: false },
  ],
  phase: 'research',
};

const council: RoomDef = {
  id: 'council',
  label: 'Council Chamber',
  width: 16,
  height: 16,
  worldOffset: { x: 42, y: 0 },
  floorColor: 0x4a3030,
  wallColor: 0x664444,
  floorTile: 'floor_5',
  doors: [
    {
      // left wall <- corridor from library
      localTile: { x: 0, y: 6 },
      targetRoomId: 'corridor_library_council',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'left',
    },
    {
      // right wall -> corridor to marketplace
      localTile: { x: 15, y: 6 },
      targetRoomId: 'corridor_council_marketplace',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [
    {
      id: 'npc_elder_north',
      skin: 'char_002',
      tile: { x: 8, y: 5 },
      type: 'static',
      caption: 'Elder Kael',
      dialogId: 'council_kael',
      facing: 'down',
    },
    {
      id: 'npc_elder_south',
      skin: 'char_003',
      tile: { x: 8, y: 10 },
      type: 'static',
      caption: 'Elder Mira',
      dialogId: 'council_mira',
      facing: 'up',
    },
    {
      id: 'npc_elder_west',
      skin: 'char_004',
      tile: { x: 5, y: 7 },
      type: 'static',
      caption: 'Elder Orin',
      dialogId: 'council_orin',
      facing: 'right',
    },
    {
      id: 'npc_elder_east',
      skin: 'char_005',
      tile: { x: 11, y: 7 },
      type: 'static',
      caption: 'Elder Saya',
      dialogId: 'council_saya',
      facing: 'left',
    },
  ],
  furniture: [
    // -- Central round table (2x2 area) --
    { tile: { x: 7, y: 7 }, spriteKey: 'TABLE_FRONT', collidable: true },
    { tile: { x: 9, y: 7 }, spriteKey: 'TABLE_FRONT', collidable: true },
    // -- Chairs around table matching elder positions --
    { tile: { x: 8, y: 5 }, spriteKey: 'CUSHIONED_CHAIR_BACK', collidable: false },
    { tile: { x: 8, y: 10 }, spriteKey: 'CUSHIONED_CHAIR_FRONT', collidable: false },
    { tile: { x: 5, y: 7 }, spriteKey: 'CUSHIONED_CHAIR_SIDE', collidable: false },
    { tile: { x: 11, y: 7 }, spriteKey: 'CUSHIONED_CHAIR_SIDE', collidable: false },
    // -- Whiteboard at top center --
    { tile: { x: 8, y: 1 }, spriteKey: 'WHITEBOARD', collidable: false },
    // -- Wall art --
    { tile: { x: 2, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 13, y: 1 }, spriteKey: 'SMALL_PAINTING', collidable: false },
    // -- Corner decor to make it feel warm --
    { tile: { x: 1, y: 2 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 14, y: 2 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 1, y: 13 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 14, y: 13 }, spriteKey: 'PLANT_2', collidable: false },
    // -- Side furniture --
    { tile: { x: 2, y: 12 }, spriteKey: 'COFFEE_TABLE', collidable: true },
    { tile: { x: 3, y: 12 }, spriteKey: 'COFFEE', collidable: false },
    { tile: { x: 13, y: 12 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 1, y: 1 }, spriteKey: 'CLOCK', collidable: false },
  ],
  phase: 'council',
};

const marketplace: RoomDef = {
  id: 'marketplace',
  label: 'Marketplace',
  width: 24,
  height: 16,
  worldOffset: { x: 61, y: 0 },
  floorColor: 0x3d3525,
  wallColor: 0x5e5038,
  floorTile: 'floor_7',
  doors: [
    {
      // left wall <- corridor from council
      localTile: { x: 0, y: 6 },
      targetRoomId: 'corridor_council_marketplace',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'left',
    },
    {
      // right wall -> corridor to time room
      localTile: { x: 23, y: 6 },
      targetRoomId: 'corridor_marketplace_timeroom',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [
    // -- Perimeter stalls/tables (leave center wide open for agents) --
    // Top row stalls
    { tile: { x: 3, y: 2 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 4, y: 2 }, spriteKey: 'COFFEE', collidable: false },
    { tile: { x: 10, y: 2 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 17, y: 2 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 18, y: 2 }, spriteKey: 'COFFEE', collidable: false },
    // Bottom row stalls
    { tile: { x: 3, y: 13 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 10, y: 13 }, spriteKey: 'COFFEE_TABLE', collidable: true },
    { tile: { x: 17, y: 13 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    // -- Seating along walls --
    { tile: { x: 1, y: 3 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 22, y: 3 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 1, y: 12 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 22, y: 12 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    // -- Corner plants & decor (cheerful) --
    { tile: { x: 1, y: 1 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 22, y: 1 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 1, y: 14 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 22, y: 14 }, spriteKey: 'PLANT_2', collidable: false },
    // -- Wall decorations --
    { tile: { x: 6, y: 1 }, spriteKey: 'SMALL_PAINTING', collidable: false },
    { tile: { x: 12, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 19, y: 1 }, spriteKey: 'SMALL_PAINTING_2', collidable: false },
    // -- Bins --
    { tile: { x: 7, y: 14 }, spriteKey: 'BIN', collidable: false },
    { tile: { x: 15, y: 14 }, spriteKey: 'BIN', collidable: false },
  ],
  phase: 'swarm',
};

const time_room: RoomDef = {
  id: 'time_room',
  label: 'Time Room',
  width: 16,
  height: 16,
  worldOffset: { x: 88, y: 0 },
  floorColor: 0x2e2e4a,
  wallColor: 0x444466,
  floorTile: 'floor_2',
  doors: [
    {
      // left wall <- corridor from marketplace
      localTile: { x: 0, y: 6 },
      targetRoomId: 'corridor_marketplace_timeroom',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'left',
    },
    {
      // right wall -> corridor to archive
      localTile: { x: 15, y: 6 },
      targetRoomId: 'corridor_timeroom_archive',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'right',
    },
  ],
  staticNpcs: [],
  furniture: [
    // -- Central pedestal/orb table --
    { tile: { x: 7, y: 7 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    { tile: { x: 8, y: 7 }, spriteKey: 'SMALL_TABLE_FRONT', collidable: true },
    // -- Cushioned benches around center for contemplation --
    { tile: { x: 7, y: 5 }, spriteKey: 'CUSHIONED_BENCH', collidable: true },
    { tile: { x: 7, y: 10 }, spriteKey: 'CUSHIONED_BENCH', collidable: true },
    // -- Corner greenery (serene garden feel) --
    { tile: { x: 1, y: 1 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 14, y: 1 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 1, y: 14 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 14, y: 14 }, spriteKey: 'LARGE_PLANT', collidable: true },
    // -- Plants scattered (lush, garden-like) --
    { tile: { x: 3, y: 3 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 12, y: 3 }, spriteKey: 'PLANT_2', collidable: false },
    { tile: { x: 3, y: 12 }, spriteKey: 'HANGING_PLANT', collidable: false },
    { tile: { x: 12, y: 12 }, spriteKey: 'CACTUS', collidable: false },
    { tile: { x: 5, y: 1 }, spriteKey: 'POT', collidable: false },
    { tile: { x: 10, y: 1 }, spriteKey: 'POT', collidable: false },
    // -- Atmospheric wall art --
    { tile: { x: 7, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 1, y: 7 }, spriteKey: 'SMALL_PAINTING', collidable: false },
  ],
  phase: 'time',
};

const archive: RoomDef = {
  id: 'archive',
  label: 'Archive',
  width: 16,
  height: 16,
  worldOffset: { x: 107, y: 0 },
  floorColor: 0x3a2a2a,
  wallColor: 0x5c4040,
  floorTile: 'floor_4',
  doors: [
    {
      // left wall <- corridor from time room
      localTile: { x: 0, y: 6 },
      targetRoomId: 'corridor_timeroom_archive',
      targetTile: { x: 1, y: 1 },
      width: 4,
      direction: 'left',
    },
  ],
  staticNpcs: [
    {
      id: 'npc_printing_press',
      skin: 'char_015',
      tile: { x: 8, y: 4 },
      type: 'static',
      caption: 'Printing Press Operator',
      dialogId: 'archive_printer',
      facing: 'down',
    },
  ],
  furniture: [
    // -- Printing press desk (NPC sits behind it) --
    { tile: { x: 7, y: 5 }, spriteKey: 'DESK_FRONT', collidable: true },
    { tile: { x: 9, y: 5 }, spriteKey: 'DESK_FRONT', collidable: true },
    { tile: { x: 10, y: 5 }, spriteKey: 'PC_FRONT_ON_3', collidable: true },
    // -- Archive bookshelves (walls of knowledge) --
    { tile: { x: 1, y: 2 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 4 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 11 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    { tile: { x: 1, y: 13 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 14, y: 2 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 14, y: 4 }, spriteKey: 'BOOKSHELF', collidable: true },
    { tile: { x: 14, y: 11 }, spriteKey: 'DOUBLE_BOOKSHELF', collidable: true },
    // -- Reading area --
    { tile: { x: 5, y: 10 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 10, y: 10 }, spriteKey: 'WOODEN_BENCH', collidable: true },
    { tile: { x: 7, y: 12 }, spriteKey: 'COFFEE_TABLE', collidable: true },
    { tile: { x: 8, y: 12 }, spriteKey: 'COFFEE', collidable: false },
    // -- Decor (grand feel) --
    { tile: { x: 5, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 11, y: 1 }, spriteKey: 'LARGE_PAINTING', collidable: false },
    { tile: { x: 8, y: 1 }, spriteKey: 'CLOCK', collidable: false },
    // -- Plants --
    { tile: { x: 3, y: 2 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 12, y: 2 }, spriteKey: 'LARGE_PLANT', collidable: true },
    { tile: { x: 3, y: 13 }, spriteKey: 'PLANT', collidable: false },
    { tile: { x: 12, y: 13 }, spriteKey: 'POT', collidable: false },
  ],
  phase: 'report',
};

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

/** All room definitions including corridor connectors, ordered left to right. */
export const roomDefs: RoomDef[] = [
  lobby,
  corridor_lobby_library,
  library,
  corridor_library_council,
  council,
  corridor_council_marketplace,
  marketplace,
  corridor_marketplace_timeroom,
  time_room,
  corridor_timeroom_archive,
  archive,
];

/**
 * Total world dimensions in tiles.
 * Calculated from the bounding box of all rooms.
 */
export const WORLD_WIDTH = (() => {
  let max = 0;
  for (const r of roomDefs) {
    const right = r.worldOffset.x + r.width;
    if (right > max) max = right;
  }
  return max;
})();

export const WORLD_HEIGHT = (() => {
  let max = 0;
  for (const r of roomDefs) {
    const bottom = r.worldOffset.y + r.height;
    if (bottom > max) max = bottom;
  }
  return max;
})();

/** Look up a single room by its `id`. */
export function getRoomById(id: string): RoomDef | undefined {
  return roomDefs.find((r) => r.id === id);
}
