import Phaser from 'phaser';
import type { WorldScene } from '../WorldScene';
import type { MiraiState } from '../../miraiSocket';
import { TILE, getRoomById } from '../world/roomDefs';

export class CouncilBehavior {
  private scene: WorldScene;
  private debateTimer?: Phaser.Time.TimerEvent;
  private clashGraphics?: Phaser.GameObjects.Graphics;
  private verdictShown = false;

  constructor(scene: WorldScene) {
    this.scene = scene;
  }

  enter(state: MiraiState): void {
    this.verdictShown = false;

    // Flash council chamber
    const room = getRoomById('council');
    if (room) {
      const ox = room.worldOffset.x * TILE;
      const oy = room.worldOffset.y * TILE;
      const flash = this.scene.add.rectangle(
        ox + room.width * TILE / 2,
        oy + room.height * TILE / 2,
        room.width * TILE,
        room.height * TILE,
        0xcc66ff, 0.08,
      );
      flash.setDepth(2);
      this.scene.tweens.add({ targets: flash, alpha: 0, duration: 2000, onComplete: () => flash.destroy() });
    }

    // Start debate: elders speak in rotation
    // Find the elder NPCs by ID pattern
    this.startDebate();
  }

  private startDebate(): void {
    const elderIds = ['npc_elder_north', 'npc_elder_south', 'npc_elder_west', 'npc_elder_east'];
    const elderNames = ['Kael', 'Mira', 'Orin', 'Saya'];
    const dimensions = ['Market Size', 'Team Quality', 'Product Fit', 'Timing', 'Competition'];
    let turn = 0;

    this.debateTimer = this.scene.time.addEvent({
      delay: 2500,
      loop: true,
      callback: () => {
        const elderNpc = this.findNpcById(elderIds[turn % 4]);
        if (elderNpc) {
          const dim = dimensions[turn % dimensions.length];
          const score = Math.floor(Math.random() * 4) + 5;
          elderNpc.say(`${dim}: ${score}/10`, 2200);
        }
        turn++;
      },
    });
  }

  onStateUpdate(state: MiraiState): void {
    if (state.council && !this.verdictShown) {
      this.verdictShown = true;

      // Stop debate rotation
      if (this.debateTimer) {
        this.debateTimer.destroy();
        this.debateTimer = undefined;
      }

      // Show verdict on all elders
      const elderIds = ['npc_elder_north', 'npc_elder_south', 'npc_elder_west', 'npc_elder_east'];
      for (const id of elderIds) {
        const npc = this.findNpcById(id);
        npc?.say(`Verdict: ${state.council.verdict} (${state.council.overall}/10)`, 5000);
      }

      // Clash effect on contested dimensions
      if (state.council.contestedDimensions.length > 0) {
        this.showClash(state.council.contestedDimensions);
      }
    }
  }

  private showClash(contested: string[]): void {
    const room = getRoomById('council');
    if (!room) return;

    const cx = (room.worldOffset.x + room.width / 2) * TILE;
    const cy = (room.worldOffset.y + room.height / 2) * TILE;

    // Show contested dimension text with flash effect
    for (let i = 0; i < contested.length; i++) {
      const text = this.scene.add.text(cx, cy - 20 + i * 16, `⚡ ${contested[i]}`, {
        fontFamily: 'monospace',
        fontSize: '10px',
        color: '#ff4444',
        stroke: '#000',
        strokeThickness: 2,
        align: 'center',
      });
      text.setOrigin(0.5);
      text.setDepth(50);
      text.setAlpha(0);

      this.scene.tweens.add({
        targets: text,
        alpha: 1,
        duration: 300,
        delay: i * 200,
        yoyo: true,
        hold: 2000,
        onComplete: () => text.destroy(),
      });
    }

    // Energy line between north and south elders
    const gfx = this.scene.add.graphics();
    gfx.setDepth(3);
    const northNpc = this.findNpcById('npc_elder_north');
    const southNpc = this.findNpcById('npc_elder_south');
    if (northNpc && southNpc) {
      gfx.lineStyle(2, 0xff4444, 0.8);
      gfx.lineBetween(northNpc.x, northNpc.y, southNpc.x, southNpc.y);
    }
    this.clashGraphics = gfx;
    this.scene.tweens.add({
      targets: gfx,
      alpha: 0,
      duration: 2000,
      delay: 1000,
      onComplete: () => { gfx.destroy(); this.clashGraphics = undefined; },
    });
  }

  tick(_time: number, _delta: number): void {
    // Nothing frame-level needed — debate runs on timer
  }

  freeze(): void {
    // Stop debate timer but keep verdict visuals on screen
    if (this.debateTimer) {
      this.debateTimer.destroy();
      this.debateTimer = undefined;
    }
  }

  exit(): void {
    if (this.debateTimer) {
      this.debateTimer.destroy();
      this.debateTimer = undefined;
    }
    if (this.clashGraphics) {
      this.clashGraphics.destroy();
      this.clashGraphics = undefined;
    }
    this.verdictShown = false;
  }

  private findNpcById(id: string): import('../entities/Npc').Npc | undefined {
    // Access npcs via scene — we need them to be accessible
    // WorldScene stores npcs in a public array
    return (this.scene as any).npcs?.find((n: any) => n.npcId === id);
  }
}
