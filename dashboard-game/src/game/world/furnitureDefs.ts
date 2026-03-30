// ---------------------------------------------------------------------------
// furnitureDefs.ts — Furniture sprite metadata for the Mirai War Room
// ---------------------------------------------------------------------------
// Actual furniture placement is inline in roomDefs.ts.
// This file exports the FurnitureDef type and a lookup table mapping each
// sprite key to its natural pixel dimensions (used for collision sizing).
// ---------------------------------------------------------------------------

// Re-export the FurnitureDef type for use elsewhere
export type { FurnitureDef } from './roomDefs';

// Sprite key -> natural pixel dimensions (for collision sizing).
// These are the actual sizes of the pixel-agents PNGs.
export const FURNITURE_SIZES: Record<string, { w: number; h: number }> = {
  DESK_FRONT: { w: 48, h: 32 },
  DESK_SIDE: { w: 32, h: 32 },
  BOOKSHELF: { w: 32, h: 16 },
  DOUBLE_BOOKSHELF: { w: 48, h: 32 },
  PC_FRONT_ON_1: { w: 16, h: 16 },
  PC_FRONT_ON_2: { w: 16, h: 16 },
  PC_FRONT_ON_3: { w: 16, h: 16 },
  PC_FRONT_OFF: { w: 16, h: 16 },
  PC_SIDE: { w: 16, h: 16 },
  PC_BACK: { w: 16, h: 16 },
  WHITEBOARD: { w: 32, h: 16 },
  TABLE_FRONT: { w: 48, h: 32 },
  SMALL_TABLE_FRONT: { w: 32, h: 16 },
  SMALL_TABLE_SIDE: { w: 16, h: 16 },
  COFFEE_TABLE: { w: 32, h: 16 },
  SOFA_FRONT: { w: 48, h: 16 },
  SOFA_SIDE: { w: 16, h: 32 },
  SOFA_BACK: { w: 48, h: 16 },
  CUSHIONED_CHAIR_FRONT: { w: 16, h: 16 },
  CUSHIONED_CHAIR_SIDE: { w: 16, h: 16 },
  CUSHIONED_CHAIR_BACK: { w: 16, h: 16 },
  WOODEN_CHAIR_FRONT: { w: 16, h: 16 },
  WOODEN_CHAIR_SIDE: { w: 16, h: 16 },
  WOODEN_CHAIR_BACK: { w: 16, h: 16 },
  CUSHIONED_BENCH: { w: 48, h: 16 },
  WOODEN_BENCH: { w: 48, h: 16 },
  PLANT: { w: 16, h: 16 },
  PLANT_2: { w: 16, h: 16 },
  LARGE_PLANT: { w: 16, h: 32 },
  HANGING_PLANT: { w: 16, h: 16 },
  CACTUS: { w: 16, h: 16 },
  POT: { w: 16, h: 16 },
  CLOCK: { w: 16, h: 16 },
  BIN: { w: 16, h: 16 },
  COFFEE: { w: 16, h: 16 },
  LARGE_PAINTING: { w: 32, h: 32 },
  SMALL_PAINTING: { w: 16, h: 16 },
  SMALL_PAINTING_2: { w: 16, h: 16 },
};
