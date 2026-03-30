/**
 * sceneApi.ts
 *
 * Contract that WorldScene exposes to the React bridge layer.
 * Methods marked with `?` are planned for later sprints.
 */

export interface SceneApi {
  /** Current pixel position of the player sprite. */
  getPlayerPosition(): { x: number; y: number };

  /** Name of the room / zone the player is currently inside. */
  getCurrentRoom(): string;

  // -------------------------------------------------------------------------
  // Phase-driven methods (Sprint 3+)
  // -------------------------------------------------------------------------

  /** Spawn an NPC representing an AI agent. */
  spawnAgentNpc?(agentData: unknown): void;

  /** Visually activate an agent NPC (e.g. glow, speech bubble). */
  activateAgentNpc?(id: number): void;

  /** Show a vote badge / animation on the agent NPC. */
  agentVoted?(id: number, vote: string, reasoning: string): void;

  /** Remove all agent NPCs from the scene. */
  clearAgents?(): void;
}
