import Phaser from 'phaser';
import { BootScene } from './BootScene';
import { CharacterSelectScene } from './CharacterSelectScene';
import { WorldScene } from './WorldScene';

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: 800,
  height: 600,
  backgroundColor: '#0a0a15',
  pixelArt: true,
  parent: 'phaser-container',
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
  physics: {
    default: 'arcade',
    arcade: {
      gravity: { x: 0, y: 0 },
      debug: false,
    },
  },
  scene: [BootScene, CharacterSelectScene, WorldScene],
};
