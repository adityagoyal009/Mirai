import Phaser from 'phaser';
import type { WorldScene } from '../WorldScene';
import type { MiraiState } from '../../miraiSocket';
import { TILE, getRoomById } from '../world/roomDefs';

export class OasisBehavior {
  private scene: WorldScene;
  private overlay?: Phaser.GameObjects.Rectangle;
  private eventTexts: Phaser.GameObjects.Text[] = [];
  private processedMonths = 0;

  constructor(scene: WorldScene) {
    this.scene = scene;
  }

  enter(_state: MiraiState): void {
    this.processedMonths = 0;
    const room = getRoomById('time_room');
    if (!room) return;

    const ox = room.worldOffset.x * TILE;
    const oy = room.worldOffset.y * TILE;
    const rw = room.width * TILE;
    const rh = room.height * TILE;

    // Create a tint overlay rectangle covering the time room
    this.overlay = this.scene.add.rectangle(
      ox + rw / 2, oy + rh / 2, rw, rh, 0xffeeaa, 0.05
    );
    this.overlay.setDepth(3);
  }

  onStateUpdate(state: MiraiState): void {
    if (!this.overlay) return;

    const timeline = state.oasisTimeline;
    if (timeline.length <= this.processedMonths) return;

    // Process new months
    for (let i = this.processedMonths; i < timeline.length; i++) {
      const entry = timeline[i];
      this.applyMonth(entry, i, timeline.length);
    }
    this.processedMonths = timeline.length;
  }

  private applyMonth(
    entry: { month: number; event: string; sentimentPct: number },
    index: number,
    _total: number
  ): void {
    // Tint based on sentiment: high sentiment = warm, low = cold
    const sentiment = entry.sentimentPct / 100;
    let color: number;
    let alpha: number;
    if (sentiment > 0.6) {
      color = 0xffeeaa; alpha = 0.08; // warm
    } else if (sentiment > 0.4) {
      color = 0xffffff; alpha = 0.02; // neutral
    } else if (sentiment > 0.2) {
      color = 0xff8844; alpha = 0.08; // sunset/warning
    } else {
      color = 0x2244aa; alpha = 0.12; // cold/dark
    }

    // Tween the overlay color/alpha
    if (this.overlay) {
      this.overlay.setFillStyle(color, alpha);
    }

    // Show floating event text in the time room
    const room = getRoomById('time_room');
    if (!room) return;

    const ox = room.worldOffset.x * TILE;
    const oy = room.worldOffset.y * TILE;
    const rw = room.width * TILE;

    const text = this.scene.add.text(
      ox + rw / 2,
      oy + TILE * 3 + index * 22,
      `M${entry.month}: ${entry.event.substring(0, 40)}`,
      {
        fontFamily: 'monospace',
        fontSize: '8px',
        color: sentiment > 0.5 ? '#88ff88' : '#ff8888',
        stroke: '#000',
        strokeThickness: 2,
        align: 'center',
      }
    );
    text.setOrigin(0.5);
    text.setDepth(10);
    text.setAlpha(0);

    this.scene.tweens.add({
      targets: text,
      alpha: 0.8,
      duration: 500,
    });

    this.eventTexts.push(text);
  }

  tick(_time: number, _delta: number): void {
    // Could add particle effects here in future
  }

  freeze(): void {
    // Keep overlay and event texts visible — nothing to stop
  }

  exit(): void {
    if (this.overlay) {
      this.scene.tweens.add({
        targets: this.overlay,
        alpha: 0,
        duration: 1000,
        onComplete: () => { this.overlay?.destroy(); this.overlay = undefined; },
      });
    }
    for (const t of this.eventTexts) {
      this.scene.tweens.add({
        targets: t,
        alpha: 0,
        duration: 500,
        onComplete: () => t.destroy(),
      });
    }
    this.eventTexts = [];
    this.processedMonths = 0;
  }
}
