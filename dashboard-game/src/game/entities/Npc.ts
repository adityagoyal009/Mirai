/**
 * Npc.ts
 *
 * Base NPC class with proximity-based "Press E" interaction prompt
 * and a SpeechBubble for dialog. Uses the same 48x48 character
 * spritesheets and animation system as the Player.
 */

import Phaser from 'phaser';
import { createCharacterAnims } from '../sprites/characterAnims';
import { SpeechBubble } from './SpeechBubble';

export interface NpcConfig {
  id: string;
  x: number;
  y: number;
  skin: string;
  caption?: string;
  type?: 'static' | 'dynamic';
  facing?: string;
  onInteract?: () => void;
}

export class Npc extends Phaser.Physics.Arcade.Sprite {
  public npcId: string;
  public caption: string;
  public npcType: 'static' | 'dynamic';
  public interactionRange: number = 60; // pixels
  public inRange: boolean = false;

  private bubble: SpeechBubble;
  private captionText: Phaser.GameObjects.Text;
  private onInteractCallback?: () => void;
  private skinKey: string;
  private facingDirection: string;

  constructor(scene: Phaser.Scene, config: NpcConfig) {
    super(scene, config.x, config.y, config.skin, 0);

    this.npcId = config.id;
    this.caption = config.caption ?? config.id;
    this.npcType = config.type ?? 'static';
    this.skinKey = config.skin;
    this.facingDirection = config.facing ?? 'down';
    this.onInteractCallback = config.onInteract;

    // Register walk/idle animations for this skin (safe to call multiple times)
    createCharacterAnims(scene, this.skinKey);

    // Add to scene + physics world
    scene.add.existing(this);
    scene.physics.add.existing(this);

    // Physics body — immovable so the player can't push NPCs around
    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setSize(24, 24);
    body.setOffset(12, 20);
    body.setImmovable(true);

    // Render below the player (Player is depth 5)
    this.setDepth(4);

    // Start in idle pose facing the configured direction
    this.anims.play(`${this.skinKey}_idle_${this.facingDirection}`, true);

    // --- Speech bubble ---
    this.bubble = new SpeechBubble(scene, this);

    // --- Caption / interaction prompt ---
    this.captionText = scene.add.text(config.x, config.y - 32, `Press E \u2014 ${this.caption}`, {
      fontFamily: 'monospace',
      fontSize: '9px',
      color: '#ffffff',
      stroke: '#000000',
      strokeThickness: 3,
      align: 'center',
    });
    this.captionText.setOrigin(0.5, 1);
    this.captionText.setDepth(90);
    this.captionText.setAlpha(0);
  }

  /* ------------------------------------------------------------------ */
  /*  Proximity / Interaction                                            */
  /* ------------------------------------------------------------------ */

  /** Call each frame from WorldScene, passing the player sprite. */
  checkProximity(player: Phaser.Physics.Arcade.Sprite): void {
    const dist = Phaser.Math.Distance.Between(this.x, this.y, player.x, player.y);
    const wasInRange = this.inRange;
    this.inRange = dist < this.interactionRange;

    if (this.inRange && !wasInRange) {
      // Fade in caption
      this.scene.tweens.killTweensOf(this.captionText);
      this.scene.tweens.add({
        targets: this.captionText,
        alpha: 1,
        duration: 200,
      });
    }

    if (!this.inRange && wasInRange) {
      // Fade out caption
      this.scene.tweens.killTweensOf(this.captionText);
      this.scene.tweens.add({
        targets: this.captionText,
        alpha: 0,
        duration: 200,
      });
    }

    // Keep caption anchored above NPC
    this.captionText.setPosition(this.x, this.y - 32);
  }

  /** Trigger the interaction callback (typically bound to the E key). */
  interact(): void {
    if (this.onInteractCallback) {
      this.onInteractCallback();
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Speech                                                             */
  /* ------------------------------------------------------------------ */

  /** Show a speech bubble above this NPC. duration in ms; 0 = stay until hide. */
  say(text: string, duration?: number): void {
    this.bubble.show(text, duration);
  }

  /* ------------------------------------------------------------------ */
  /*  Lifecycle                                                          */
  /* ------------------------------------------------------------------ */

  update(_time: number, delta: number): void {
    this.bubble.update(delta);
  }

  /** Replace the interaction callback at runtime. */
  setOnInteract(fn: () => void): void {
    this.onInteractCallback = fn;
  }

  destroy(fromScene?: boolean): void {
    this.bubble.destroy();
    this.captionText.destroy();
    super.destroy(fromScene);
  }
}
