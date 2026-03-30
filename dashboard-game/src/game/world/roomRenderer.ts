import Phaser from 'phaser';
import { type RoomDef, TILE, WORLD_WIDTH, WORLD_HEIGHT } from './roomDefs';
import { FURNITURE_SIZES } from './furnitureDefs';

export interface RenderResult {
  wallLayer: Phaser.Physics.Arcade.StaticGroup;
  objectLayer: Phaser.Physics.Arcade.StaticGroup;
  worldWidth: number;
  worldHeight: number;
  spawnPoint: { x: number; y: number } | null;
}

export class RoomRenderer {
  static renderAll(scene: Phaser.Scene, rooms: RoomDef[]): RenderResult {
    const worldPxW = WORLD_WIDTH * TILE;
    const worldPxH = WORLD_HEIGHT * TILE;
    const gfx = scene.add.graphics();
    gfx.setDepth(0);

    const wallGroup = scene.physics.add.staticGroup();
    const objectGroup = scene.physics.add.staticGroup();
    let spawnPoint: { x: number; y: number } | null = null;

    for (const room of rooms) {
      const ox = room.worldOffset.x * TILE;
      const oy = room.worldOffset.y * TILE;
      const rw = room.width * TILE;
      const rh = room.height * TILE;

      // --- Floor ---
      // If room has a floorTile and the texture exists, tile it across the interior
      // Otherwise fall back to colored rectangle
      if (room.floorTile && scene.textures.exists(room.floorTile)) {
        // Stamp the 16x16 floor tile at 2x scale across each tile position in the room interior
        for (let ly = 1; ly < room.height - 1; ly++) {
          for (let lx = 1; lx < room.width - 1; lx++) {
            const px = ox + lx * TILE + TILE / 2;
            const py = oy + ly * TILE + TILE / 2;
            scene.add.image(px, py, room.floorTile).setScale(2).setDepth(0);
          }
        }
      } else {
        gfx.fillStyle(room.floorColor, 1);
        gfx.fillRect(ox + TILE, oy + TILE, rw - TILE * 2, rh - TILE * 2);
      }

      // --- Walls ---
      // Build door tile set for this room
      const doorTiles = buildDoorTileSet(room);

      for (let ly = 0; ly < room.height; ly++) {
        for (let lx = 0; lx < room.width; lx++) {
          if (!isPerimeter(lx, ly, room.width, room.height)) continue;

          const wx = room.worldOffset.x + lx;
          const wy = room.worldOffset.y + ly;
          const key = `${wx},${wy}`;

          if (doorTiles.has(key)) {
            // Door opening — draw floor tile here too
            if (room.floorTile && scene.textures.exists(room.floorTile)) {
              scene.add.image(wx * TILE + TILE / 2, wy * TILE + TILE / 2, room.floorTile)
                .setScale(2).setDepth(0);
            } else {
              gfx.fillStyle(room.floorColor, 0.6);
              gfx.fillRect(wx * TILE, wy * TILE, TILE, TILE);
            }
            continue;
          }

          // Wall tile — draw colored rectangle with subtle shadow
          gfx.fillStyle(room.wallColor, 1);
          gfx.fillRect(wx * TILE, wy * TILE, TILE, TILE);
          // Shadow on bottom edge
          gfx.fillStyle(0x000000, 0.2);
          gfx.fillRect(wx * TILE, wy * TILE + TILE - 4, TILE, 4);
          // Highlight on top edge
          gfx.fillStyle(0xffffff, 0.05);
          gfx.fillRect(wx * TILE, wy * TILE, TILE, 2);

          // Physics body
          const body = scene.add.zone(wx * TILE + TILE / 2, wy * TILE + TILE / 2, TILE, TILE);
          wallGroup.add(body);
          (body.body as Phaser.Physics.Arcade.StaticBody).setSize(TILE, TILE);
        }
      }

      // --- Room label ---
      if (room.label) {
        scene.add.text(ox + rw / 2, oy + TILE + 8, room.label, {
          fontFamily: 'monospace',
          fontSize: '12px',
          color: '#ffffff',
          stroke: '#000000',
          strokeThickness: 3,
          align: 'center',
        }).setOrigin(0.5, 0).setAlpha(0.5).setDepth(1);
      }

      // --- Furniture sprites ---
      for (const furn of room.furniture) {
        const fx = (room.worldOffset.x + furn.tile.x) * TILE + TILE / 2;
        const fy = (room.worldOffset.y + furn.tile.y) * TILE + TILE / 2;
        const scale = furn.scale ?? 2;
        const depth = furn.depth ?? 3;

        if (scene.textures.exists(furn.spriteKey)) {
          const img = scene.add.image(fx, fy, furn.spriteKey);
          img.setScale(scale);
          img.setDepth(depth);

          if (furn.collidable) {
            // Get natural size for collision body
            const natural = FURNITURE_SIZES[furn.spriteKey];
            const cw = natural ? natural.w * scale : TILE;
            const ch = natural ? natural.h * scale : TILE;
            const zone = scene.add.zone(fx, fy, cw, ch);
            objectGroup.add(zone);
            (zone.body as Phaser.Physics.Arcade.StaticBody).setSize(cw, ch);
          }
        } else {
          // Fallback: colored rectangle
          gfx.fillStyle(room.wallColor, 0.4);
          gfx.fillRect(fx - TILE / 2, fy - TILE / 2, TILE, TILE);
          if (furn.collidable) {
            const zone = scene.add.zone(fx, fy, TILE, TILE);
            objectGroup.add(zone);
            (zone.body as Phaser.Physics.Arcade.StaticBody).setSize(TILE, TILE);
          }
        }
      }

      // --- Spawn point ---
      if (room.spawnPoint && !spawnPoint) {
        spawnPoint = {
          x: (room.worldOffset.x + room.spawnPoint.x) * TILE + TILE / 2,
          y: (room.worldOffset.y + room.spawnPoint.y) * TILE + TILE / 2,
        };
      }
    }

    wallGroup.refresh();
    objectGroup.refresh();

    return { wallLayer: wallGroup, objectLayer: objectGroup, worldWidth: worldPxW, worldHeight: worldPxH, spawnPoint };
  }
}

// Helpers (same logic as before)
function buildDoorTileSet(room: RoomDef): Set<string> {
  const set = new Set<string>();
  const ox = room.worldOffset.x;
  const oy = room.worldOffset.y;

  for (const door of room.doors) {
    const lx = door.localTile.x;
    const ly = door.localTile.y;

    if (door.direction === 'up' || door.direction === 'down') {
      for (let dx = 0; dx < door.width; dx++) {
        set.add(`${ox + lx + dx},${oy + ly}`);
      }
    } else {
      for (let dy = 0; dy < door.width; dy++) {
        set.add(`${ox + lx},${oy + ly + dy}`);
      }
    }
  }
  return set;
}

function isPerimeter(lx: number, ly: number, w: number, h: number): boolean {
  return lx === 0 || ly === 0 || lx === w - 1 || ly === h - 1;
}
