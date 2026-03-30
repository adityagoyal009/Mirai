/**
 * Player.ts
 *
 * Player-controlled character sprite with WASD + arrow-key movement,
 * directional walk/idle animations, and a freeze flag for cutscenes.
 */

import { createCharacterAnims } from '../sprites/characterAnims';

export class Player extends Phaser.Physics.Arcade.Sprite {
  private speed = 160;
  private currentDirection: string = 'down';
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: {
    W: Phaser.Input.Keyboard.Key;
    A: Phaser.Input.Keyboard.Key;
    S: Phaser.Input.Keyboard.Key;
    D: Phaser.Input.Keyboard.Key;
  };
  private skinKey: string;

  /** When true the player cannot move and velocity is zeroed each frame. */
  public frozen = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    skinKey: string = 'char_009',
  ) {
    super(scene, x, y, skinKey, 0);
    this.skinKey = skinKey;

    // Ensure animations exist for this skin
    createCharacterAnims(scene, skinKey);

    // Add to scene + physics world
    scene.add.existing(this);
    scene.physics.add.existing(this);

    // Smaller hitbox (24x24) centered within the 48x48 sprite frame
    const body = this.body as Phaser.Physics.Arcade.Body;
    body.setSize(24, 24);
    body.setOffset(12, 20);

    this.setCollideWorldBounds(true);
    this.setDepth(5);

    // Input setup
    this.cursors = scene.input.keyboard!.createCursorKeys();
    this.wasd = {
      W: scene.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.W),
      A: scene.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.A),
      S: scene.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.S),
      D: scene.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D),
    };
  }

  update(): void {
    if (this.frozen) {
      this.setVelocity(0);
      return;
    }

    // Read input
    const left = this.cursors.left.isDown || this.wasd.A.isDown;
    const right = this.cursors.right.isDown || this.wasd.D.isDown;
    const up = this.cursors.up.isDown || this.wasd.W.isDown;
    const down = this.cursors.down.isDown || this.wasd.S.isDown;

    // Reset velocity each frame
    this.setVelocity(0);

    // Horizontal
    if (left) {
      this.setVelocityX(-this.speed);
      this.currentDirection = 'left';
    } else if (right) {
      this.setVelocityX(this.speed);
      this.currentDirection = 'right';
    }

    // Vertical
    if (up) {
      this.setVelocityY(-this.speed);
      this.currentDirection = 'up';
    } else if (down) {
      this.setVelocityY(this.speed);
      this.currentDirection = 'down';
    }

    // Normalize diagonal movement so speed stays consistent
    const vel = this.body!.velocity;
    if (vel.x !== 0 && vel.y !== 0) {
      vel.normalize().scale(this.speed);
    }

    // Play the appropriate animation + footstep sound
    if (vel.x !== 0 || vel.y !== 0) {
      this.anims.play(`${this.skinKey}_walk_${this.currentDirection}`, true);
      // Footstep sound (SoundManager accessed from scene)
      const sm = (this.scene as any).soundManager;
      if (sm) sm.playFootstep();
    } else {
      this.anims.play(`${this.skinKey}_idle_${this.currentDirection}`, true);
    }
  }

  /** Returns the direction the player is currently facing. */
  getDirection(): string {
    return this.currentDirection;
  }
}
