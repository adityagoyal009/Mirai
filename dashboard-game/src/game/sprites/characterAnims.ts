/**
 * characterAnims.ts
 *
 * Creates walk and idle animations from 192x192 character spritesheets
 * laid out as a 4x4 grid of 48x48 frames.
 *
 * Frame layout per spritesheet:
 *   Row 0 (frames  0- 3): walk_down
 *   Row 1 (frames  4- 7): walk_left
 *   Row 2 (frames  8-11): walk_right
 *   Row 3 (frames 12-15): walk_up
 *
 * Idle uses frame index 0 of each respective row.
 */

const DIRECTIONS = ['down', 'left', 'right', 'up'] as const;

/** Row-start frame for each direction (row * 4). */
const ROW_START: Record<(typeof DIRECTIONS)[number], number> = {
  down: 0,
  left: 4,
  right: 8,
  up: 12,
};

/**
 * Register the eight standard character animations for a given spritesheet key.
 *
 * Animations created:
 *   `${key}_walk_down`  / `${key}_idle_down`
 *   `${key}_walk_left`  / `${key}_idle_left`
 *   `${key}_walk_right` / `${key}_idle_right`
 *   `${key}_walk_up`    / `${key}_idle_up`
 *
 * Safe to call multiple times — silently skips if the animations already exist.
 */
export function createCharacterAnims(scene: Phaser.Scene, key: string): void {
  // Guard against duplicate registration
  if (scene.anims.exists(`${key}_walk_down`)) return;

  for (const dir of DIRECTIONS) {
    const start = ROW_START[dir];

    // Walk animation — 4 frames, looping
    scene.anims.create({
      key: `${key}_walk_${dir}`,
      frames: scene.anims.generateFrameNumbers(key, { start, end: start + 3 }),
      frameRate: 8,
      repeat: -1,
    });

    // Idle animation — single frame (first frame of the row)
    scene.anims.create({
      key: `${key}_idle_${dir}`,
      frames: [{ key, frame: start }],
      frameRate: 1,
      repeat: 0,
    });
  }
}
