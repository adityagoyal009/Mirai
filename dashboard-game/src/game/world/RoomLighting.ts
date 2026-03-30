import Phaser from 'phaser';
import { roomDefs, TILE } from './roomDefs';

const ROOM_TINTS: Record<string, { color: number; alpha: number }> = {
  lobby: { color: 0xffddaa, alpha: 0.04 },
  library: { color: 0xaaffaa, alpha: 0.03 },
  council: { color: 0xddaaff, alpha: 0.04 },
  marketplace: { color: 0xffeeaa, alpha: 0.03 },
  time_room: { color: 0xaaddff, alpha: 0.05 },
  archive: { color: 0xffddcc, alpha: 0.03 },
};

interface RoomOverlay {
  id: string;
  rect: Phaser.GameObjects.Rectangle;
  baseAlpha: number;
}

export class RoomLighting {
  private scene: Phaser.Scene;
  private overlays: RoomOverlay[] = [];
  private currentRoomId: string = '';

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.createOverlays();
  }

  private createOverlays(): void {
    for (const room of roomDefs) {
      if (!room.label) continue;
      const tint = ROOM_TINTS[room.id];
      if (!tint) continue;

      const ox = room.worldOffset.x * TILE;
      const oy = room.worldOffset.y * TILE;
      const rw = room.width * TILE;
      const rh = room.height * TILE;

      const rect = this.scene.add.rectangle(
        ox + rw / 2, oy + rh / 2, rw - TILE * 2, rh - TILE * 2,
        tint.color, tint.alpha,
      );
      rect.setDepth(2);

      this.overlays.push({ id: room.id, rect, baseAlpha: tint.alpha });
    }
  }

  /** Call each frame. Pulses the room overlay when entering a new room. */
  update(playerX: number, playerY: number): void {
    const tileX = Math.floor(playerX / TILE);
    const tileY = Math.floor(playerY / TILE);

    for (const room of roomDefs) {
      if (!room.label) continue;
      const ox = room.worldOffset.x;
      const oy = room.worldOffset.y;
      if (tileX >= ox && tileX < ox + room.width && tileY >= oy && tileY < oy + room.height) {
        if (room.id !== this.currentRoomId) {
          this.currentRoomId = room.id;
          this.pulseRoom(room.id);
        }
        return;
      }
    }
  }

  private pulseRoom(roomId: string): void {
    const overlay = this.overlays.find((o) => o.id === roomId);
    if (!overlay) return;

    this.scene.tweens.add({
      targets: overlay.rect,
      alpha: overlay.baseAlpha * 2.5,
      duration: 400,
      yoyo: true,
      ease: 'Sine.easeOut',
      onComplete: () => {
        overlay.rect.setAlpha(overlay.baseAlpha);
      },
    });
  }
}
