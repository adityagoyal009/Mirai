import Phaser from 'phaser';
import { roomDefs, TILE, type RoomDef } from './roomDefs';

const PHASE_COLORS: Record<string, number> = {
  intake: 0x4a9eff,
  research: 0x4a9eff,
  council: 0xcc66ff,
  oasis: 0xffaa4a,
  swarm: 0xffaa4a,
  time: 0xe6e64a,
  report: 0x44cc66,
};

export class RoomAnnouncer {
  private scene: Phaser.Scene;
  private currentRoomId: string = '';
  private banner: Phaser.GameObjects.Container | null = null;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  /** Call each frame with player world position. */
  update(playerX: number, playerY: number): void {
    const tileX = Math.floor(playerX / TILE);
    const tileY = Math.floor(playerY / TILE);

    for (const room of roomDefs) {
      if (!room.label) continue; // skip corridors
      const ox = room.worldOffset.x;
      const oy = room.worldOffset.y;
      if (tileX >= ox && tileX < ox + room.width && tileY >= oy && tileY < oy + room.height) {
        if (room.id !== this.currentRoomId) {
          this.currentRoomId = room.id;
          this.showBanner(room);
        }
        return;
      }
    }
  }

  private showBanner(room: RoomDef): void {
    // Destroy previous banner if still animating
    if (this.banner) {
      this.banner.destroy();
    }

    const cam = this.scene.cameras.main;
    // Banner positioned at top of viewport (uses camera scroll)
    const cx = cam.scrollX + cam.width / (2 * cam.zoom);
    const cy = cam.scrollY + 20 / cam.zoom;

    const container = this.scene.add.container(cx, cy - 30);
    container.setDepth(200);
    container.setScrollFactor(0); // fixed to camera

    // Background bar
    const bg = this.scene.add.rectangle(0, 0, 280, 28, 0x0a0a15, 0.85);
    bg.setStrokeStyle(1, 0x333355, 0.5);
    container.add(bg);

    // Room name
    const phaseColor = PHASE_COLORS[room.phase || ''] || 0x888888;
    const colorStr = '#' + phaseColor.toString(16).padStart(6, '0');

    const nameText = this.scene.add.text(-130, -6, room.label, {
      fontFamily: 'monospace',
      fontSize: '11px',
      color: '#ffffff',
    });
    container.add(nameText);

    // Phase label
    if (room.phase) {
      const phaseText = this.scene.add.text(130, -6, room.phase.toUpperCase(), {
        fontFamily: 'monospace',
        fontSize: '9px',
        color: colorStr,
        align: 'right',
      });
      phaseText.setOrigin(1, 0);
      container.add(phaseText);
    }

    // Slide in from top
    container.setAlpha(0);
    this.scene.tweens.add({
      targets: container,
      y: cy,
      alpha: 1,
      duration: 300,
      ease: 'Power2',
    });

    // Slide out after hold
    this.scene.tweens.add({
      targets: container,
      alpha: 0,
      y: cy - 20,
      duration: 300,
      delay: 2000,
      onComplete: () => container.destroy(),
    });

    this.banner = container;
  }
}
