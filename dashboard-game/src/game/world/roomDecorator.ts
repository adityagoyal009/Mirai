import Phaser from 'phaser';
import { roomDefs, TILE, type RoomDef } from './roomDefs';

export class RoomDecorator {
  /**
   * Add visual details to all rooms: subtle grid lines, corner accents,
   * phase icons, and door indicators.
   */
  static decorateAll(scene: Phaser.Scene): void {
    const gfx = scene.add.graphics();
    gfx.setDepth(1); // above floor (0), below objects (2+)

    for (const room of roomDefs) {
      if (!room.label) continue; // skip corridors

      const ox = room.worldOffset.x * TILE;
      const oy = room.worldOffset.y * TILE;
      const rw = room.width * TILE;
      const rh = room.height * TILE;

      // Subtle grid lines inside the room
      gfx.lineStyle(1, 0xffffff, 0.03);
      for (let lx = 1; lx < room.width - 1; lx++) {
        gfx.lineBetween(ox + lx * TILE, oy + TILE, ox + lx * TILE, oy + rh - TILE);
      }
      for (let ly = 1; ly < room.height - 1; ly++) {
        gfx.lineBetween(ox + TILE, oy + ly * TILE, ox + rw - TILE, oy + ly * TILE);
      }

      // Corner accent marks (small L-shapes in brighter wall color)
      const accentColor = room.wallColor;
      const accentAlpha = 0.4;
      const accentLen = 12;
      gfx.lineStyle(2, accentColor, accentAlpha);
      // Top-left
      gfx.lineBetween(ox + TILE + 2, oy + TILE + 2, ox + TILE + accentLen, oy + TILE + 2);
      gfx.lineBetween(ox + TILE + 2, oy + TILE + 2, ox + TILE + 2, oy + TILE + accentLen);
      // Top-right
      gfx.lineBetween(ox + rw - TILE - 2, oy + TILE + 2, ox + rw - TILE - accentLen, oy + TILE + 2);
      gfx.lineBetween(ox + rw - TILE - 2, oy + TILE + 2, ox + rw - TILE - 2, oy + TILE + accentLen);
      // Bottom-left
      gfx.lineBetween(ox + TILE + 2, oy + rh - TILE - 2, ox + TILE + accentLen, oy + rh - TILE - 2);
      gfx.lineBetween(ox + TILE + 2, oy + rh - TILE - 2, ox + TILE + 2, oy + rh - TILE - accentLen);
      // Bottom-right
      gfx.lineBetween(ox + rw - TILE - 2, oy + rh - TILE - 2, ox + rw - TILE - accentLen, oy + rh - TILE - 2);
      gfx.lineBetween(ox + rw - TILE - 2, oy + rh - TILE - 2, ox + rw - TILE - 2, oy + rh - TILE - accentLen);

      // Phase icon/badge in top-left inner corner
      if (room.phase) {
        const phaseColors: Record<string, string> = {
          intake: '#4a9eff',
          research: '#4a9eff',
          council: '#cc66ff',
          oasis: '#ffaa4a',
          swarm: '#ffaa4a',
          time: '#e6e64a',
          report: '#44cc66',
        };
        const color = phaseColors[room.phase] || '#888';
        scene.add.text(ox + TILE + 6, oy + TILE + 4, room.phase.toUpperCase(), {
          fontFamily: 'monospace',
          fontSize: '7px',
          color,
        }).setAlpha(0.5).setDepth(1);
      }
    }

    // Door indicators — small arrows at door openings
    for (const room of roomDefs) {
      for (const door of room.doors) {
        const wx = (room.worldOffset.x + door.localTile.x) * TILE;
        const wy = (room.worldOffset.y + door.localTile.y) * TILE;

        // Small triangle arrow pointing through the door
        const arrowSize = 6;
        let cx: number, cy: number;
        if (door.direction === 'down') {
          cx = wx + (door.width * TILE) / 2;
          cy = wy + TILE / 2;
          gfx.lineStyle(1, 0xffffff, 0.15);
          gfx.lineBetween(cx - arrowSize, cy - arrowSize, cx, cy);
          gfx.lineBetween(cx + arrowSize, cy - arrowSize, cx, cy);
        } else if (door.direction === 'up') {
          cx = wx + (door.width * TILE) / 2;
          cy = wy + TILE / 2;
          gfx.lineStyle(1, 0xffffff, 0.15);
          gfx.lineBetween(cx - arrowSize, cy + arrowSize, cx, cy);
          gfx.lineBetween(cx + arrowSize, cy + arrowSize, cx, cy);
        } else if (door.direction === 'right') {
          cx = wx + TILE / 2;
          cy = wy + (door.width * TILE) / 2;
          gfx.lineStyle(1, 0xffffff, 0.15);
          gfx.lineBetween(cx - arrowSize, cy - arrowSize, cx, cy);
          gfx.lineBetween(cx - arrowSize, cy + arrowSize, cx, cy);
        } else if (door.direction === 'left') {
          cx = wx + TILE / 2;
          cy = wy + (door.width * TILE) / 2;
          gfx.lineStyle(1, 0xffffff, 0.15);
          gfx.lineBetween(cx + arrowSize, cy - arrowSize, cx, cy);
          gfx.lineBetween(cx + arrowSize, cy + arrowSize, cx, cy);
        }
      }
    }
  }
}
