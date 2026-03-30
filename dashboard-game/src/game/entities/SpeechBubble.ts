/**
 * SpeechBubble.ts
 *
 * Typewriter speech bubble that floats above a parent sprite.
 * Ported from eweren's CharacterNode.say() pattern: text is revealed
 * character-by-character at a fixed rate, with a rounded-rect background
 * that resizes to fit the current visible text.
 */

export class SpeechBubble {
  private container: Phaser.GameObjects.Container;
  private bg: Phaser.GameObjects.Graphics;
  private textObj: Phaser.GameObjects.Text;
  private fullText: string = '';
  private displayedChars: number = 0;
  private charRate: number = 28;   // characters per second (eweren pattern)
  private elapsed: number = 0;
  private duration: number = 0;    // ms, 0 = indefinite until hide()
  private active: boolean = false;
  private parent: Phaser.GameObjects.Sprite;
  private scene: Phaser.Scene;

  /** Vertical offset from parent origin to bubble anchor. */
  private static readonly Y_OFFSET = -40;
  /** Horizontal padding inside the bubble background. */
  private static readonly PAD_X = 8;
  /** Vertical padding inside the bubble background. */
  private static readonly PAD_Y = 6;
  /** Height of the small pointer triangle at the bottom. */
  private static readonly POINTER_H = 6;
  /** Corner radius for the rounded rect. */
  private static readonly RADIUS = 6;
  /** Maximum text width before word-wrap kicks in. */
  private static readonly WRAP_WIDTH = 150;
  /** Fade-in / fade-out tween duration in ms. */
  private static readonly FADE_MS = 200;

  constructor(scene: Phaser.Scene, parent: Phaser.GameObjects.Sprite) {
    this.scene = scene;
    this.parent = parent;

    // Background graphics (drawn dynamically as text grows)
    this.bg = scene.add.graphics();

    // Text object — small white monospace, word-wrapped
    this.textObj = scene.add.text(0, 0, '', {
      fontFamily: 'monospace',
      fontSize: '9px',
      color: '#ffffff',
      wordWrap: { width: SpeechBubble.WRAP_WIDTH, useAdvancedWrap: true },
      lineSpacing: 2,
    });
    this.textObj.setOrigin(0.5, 1);

    // Container holds both; positioned above parent each frame
    this.container = scene.add.container(parent.x, parent.y + SpeechBubble.Y_OFFSET, [
      this.bg,
      this.textObj,
    ]);
    this.container.setDepth(100);
    this.container.setAlpha(0);
  }

  /* ------------------------------------------------------------------ */
  /*  Public API                                                         */
  /* ------------------------------------------------------------------ */

  /** Show a message with typewriter reveal. duration in ms; 0 = stay until hide(). */
  show(text: string, duration: number = 5000): void {
    this.fullText = text;
    this.displayedChars = 0;
    this.elapsed = 0;
    this.duration = duration;
    this.active = true;

    // Reset text so the background starts small
    this.textObj.setText('');
    this.redrawBg();

    // Fade in
    this.scene.tweens.killTweensOf(this.container);
    this.scene.tweens.add({
      targets: this.container,
      alpha: 1,
      duration: SpeechBubble.FADE_MS,
    });
  }

  /** Fade out and deactivate. */
  hide(): void {
    if (!this.active) return;
    this.scene.tweens.killTweensOf(this.container);
    this.scene.tweens.add({
      targets: this.container,
      alpha: 0,
      duration: SpeechBubble.FADE_MS,
      onComplete: () => {
        this.active = false;
      },
    });
  }

  /** Called every frame from the owning NPC / entity. */
  update(delta: number): void {
    if (!this.active) return;

    // Follow parent sprite
    this.container.setPosition(this.parent.x, this.parent.y + SpeechBubble.Y_OFFSET);

    // Advance typewriter
    this.elapsed += delta;
    const targetChars = Math.min(
      Math.floor((this.elapsed / 1000) * this.charRate),
      this.fullText.length,
    );

    if (targetChars !== this.displayedChars) {
      this.displayedChars = targetChars;
      this.textObj.setText(this.fullText.substring(0, this.displayedChars));
      this.redrawBg();
    }

    // Auto-hide after duration (counted from when text is fully revealed)
    if (
      this.duration > 0 &&
      this.displayedChars >= this.fullText.length &&
      this.elapsed > (this.fullText.length / this.charRate) * 1000 + this.duration
    ) {
      this.hide();
    }
  }

  /** Remove all game objects. */
  destroy(): void {
    this.container.destroy(true);
  }

  /* ------------------------------------------------------------------ */
  /*  Internal                                                           */
  /* ------------------------------------------------------------------ */

  /** Redraw the rounded-rect background + pointer triangle to fit current text size. */
  private redrawBg(): void {
    this.bg.clear();

    const textW = Math.max(this.textObj.width, 20);
    const textH = Math.max(this.textObj.height, 10);
    const padX = SpeechBubble.PAD_X;
    const padY = SpeechBubble.PAD_Y;
    const r = SpeechBubble.RADIUS;
    const ptrH = SpeechBubble.POINTER_H;

    const boxW = textW + padX * 2;
    const boxH = textH + padY * 2;

    // Semi-transparent dark background
    this.bg.fillStyle(0x1a1a2e, 0.88);

    // Rounded rect centered on container origin, sitting above the pointer
    const x = -boxW / 2;
    const y = -(boxH + ptrH);
    this.bg.fillRoundedRect(x, y, boxW, boxH, r);

    // Small triangle pointer at bottom center
    this.bg.fillTriangle(
      -5, -ptrH,  // left
       5, -ptrH,  // right
       0,  0,     // tip
    );

    // Position text centered inside the box
    this.textObj.setPosition(0, -ptrH - padY);
  }
}
