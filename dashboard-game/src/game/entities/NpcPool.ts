import Phaser from 'phaser';
import { AgentNpc } from './AgentNpc';
import type { AgentData } from '../../miraiSocket';

const MAX_VISIBLE_SPRITES = 60;

export class NpcPool {
  private scene: Phaser.Scene;
  private allAgents = new Map<number, { data: AgentData; worldX: number; worldY: number }>();
  private activeSprites = new Map<number, AgentNpc>();
  private recyclePool: AgentNpc[] = [];

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  /** Register an agent with a world position. May or may not create a sprite. */
  add(agentData: AgentData, worldX: number, worldY: number): AgentNpc | null {
    this.allAgents.set(agentData.id, { data: agentData, worldX, worldY });

    // If under the sprite limit and near camera, create a sprite immediately
    if (this.activeSprites.size < MAX_VISIBLE_SPRITES && this.isNearCamera(worldX, worldY)) {
      return this.activateSprite(agentData, worldX, worldY);
    }
    return null;
  }

  /** Get the sprite for an agent (may be null if off-screen/pooled). */
  getSprite(id: number): AgentNpc | undefined {
    return this.activeSprites.get(id);
  }

  /** Get all registered agent data regardless of sprite state. */
  getAllData(): Map<number, { data: AgentData; worldX: number; worldY: number }> {
    return this.allAgents;
  }

  /** Call each frame to activate/deactivate sprites based on camera position. */
  updateVisibility(camera: Phaser.Cameras.Scene2D.Camera): void {
    const bounds = new Phaser.Geom.Rectangle(
      camera.scrollX - camera.width,
      camera.scrollY - camera.height,
      camera.width * 3,
      camera.height * 3,
    );

    // Deactivate sprites that are too far from camera
    for (const [id, sprite] of this.activeSprites) {
      if (!bounds.contains(sprite.x, sprite.y)) {
        this.deactivateSprite(id, sprite);
      }
    }

    // Activate sprites for agents near camera (up to limit)
    if (this.activeSprites.size < MAX_VISIBLE_SPRITES) {
      for (const [id, entry] of this.allAgents) {
        if (this.activeSprites.has(id)) continue;
        if (this.activeSprites.size >= MAX_VISIBLE_SPRITES) break;
        if (bounds.contains(entry.worldX, entry.worldY)) {
          this.activateSprite(entry.data, entry.worldX, entry.worldY);
        }
      }
    }
  }

  private activateSprite(data: AgentData, x: number, y: number): AgentNpc {
    let sprite = this.recyclePool.pop();
    if (sprite) {
      // Reuse pooled sprite
      sprite.setPosition(x, y);
      sprite.setVisible(true);
      sprite.setActive(true);
      sprite.agentData = data;
    } else {
      // Create new sprite
      sprite = new AgentNpc(this.scene, data, x, y);
    }
    this.activeSprites.set(data.id, sprite);

    // Apply vote state if already voted
    if (data.vote) {
      sprite.setVoted(data.vote, data.reasoning || '');
    }

    return sprite;
  }

  private deactivateSprite(id: number, sprite: AgentNpc): void {
    sprite.setVisible(false);
    sprite.setActive(false);
    this.activeSprites.delete(id);
    this.recyclePool.push(sprite);
  }

  private isNearCamera(x: number, y: number): boolean {
    const cam = this.scene.cameras.main;
    const dx = Math.abs(x - (cam.scrollX + cam.width / 2));
    const dy = Math.abs(y - (cam.scrollY + cam.height / 2));
    return dx < cam.width * 1.5 && dy < cam.height * 1.5;
  }

  /** Mark an agent as active (visual pulse). */
  markActive(id: number): void {
    const sprite = this.activeSprites.get(id);
    if (sprite) sprite.markActive();
    // Also update stored data so newly activated sprites get the state
    const entry = this.allAgents.get(id);
    if (entry) entry.data.activity = 'evaluating';
  }

  /** Mark an agent as voted. */
  setVoted(id: number, vote: 'positive' | 'negative', reasoning: string): void {
    const sprite = this.activeSprites.get(id);
    if (sprite) sprite.setVoted(vote, reasoning);
    // Update stored data
    const entry = this.allAgents.get(id);
    if (entry) {
      entry.data.vote = vote;
      entry.data.reasoning = reasoning;
    }
  }

  /** Remove all agents and sprites. */
  clear(): void {
    for (const [, sprite] of this.activeSprites) {
      sprite.destroy();
    }
    for (const sprite of this.recyclePool) {
      sprite.destroy();
    }
    this.activeSprites.clear();
    this.recyclePool = [];
    this.allAgents.clear();
  }

  get totalCount(): number { return this.allAgents.size; }
  get visibleCount(): number { return this.activeSprites.size; }
}
