import Phaser from 'phaser';

export class SoundManager {
  private scene: Phaser.Scene;
  private lastFootstep = 0;
  private enabled = true;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  playFootstep(): void {
    const now = Date.now();
    if (now - this.lastFootstep < 250) return; // throttle
    this.lastFootstep = now;
    this.play('snd_click', 0.08);
  }

  playGateUnlock(): void { this.play('snd_confirm', 0.4); }
  playVote(positive: boolean): void { this.play(positive ? 'snd_select' : 'snd_bass', 0.25); }
  playPhaseTransition(): void { this.play('snd_ticket', 0.3); }
  playDialogAdvance(): void { this.play('snd_click', 0.2); }
  playAgentSpawn(): void { this.play('snd_select', 0.15); }

  private play(key: string, volume: number): void {
    if (!this.enabled) return;
    try {
      this.scene.sound.play(key, { volume });
    } catch { /* sound not loaded yet */ }
  }

  toggle(): void { this.enabled = !this.enabled; }
}
