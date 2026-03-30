import Phaser from 'phaser';
import type { WorldScene } from '../WorldScene';
import type { MiraiState } from '../../miraiSocket';
import { TILE, getRoomById } from '../world/roomDefs';

interface WanderState {
  agentId: number;
  tween: Phaser.Tweens.Tween | null;
  nextWanderTime: number;
}

export class SwarmBehavior {
  private scene: WorldScene;
  private wanderers = new Map<number, WanderState>();
  private bounds = { x: 0, y: 0, w: 0, h: 0 };
  private active = false;

  constructor(scene: WorldScene) {
    this.scene = scene;
  }

  enter(_state: MiraiState): void {
    this.active = true;
    const room = getRoomById('marketplace');
    if (room) {
      const padding = TILE * 2;
      this.bounds = {
        x: room.worldOffset.x * TILE + padding,
        y: room.worldOffset.y * TILE + padding,
        w: room.width * TILE - padding * 2,
        h: room.height * TILE - padding * 2,
      };
    }
  }

  onStateUpdate(_state: MiraiState): void {
    // Nothing continuous to update from state
  }

  tick(time: number, _delta: number): void {
    if (!this.active) return;

    const agentNpcs = (this.scene as any).agentNpcs as Map<number, any>;
    if (!agentNpcs) return;

    for (const [id, agent] of agentNpcs) {
      let ws = this.wanderers.get(id);

      // Initialize wander state for new agents
      if (!ws) {
        ws = {
          agentId: id,
          tween: null,
          nextWanderTime: time + 1000 + Math.random() * 3000,
        };
        this.wanderers.set(id, ws);
      }

      // Only wander if agent has voted (finished processing)
      // and no active tween and time has elapsed
      if (agent.agentData?.vote && !ws.tween && time > ws.nextWanderTime) {
        this.startWander(agent, ws, time);
      }
    }
  }

  private startWander(agent: any, ws: WanderState, _time: number): void {
    // Pick a random nearby point (within 40px but inside marketplace bounds)
    const targetX = Phaser.Math.Clamp(
      agent.x + (Math.random() - 0.5) * 80,
      this.bounds.x,
      this.bounds.x + this.bounds.w,
    );
    const targetY = Phaser.Math.Clamp(
      agent.y + (Math.random() - 0.5) * 80,
      this.bounds.y,
      this.bounds.y + this.bounds.h,
    );

    const dist = Phaser.Math.Distance.Between(agent.x, agent.y, targetX, targetY);
    const duration = (dist / 30) * 1000; // slow wander speed (30 px/s)

    ws.tween = this.scene.tweens.add({
      targets: agent,
      x: targetX,
      y: targetY,
      duration: Math.max(duration, 500),
      ease: 'Sine.easeInOut',
      onComplete: () => {
        ws.tween = null;
        ws.nextWanderTime = Date.now() + 2000 + Math.random() * 4000;
      },
    });
  }

  exit(): void {
    this.active = false;
    for (const ws of this.wanderers.values()) {
      if (ws.tween) ws.tween.stop();
    }
    this.wanderers.clear();
  }

  freeze(): void {
    // Stop wandering but keep agents visible
    for (const ws of this.wanderers.values()) {
      if (ws.tween) ws.tween.stop();
      ws.tween = null;
    }
    this.active = false;
  }
}
