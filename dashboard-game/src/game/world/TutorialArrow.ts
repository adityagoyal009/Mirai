import Phaser from 'phaser';
import { TILE, getRoomById } from './roomDefs';

export class TutorialArrow {
  private scene: Phaser.Scene;
  private arrow: Phaser.GameObjects.Graphics | null = null;
  private label: Phaser.GameObjects.Text | null = null;
  private tween: Phaser.Tweens.Tween | null = null;
  private dismissed = false;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.createStartArrow();
  }

  private createStartArrow(): void {
    // Find the intake desk NPC position from roomDefs
    const lobby = getRoomById('lobby');
    if (!lobby || !lobby.staticNpcs.length) return;

    const npcDef = lobby.staticNpcs[0];
    const nx = (lobby.worldOffset.x + npcDef.tile.x) * TILE + TILE / 2;
    const ny = (lobby.worldOffset.y + npcDef.tile.y) * TILE - 20;

    // Draw a downward-pointing triangle arrow
    const arrow = this.scene.add.graphics();
    arrow.fillStyle(0x4a9eff, 0.9);
    arrow.fillTriangle(-8, -12, 8, -12, 0, 0); // pointing down
    arrow.setPosition(nx, ny);
    arrow.setDepth(100);
    this.arrow = arrow;

    // "Start here!" text above arrow
    this.label = this.scene.add.text(nx, ny - 20, 'Start here!', {
      fontFamily: 'monospace',
      fontSize: '10px',
      color: '#4a9eff',
      stroke: '#000',
      strokeThickness: 3,
      align: 'center',
    });
    this.label.setOrigin(0.5);
    this.label.setDepth(100);

    // Bobbing animation
    this.tween = this.scene.tweens.add({
      targets: [arrow, this.label],
      y: '-=8',
      duration: 600,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });
  }

  /** Call each frame with player position. Dismisses when player is near intake desk. */
  checkDismiss(playerX: number, playerY: number): void {
    if (this.dismissed || !this.arrow) return;
    const dist = Phaser.Math.Distance.Between(playerX, playerY, this.arrow.x, this.arrow.y + 20);
    if (dist < 60) {
      this.dismiss();
    }
  }

  dismiss(): void {
    if (this.dismissed) return;
    this.dismissed = true;
    if (this.tween) this.tween.stop();
    if (this.arrow) {
      this.scene.tweens.add({ targets: this.arrow, alpha: 0, duration: 300, onComplete: () => this.arrow?.destroy() });
    }
    if (this.label) {
      this.scene.tweens.add({ targets: this.label, alpha: 0, duration: 300, onComplete: () => this.label?.destroy() });
    }
  }

  /** Show a temporary directional hint near a gate that just opened. */
  showDirectionHint(x: number, y: number): void {
    const hint = this.scene.add.text(x + 20, y, 'Walk right to proceed  \u2192', {
      fontFamily: 'monospace',
      fontSize: '9px',
      color: '#44cc66',
      stroke: '#000',
      strokeThickness: 2,
    });
    hint.setOrigin(0, 0.5);
    hint.setDepth(50);
    hint.setAlpha(0);

    this.scene.tweens.add({
      targets: hint,
      alpha: 1,
      duration: 300,
    });
    this.scene.tweens.add({
      targets: hint,
      alpha: 0,
      duration: 500,
      delay: 3000,
      onComplete: () => hint.destroy(),
    });
  }
}
