import type { WorldScene } from '../WorldScene';
import type { MiraiState } from '../../miraiSocket';
import { TILE, getRoomById } from '../world/roomDefs';

export class ReportBehavior {
  private scene: WorldScene;
  private activated = false;
  private scrollText?: Phaser.GameObjects.Text;

  constructor(scene: WorldScene) {
    this.scene = scene;
  }

  enter(state: MiraiState): void {
    this.activated = false;

    // Flash archive room
    const room = getRoomById('archive');
    if (!room) return;

    const ox = room.worldOffset.x * TILE;
    const oy = room.worldOffset.y * TILE;
    const rw = room.width * TILE;
    const rh = room.height * TILE;

    const flash = this.scene.add.rectangle(
      ox + rw / 2, oy + rh / 2, rw, rh, 0x44cc66, 0.1
    );
    flash.setDepth(2);
    this.scene.tweens.add({
      targets: flash,
      alpha: 0,
      duration: 2000,
      onComplete: () => flash.destroy(),
    });
  }

  onStateUpdate(state: MiraiState): void {
    if (this.activated) return;
    if (state.phase !== 'complete') return;

    this.activated = true;

    // Make the printing press NPC say the report is ready
    const printerNpc = (this.scene as any).npcs?.find(
      (n: any) => n.npcId === 'npc_printing_press'
    );
    if (printerNpc) {
      printerNpc.say('Your report is ready! Press E to collect.', 0);

      // Update the NPC's interaction to emit a report event
      printerNpc.setOnInteract(() => {
        this.scene.events.emit('report:collect', state.narrative || 'Report generated.');
        printerNpc.say('Report collected!', 3000);
      });
    }

    // Show a small scroll/paper visual near the NPC
    const room = getRoomById('archive');
    if (room) {
      const cx = (room.worldOffset.x + room.width / 2) * TILE;
      const cy = (room.worldOffset.y + room.height / 2 + 3) * TILE;

      this.scrollText = this.scene.add.text(cx, cy, '📜 Report Ready', {
        fontFamily: 'monospace',
        fontSize: '10px',
        color: '#44cc66',
        stroke: '#000',
        strokeThickness: 2,
        align: 'center',
      });
      this.scrollText.setOrigin(0.5);
      this.scrollText.setDepth(10);

      // Gentle bob animation
      this.scene.tweens.add({
        targets: this.scrollText,
        y: cy - 4,
        duration: 1500,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut',
      });
    }
  }

  tick(_time: number, _delta: number): void {
    // Nothing frame-level needed
  }

  exit(): void {
    this.activated = false;
    if (this.scrollText) {
      this.scrollText.destroy();
      this.scrollText = undefined;
    }
  }
}
