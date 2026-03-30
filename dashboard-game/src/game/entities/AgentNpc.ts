/**
 * AgentNpc.ts
 *
 * Specialised NPC subclass representing a swarm agent in the War Room.
 * Handles the spawn -> active -> voted lifecycle with visual feedback
 * (tinting, scale pulses, speech bubbles for reasoning excerpts).
 */

import Phaser from 'phaser';
import { Npc } from './Npc';
import type { AgentData, Vote } from '../../miraiSocket';

/** Character skins cycled through for agent NPCs. */
const AGENT_SKINS = [
  'char_015',
  'char_025',
  'char_035',
  'char_045',
  'char_001',
  'char_002',
  'char_003',
  'char_004',
  'char_005',
] as const;

/** Directions cycled through for initial facing. */
const FACING_DIRS = ['down', 'left', 'right', 'up'] as const;

export class AgentNpc extends Npc {
  public agentData: AgentData;

  constructor(
    scene: Phaser.Scene,
    agentData: AgentData,
    worldX: number,
    worldY: number,
  ) {
    const skin = AGENT_SKINS[agentData.id % AGENT_SKINS.length];

    super(scene, {
      id: `agent_${agentData.id}`,
      x: worldX,
      y: worldY,
      skin,
      caption: agentData.persona,
      type: 'dynamic',
      facing: FACING_DIRS[agentData.id % FACING_DIRS.length],
    });

    this.agentData = agentData;

    // --- Spawn animation: scale from 0 to 1 with a bounce ---
    this.setScale(0);
    scene.tweens.add({
      targets: this,
      scaleX: 1,
      scaleY: 1,
      duration: 300,
      ease: 'Back.easeOut',
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Vote lifecycle                                                     */
  /* ------------------------------------------------------------------ */

  /** Visual indicator that this agent is currently evaluating. */
  markActive(): void {
    // Pulse effect — scale up and back three times
    this.scene.tweens.add({
      targets: this,
      scaleX: 1.2,
      scaleY: 1.2,
      duration: 200,
      yoyo: true,
      repeat: 2,
    });

    // Yellow tint to signal "thinking"
    this.setTint(0xaaaa44);
  }

  /** Mark this agent as having voted and display a reasoning excerpt. */
  setVoted(vote: Vote, reasoning: string): void {
    // Tint green for positive, red for negative
    const color = vote === 'positive' ? 0x44cc66 : 0xcc4444;
    this.setTint(color);

    // Pop animation
    this.scene.tweens.add({
      targets: this,
      scaleX: 1.3,
      scaleY: 1.3,
      duration: 150,
      yoyo: true,
    });

    // Show a truncated reasoning bubble
    const preview =
      reasoning.length > 60 ? reasoning.substring(0, 60) + '...' : reasoning;
    this.say(preview, 3500);

    // Persist into backing data
    this.agentData.vote = vote;
    this.agentData.reasoning = reasoning;
  }

  /** Reset visual state (clear tint, hide bubble). */
  resetVisual(): void {
    this.clearTint();
    this.setScale(1);
  }
}
