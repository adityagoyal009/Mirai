import Phaser from 'phaser';
import { roomDefs, TILE } from './roomDefs';

interface ParticleConfig {
  color: number;
  count: number;
  alpha: number;
  lifespan: number;
  speedX: { min: number; max: number };
  speedY: { min: number; max: number };
  scale: { start: number; end: number };
}

const ROOM_PARTICLES: Record<string, ParticleConfig> = {
  lobby: { color: 0xffeecc, count: 10, alpha: 0.2, lifespan: 3000, speedX: { min: -5, max: 5 }, speedY: { min: -10, max: -3 }, scale: { start: 1.5, end: 0.5 } },
  library: { color: 0xffffff, count: 8, alpha: 0.12, lifespan: 4000, speedX: { min: -8, max: 8 }, speedY: { min: -3, max: 3 }, scale: { start: 1, end: 0.3 } },
  council: { color: 0xcc66ff, count: 6, alpha: 0.25, lifespan: 1200, speedX: { min: -15, max: 15 }, speedY: { min: -15, max: 15 }, scale: { start: 2, end: 0 } },
  marketplace: { color: 0xffcc44, count: 12, alpha: 0.12, lifespan: 3500, speedX: { min: -3, max: 3 }, speedY: { min: 3, max: 8 }, scale: { start: 1, end: 0.5 } },
  time_room: { color: 0x66ccff, count: 8, alpha: 0.2, lifespan: 2500, speedX: { min: -10, max: 10 }, speedY: { min: -10, max: 10 }, scale: { start: 1.5, end: 0 } },
  archive: { color: 0x3344aa, count: 5, alpha: 0.18, lifespan: 3000, speedX: { min: -2, max: 2 }, speedY: { min: 3, max: 8 }, scale: { start: 1, end: 0.5 } },
};

export class AmbientParticles {
  static decorateAll(scene: Phaser.Scene): void {
    // Generate a tiny 2x2 white pixel texture for particles
    if (!scene.textures.exists('particle_dot')) {
      const gfx = scene.add.graphics();
      gfx.fillStyle(0xffffff, 1);
      gfx.fillRect(0, 0, 2, 2);
      gfx.generateTexture('particle_dot', 2, 2);
      gfx.destroy();
    }

    for (const room of roomDefs) {
      if (!room.label) continue;
      const config = ROOM_PARTICLES[room.id];
      if (!config) continue;

      const ox = room.worldOffset.x * TILE;
      const oy = room.worldOffset.y * TILE;
      const rw = room.width * TILE;
      const rh = room.height * TILE;
      const padding = TILE;

      const emitter = scene.add.particles(ox + rw / 2, oy + rh / 2, 'particle_dot', {
        lifespan: config.lifespan,
        speed: { min: 5, max: 15 },
        speedX: config.speedX,
        speedY: config.speedY,
        scale: config.scale,
        alpha: { start: config.alpha, end: 0 },
        tint: config.color,
        frequency: config.lifespan / config.count,
        emitZone: {
          type: 'random' as const,
          source: new Phaser.Geom.Rectangle(
            -(rw / 2 - padding),
            -(rh / 2 - padding),
            rw - padding * 2,
            rh - padding * 2,
          ),
        } as Phaser.Types.GameObjects.Particles.ParticleEmitterRandomZoneConfig,
        quantity: 1,
      });
      emitter.setDepth(2);
    }
  }
}
