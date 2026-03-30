import Phaser from 'phaser';
import { roomDefs, TILE } from './world/roomDefs';
import { RoomRenderer } from './world/roomRenderer';
import { Player } from './entities/Player';
import { Npc } from './entities/Npc';
import { AgentNpc } from './entities/AgentNpc';
import { createCharacterAnims } from './sprites/characterAnims';
import { DialogManager, type DialogState } from './dialog/DialogManager';
import { PhaseManager } from './phases/PhaseManager';
import { RoomDecorator } from './world/roomDecorator';
import { NpcPool } from './entities/NpcPool';
import { GateManager } from './world/GateManager';
import { SoundManager } from './audio/SoundManager';
import { TutorialArrow } from './world/TutorialArrow';
import { AmbientParticles } from './world/AmbientParticles';
import { RoomAnnouncer } from './world/RoomAnnouncer';
import { RoomLighting } from './world/RoomLighting';
import type { AgentData, MiraiState } from '../miraiSocket';

/** Phase-name to room-id lookup derived from roomDefs. */
const phaseRoomMap: Record<string, string> = {};
for (const room of roomDefs) {
  if (room.phase) {
    phaseRoomMap[room.phase] = room.id;
  }
}

export class WorldScene extends Phaser.Scene {
  public player!: Player;
  public dialogManager!: DialogManager;
  public phaseManager!: PhaseManager;
  public npcs: Npc[] = [];

  private wallLayer!: Phaser.Physics.Arcade.StaticGroup;
  private objectLayer!: Phaser.Physics.Arcade.StaticGroup;
  private agentNpcs = new Map<number, AgentNpc>();
  private npcPool!: NpcPool;
  public gateManager!: GateManager;
  public soundManager!: SoundManager;
  private tutorialArrow!: TutorialArrow;
  private roomAnnouncer!: RoomAnnouncer;
  private roomLighting!: RoomLighting;
  private nearestNpc: Npc | null = null;
  private eKey!: Phaser.Input.Keyboard.Key;

  // Callbacks for React bridge
  private onNearestNpcChange?: (npc: { id: string; caption: string } | null) => void;
  private onDialogChange?: (state: DialogState) => void;

  constructor() {
    super({ key: 'WorldScene' });
  }

  /* ------------------------------------------------------------------ */
  /*  Lifecycle                                                          */
  /* ------------------------------------------------------------------ */

  create(data?: { selectedSkin?: string }): void {
    // 1. Player animations
    const playerSkin = data?.selectedSkin || 'char_009';
    createCharacterAnims(this, playerSkin);

    // 2. Build world
    const { wallLayer, objectLayer, worldWidth, worldHeight, spawnPoint } =
      RoomRenderer.renderAll(this, roomDefs);

    this.wallLayer = wallLayer;
    this.objectLayer = objectLayer;

    // 3. Player
    const spawnX = spawnPoint?.x ?? 400;
    const spawnY = spawnPoint?.y ?? 300;
    this.player = new Player(this, spawnX, spawnY, playerSkin);

    // 4. Camera
    this.cameras.main.startFollow(this.player, true, 0.08, 0.08);
    this.cameras.main.setBounds(0, 0, worldWidth, worldHeight);
    this.physics.world.setBounds(0, 0, worldWidth, worldHeight);

    // 5. Collisions
    this.physics.add.collider(this.player, this.wallLayer);
    this.physics.add.collider(this.player, this.objectLayer);

    // 6. Visual polish
    RoomDecorator.decorateAll(this);

    // 7. NPC pool for swarm performance
    this.npcPool = new NpcPool(this);

    // 8. Spawn static NPCs from room defs
    this.spawnStaticNpcs();

    // 9. Dialog system
    this.dialogManager = new DialogManager(this);
    this.dialogManager.onChange((state) => {
      // Freeze/unfreeze player during dialog
      this.player.frozen = state.active;
      // Disable/enable Phaser keyboard so React dialog can capture keys
      if (state.active) {
        this.input.keyboard?.disableGlobalCapture();
      } else {
        this.input.keyboard?.enableGlobalCapture();
      }
      this.onDialogChange?.(state);
    });

    // Listen for dialog completion (e.g., intake desk triggers analysis)
    this.events.on('dialog:complete', (dialogId: string, responses: Record<string, string>) => {
      this.events.emit('analysis:start', dialogId, responses);
      // Unlock first gate when intake dialog finishes
      if (dialogId === 'intake_welcome') {
        this.gateManager.unlockCorridor('corridor_lobby_library');
      }
    });

    // 10. Gate system — locked barriers between rooms
    this.gateManager = new GateManager(this, this.wallLayer);

    // 11. Phase manager
    this.phaseManager = new PhaseManager(this);

    // 12. Sound manager
    this.soundManager = new SoundManager(this);

    // 13. Tutorial arrow ("Start here!")
    this.tutorialArrow = new TutorialArrow(this);

    // 14. Room announcer (entry banners)
    this.roomAnnouncer = new RoomAnnouncer(this);

    // 15. Room lighting (ambient tint overlays)
    this.roomLighting = new RoomLighting(this);

    // 16. Ambient particles (per-room floating effects)
    AmbientParticles.decorateAll(this);

    // 17. Camera zoom for better pixel art visibility
    this.cameras.main.setZoom(1.5);

    // 18. E key for interaction
    this.eKey = this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.E);
    this.eKey.on('down', () => {
      if (this.dialogManager.state.active) return;
      if (this.nearestNpc && this.nearestNpc.inRange) {
        this.nearestNpc.interact();
      }
    });
  }

  update(_time: number, delta: number): void {
    if (!this.player) return;

    this.player.update();
    this.phaseManager.tick(_time, delta);
    this.npcPool.updateVisibility(this.cameras.main);
    this.gateManager.checkProximity(this.player.x, this.player.y);
    this.tutorialArrow.checkDismiss(this.player.x, this.player.y);
    this.roomAnnouncer.update(this.player.x, this.player.y);
    this.roomLighting.update(this.player.x, this.player.y);

    // Update all NPCs: proximity check + speech bubble
    let closest: Npc | null = null;
    let closestDist = Infinity;

    for (const npc of this.npcs) {
      npc.checkProximity(this.player);
      npc.update(_time, delta);

      if (npc.inRange) {
        const d = Phaser.Math.Distance.Between(npc.x, npc.y, this.player.x, this.player.y);
        if (d < closestDist) {
          closestDist = d;
          closest = npc;
        }
      }
    }

    // Update agent NPCs too
    for (const [, agentNpc] of this.agentNpcs) {
      agentNpc.checkProximity(this.player);
      agentNpc.update(_time, delta);

      if (agentNpc.inRange) {
        const d = Phaser.Math.Distance.Between(agentNpc.x, agentNpc.y, this.player.x, this.player.y);
        if (d < closestDist) {
          closestDist = d;
          closest = agentNpc;
        }
      }
    }

    // Track nearest NPC changes for the HUD prompt
    if (closest !== this.nearestNpc) {
      this.nearestNpc = closest;
      this.onNearestNpcChange?.(
        closest ? { id: closest.npcId, caption: closest.caption } : null
      );
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Static NPC spawning                                                */
  /* ------------------------------------------------------------------ */

  private spawnStaticNpcs(): void {
    for (const room of roomDefs) {
      for (const def of room.staticNpcs) {
        const worldX = (room.worldOffset.x + def.tile.x) * TILE + TILE / 2;
        const worldY = (room.worldOffset.y + def.tile.y) * TILE + TILE / 2;

        const npc = new Npc(this, {
          id: def.id,
          x: worldX,
          y: worldY,
          skin: def.skin,
          caption: def.caption,
          type: def.type,
          facing: def.facing,
          onInteract: () => {
            if (def.dialogId) {
              this.dialogManager.startDialog(def.dialogId, def.caption || def.id);
            } else {
              npc.say('...', 2000);
            }
          },
        });

        // Collide player with NPC
        this.physics.add.collider(this.player, npc);
        this.npcs.push(npc);
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Agent NPC management (for swarm phase)                             */
  /* ------------------------------------------------------------------ */

  spawnAgentNpc(agentData: AgentData): void {
    if (this.agentNpcs.has(agentData.id)) return;

    // Find marketplace room bounds
    const room = roomDefs.find((r) => r.id === 'marketplace');
    if (!room) return;

    const ox = room.worldOffset.x * TILE;
    const oy = room.worldOffset.y * TILE;
    const padding = TILE * 2;
    const worldX = ox + padding + Math.random() * (room.width * TILE - padding * 2);
    const worldY = oy + padding + Math.random() * (room.height * TILE - padding * 2);

    const agent = new AgentNpc(this, agentData, worldX, worldY);
    agent.setOnInteract(() => {
      this.events.emit('agent:inspect', agentData);
    });

    this.physics.add.collider(this.player, agent);
    this.agentNpcs.set(agentData.id, agent);
  }

  activateAgentNpc(id: number): void {
    this.agentNpcs.get(id)?.markActive();
  }

  agentVoted(id: number, vote: 'positive' | 'negative', reasoning: string): void {
    this.agentNpcs.get(id)?.setVoted(vote, reasoning);
  }

  clearAgents(): void {
    for (const [, agent] of this.agentNpcs) {
      agent.destroy();
    }
    this.agentNpcs.clear();
  }

  /* ------------------------------------------------------------------ */
  /*  React bridge                                                       */
  /* ------------------------------------------------------------------ */

  getPlayerPosition(): { x: number; y: number } {
    if (!this.player) return { x: 0, y: 0 };
    return { x: this.player.x, y: this.player.y };
  }

  getPhaseRoomId(phase: string): string | undefined {
    return phaseRoomMap[phase];
  }

  onNearestNpc(fn: (npc: { id: string; caption: string } | null) => void): void {
    this.onNearestNpcChange = fn;
  }

  onDialog(fn: (state: DialogState) => void): void {
    this.onDialogChange = fn;
  }
}
