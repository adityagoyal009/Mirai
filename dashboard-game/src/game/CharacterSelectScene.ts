import Phaser from 'phaser';
import { createCharacterAnims } from './sprites/characterAnims';

const SKINS = [
  { key: 'char_001', label: 'Agent Alpha' },
  { key: 'char_002', label: 'Agent Beta' },
  { key: 'char_003', label: 'Agent Gamma' },
  { key: 'char_004', label: 'Agent Delta' },
  { key: 'char_005', label: 'Agent Epsilon' },
  { key: 'char_009', label: 'Agent Zeta' },
  { key: 'char_015', label: 'Agent Eta' },
  { key: 'char_025', label: 'Agent Theta' },
  { key: 'char_035', label: 'Agent Iota' },
  { key: 'char_045', label: 'Agent Kappa' },
];

export class CharacterSelectScene extends Phaser.Scene {
  constructor() {
    super({ key: 'CharacterSelectScene' });
  }

  create(): void {
    const { width, height } = this.cameras.main;

    // Dark background
    this.cameras.main.setBackgroundColor('#0a0a15');

    // Title
    this.add.text(width / 2, 40, 'CHOOSE YOUR AVATAR', {
      fontFamily: 'monospace',
      fontSize: '18px',
      color: '#4a9eff',
      letterSpacing: 4,
    }).setOrigin(0.5);

    this.add.text(width / 2, 65, 'Click to select', {
      fontFamily: 'monospace',
      fontSize: '10px',
      color: '#555',
    }).setOrigin(0.5);

    // Grid of characters — 5 columns x 2 rows
    const cols = 5;
    const cellW = 120;
    const cellH = 120;
    const startX = (width - cols * cellW) / 2 + cellW / 2;
    const startY = 120;

    SKINS.forEach((skin, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cx = startX + col * cellW;
      const cy = startY + row * cellH;

      // Ensure animations exist
      createCharacterAnims(this, skin.key);

      // Character sprite (idle_down)
      const sprite = this.add.sprite(cx, cy, skin.key, 0);
      sprite.setScale(2);
      sprite.anims.play(`${skin.key}_idle_down`);

      // Selection highlight box (hidden by default)
      const highlight = this.add.rectangle(cx, cy, 80, 90, 0x4a9eff, 0.15);
      highlight.setStrokeStyle(2, 0x4a9eff, 0.5);
      highlight.setVisible(false);

      // Label
      const label = this.add.text(cx, cy + 45, skin.label, {
        fontFamily: 'monospace',
        fontSize: '8px',
        color: '#888',
        align: 'center',
      }).setOrigin(0.5);

      // Make interactive
      sprite.setInteractive({ useHandCursor: true });
      sprite.on('pointerover', () => {
        highlight.setVisible(true);
        sprite.setScale(2.5);
        label.setColor('#fff');
      });
      sprite.on('pointerout', () => {
        highlight.setVisible(false);
        sprite.setScale(2);
        label.setColor('#888');
      });
      sprite.on('pointerdown', () => {
        // Store selection and start the game
        this.scene.start('WorldScene', { selectedSkin: skin.key });
      });
    });
  }
}
