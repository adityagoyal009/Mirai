import Phaser from 'phaser';

const CHARACTER_IDS = [
  '001', '002', '003', '004', '005',
  '009', '015', '025', '035', '045',
] as const;

const TILESETS: { key: string; file: string; width: number; height: number }[] = [
  { key: 'ground',     file: 'ground.png',     width: 768,  height: 384  },
  { key: 'grasslands', file: 'grasslands.png', width: 1024, height: 1024 },
  { key: 'village',    file: 'village.png',    width: 1024, height: 1024 },
];

const FURNITURE_KEYS = [
  'BIN', 'BOOKSHELF', 'CACTUS', 'CLOCK', 'COFFEE', 'COFFEE_TABLE',
  'CUSHIONED_BENCH', 'CUSHIONED_CHAIR_BACK', 'CUSHIONED_CHAIR_FRONT',
  'CUSHIONED_CHAIR_SIDE', 'DESK_FRONT', 'DESK_SIDE', 'DOUBLE_BOOKSHELF',
  'HANGING_PLANT', 'LARGE_PAINTING', 'LARGE_PLANT', 'PC_BACK',
  'PC_FRONT_OFF', 'PC_FRONT_ON_1', 'PC_FRONT_ON_2', 'PC_FRONT_ON_3',
  'PC_SIDE', 'PLANT', 'PLANT_2', 'POT', 'SMALL_PAINTING',
  'SMALL_PAINTING_2', 'SMALL_TABLE_FRONT', 'SMALL_TABLE_SIDE',
  'SOFA_BACK', 'SOFA_FRONT', 'SOFA_SIDE', 'TABLE_FRONT', 'WHITEBOARD',
  'WOODEN_BENCH', 'WOODEN_CHAIR_BACK', 'WOODEN_CHAIR_FRONT',
  'WOODEN_CHAIR_SIDE',
] as const;

const FLOOR_COUNT = 9;  // floor_0.png through floor_8.png

export class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BootScene' });
  }

  preload(): void {
    /* ---- loading bar ---- */
    const { width, height } = this.cameras.main;
    const barWidth = 320;
    const barHeight = 24;
    const barX = (width - barWidth) / 2;
    const barY = (height - barHeight) / 2;

    const bgBar = this.add.graphics();
    bgBar.fillStyle(0x444444, 1);
    bgBar.fillRect(barX, barY, barWidth, barHeight);

    const progressBar = this.add.graphics();

    const loadingText = this.add.text(width / 2, barY - 24, 'Loading...', {
      fontFamily: 'monospace',
      fontSize: '14px',
      color: '#e0e0e0',
    }).setOrigin(0.5);

    this.load.on('progress', (value: number) => {
      progressBar.clear();
      progressBar.fillStyle(0x6c63ff, 1);
      progressBar.fillRect(barX + 2, barY + 2, (barWidth - 4) * value, barHeight - 4);
    });

    this.load.on('complete', () => {
      bgBar.destroy();
      progressBar.destroy();
      loadingText.destroy();
    });

    /* ---- character spritesheets ---- */
    for (const id of CHARACTER_IDS) {
      this.load.spritesheet(
        `char_${id}`,
        `/sprites/characters/Character_${id}.png`,
        { frameWidth: 48, frameHeight: 48 },
      );
    }

    /* ---- tileset spritesheets ---- */
    for (const ts of TILESETS) {
      this.load.spritesheet(
        ts.key,
        `/sprites/tilesets/${ts.file}`,
        { frameWidth: 32, frameHeight: 32 },
      );
    }

    /* ---- furniture images ---- */
    for (const key of FURNITURE_KEYS) {
      this.load.image(key, `/sprites/furniture/${key}.png`);
    }

    /* ---- floor tiles ---- */
    for (let i = 0; i < FLOOR_COUNT; i++) {
      this.load.image(`floor_${i}`, `/sprites/floors/floor_${i}.png`);
    }

    /* ---- wall tile ---- */
    this.load.image('wall_0', '/sprites/walls/wall_0.png');

    /* ---- sound effects ---- */
    this.load.audio('snd_click', '/sounds/click.mp3');
    this.load.audio('snd_confirm', '/sounds/confirm.mp3');
    this.load.audio('snd_select', '/sounds/select.mp3');
    this.load.audio('snd_bass', '/sounds/bass.mp3');
    this.load.audio('snd_ticket', '/sounds/ticket.ogg');
    this.load.audio('snd_back', '/sounds/back.mp3');
  }

  create(): void {
    this.scene.start('CharacterSelectScene');
  }
}
