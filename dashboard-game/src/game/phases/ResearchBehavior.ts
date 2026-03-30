/**
 * ResearchBehavior.ts
 *
 * Library phase: research agents walk between bookshelves, pause to "read",
 * show live search snippets, and display progress. Press E for full summary.
 */

import Phaser from 'phaser';
import type { WorldScene } from '../WorldScene';
import type { MiraiState } from '../../miraiSocket';
import { Npc } from '../entities/Npc';
import { TILE, getRoomById } from '../world/roomDefs';

// Bookshelf positions in library LOCAL tile coords (from roomDefs furniture)
// Waypoints matching new library furniture layout (local tile coords)
// Agents walk NEXT TO shelves/desks, not on top of them
const BOOKSHELF_TILES = [
  { x: 3, y: 2 },  // near left shelf top
  { x: 3, y: 4 },  // near left shelf mid
  { x: 3, y: 11 }, // near left shelf bottom
  { x: 16, y: 2 }, // near right shelf top
  { x: 16, y: 4 }, // near right shelf mid
  { x: 16, y: 11 }, // near right shelf bottom
  { x: 9, y: 3 },  // study desk top
  { x: 9, y: 11 }, // study desk bottom
  { x: 13, y: 3 }, // island bookshelf top
  { x: 13, y: 11 }, // island bookshelf bottom
];

const SEARCH_SNIPPETS = [
  'Scanning market reports...',
  'Found: Industry trend analysis',
  'Reading: Competitor landscape',
  'Parsing financial data...',
  'Found: TAM/SAM breakdown',
  'Analyzing patent filings...',
  'Found: Customer reviews',
  'Searching: Regulatory filings',
  'Found: Pricing benchmarks',
  'Indexing research papers...',
  'Found: Market sizing study',
  'Reading: Due diligence notes',
  'Found: Growth trajectory data',
  'Scanning news articles...',
  'Found: Funding round data',
];

interface ResearchAgent {
  npc: Npc;
  waypointIndex: number;
  waypoints: { x: number; y: number }[];
  state: 'walking' | 'reading' | 'idle';
  readTimer: number;
  snippetIndex: number;
  tween: Phaser.Tweens.Tween | null;
}

export class ResearchBehavior {
  private scene: WorldScene;
  private agents: ResearchAgent[] = [];
  private summaryText: string = '';
  private progressText: Phaser.GameObjects.Text | null = null;
  private sourcesFound = 0;
  private totalSources = 0;
  private roomOx = 0;
  private roomOy = 0;

  constructor(scene: WorldScene) {
    this.scene = scene;
  }

  enter(_state: MiraiState): void {
    const room = getRoomById('library');
    if (!room) return;

    this.roomOx = room.worldOffset.x;
    this.roomOy = room.worldOffset.y;
    const ox = this.roomOx * TILE;
    const oy = this.roomOy * TILE;

    // Flash the library
    const rw = room.width * TILE;
    const rh = room.height * TILE;
    const flash = this.scene.add.rectangle(
      ox + rw / 2, oy + rh / 2, rw, rh, 0x4a9eff, 0.1,
    );
    flash.setDepth(2);
    this.scene.tweens.add({
      targets: flash, alpha: 0, duration: 1500,
      onComplete: () => flash.destroy(),
    });

    // Progress counter in top area of library
    this.progressText = this.scene.add.text(
      ox + rw / 2, oy + TILE + 24,
      'Sources: 0 | Searching...',
      {
        fontFamily: 'monospace',
        fontSize: '9px',
        color: '#4a9eff',
        backgroundColor: '#0a0a1acc',
        padding: { x: 8, y: 3 },
        align: 'center',
      },
    );
    this.progressText.setOrigin(0.5);
    this.progressText.setDepth(15);

    // Spawn 4 research agents with bookshelf waypoint routes
    const skins = ['char_025', 'char_035', 'char_045', 'char_005'];
    const names = ['Researcher Alpha', 'Researcher Beta', 'Researcher Gamma', 'Researcher Delta'];

    for (let i = 0; i < 4; i++) {
      // Each agent gets a shuffled subset of bookshelf waypoints
      const waypoints = Phaser.Utils.Array.Shuffle([...BOOKSHELF_TILES])
        .slice(0, 4 + Math.floor(Math.random() * 3))
        .map((t) => ({
          x: (this.roomOx + t.x) * TILE + TILE / 2,
          y: (this.roomOy + t.y) * TILE + TILE / 2,
        }));

      const startWp = waypoints[0];
      const npc = new Npc(this.scene, {
        id: `research_agent_${i}`,
        x: startWp.x,
        y: startWp.y,
        skin: skins[i],
        caption: names[i],
        type: 'dynamic',
        facing: 'down',
        onInteract: () => {
          const full = this.summaryText || 'Still searching... Check back soon.';
          npc.say(full, 6000);
        },
      });

      const agent: ResearchAgent = {
        npc,
        waypointIndex: 0,
        waypoints,
        state: 'idle',
        readTimer: 0,
        snippetIndex: (i * 4) % SEARCH_SNIPPETS.length,
        tween: null,
      };

      this.agents.push(agent);

      // Start first walk after a staggered delay
      this.scene.time.delayedCall(500 + i * 400, () => {
        this.walkToNextWaypoint(agent);
      });
    }
  }

  private walkToNextWaypoint(agent: ResearchAgent): void {
    if (agent.state === 'reading') return;

    agent.waypointIndex = (agent.waypointIndex + 1) % agent.waypoints.length;
    const target = agent.waypoints[agent.waypointIndex];
    const dist = Phaser.Math.Distance.Between(agent.npc.x, agent.npc.y, target.x, target.y);
    const speed = 60; // px per second
    const duration = (dist / speed) * 1000;

    agent.state = 'walking';

    // Determine walk direction for animation
    const dx = target.x - agent.npc.x;
    const dy = target.y - agent.npc.y;
    const dir = Math.abs(dx) > Math.abs(dy)
      ? (dx > 0 ? 'right' : 'left')
      : (dy > 0 ? 'down' : 'up');

    // Play walk animation
    const skinKey = (agent.npc as any).skinKey || 'char_025';
    if (agent.npc.anims) {
      agent.npc.anims.play(`${skinKey}_walk_${dir}`, true);
    }

    agent.tween = this.scene.tweens.add({
      targets: agent.npc,
      x: target.x,
      y: target.y,
      duration: Math.max(duration, 800),
      ease: 'Linear',
      onComplete: () => {
        // Arrived at bookshelf — start reading
        agent.state = 'reading';
        agent.readTimer = 0;

        // Idle animation facing the bookshelf
        if (agent.npc.anims) {
          agent.npc.anims.play(`${skinKey}_idle_${dir}`, true);
        }

        // Show a search snippet
        const snippet = SEARCH_SNIPPETS[agent.snippetIndex % SEARCH_SNIPPETS.length];
        agent.snippetIndex++;
        agent.npc.say(snippet, 2000);
      },
    });
  }

  onStateUpdate(state: MiraiState): void {
    if (state.researchSummary) {
      this.summaryText = state.researchSummary;
    }

    // Update progress from researchSummary length as a rough proxy
    // The actual findings count comes in researchComplete but we approximate during
    if (state.researchSummary) {
      this.sourcesFound = Math.min(
        Math.floor(state.researchSummary.length / 30),
        20,
      );
    }

    if (this.progressText) {
      this.progressText.setText(
        `Sources: ${this.sourcesFound}${this.totalSources ? '/' + this.totalSources : ''} | Searching...`,
      );
    }
  }

  tick(_time: number, delta: number): void {
    for (const agent of this.agents) {
      agent.npc.checkProximity(this.scene.player);
      agent.npc.update(_time, delta);

      // If reading, wait 2-3 seconds then walk to next waypoint
      if (agent.state === 'reading') {
        agent.readTimer += delta;
        if (agent.readTimer > 2000 + Math.random() * 1000) {
          agent.readTimer = 0;
          this.walkToNextWaypoint(agent);
        }
      }
    }
  }

  freeze(): void {
    // Stop movement but keep NPCs visible in their final positions
    for (const agent of this.agents) {
      if (agent.tween) agent.tween.stop();
      agent.state = 'idle';
    }
  }

  exit(): void {
    // Stop all movement
    for (const agent of this.agents) {
      if (agent.tween) agent.tween.stop();
    }

    // Agents converge to center of library, show completion message
    const room = getRoomById('library');
    if (room) {
      const cx = (room.worldOffset.x + room.width / 2) * TILE;
      const cy = (room.worldOffset.y + room.height / 2) * TILE;

      for (let i = 0; i < this.agents.length; i++) {
        const agent = this.agents[i];
        const targetX = cx - 40 + i * 25;

        this.scene.tweens.add({
          targets: agent.npc,
          x: targetX,
          y: cy,
          duration: 800,
          ease: 'Quad.easeOut',
          onComplete: () => {
            agent.npc.say('Research complete!', 2500);
          },
        });

        // Destroy after announcement
        this.scene.time.delayedCall(3500, () => {
          agent.npc.destroy();
        });
      }
    }

    // Update progress text to show completion
    if (this.progressText) {
      this.progressText.setText('Research Complete!');
      this.progressText.setColor('#44cc66');
      this.scene.tweens.add({
        targets: this.progressText,
        alpha: 0,
        duration: 1000,
        delay: 3000,
        onComplete: () => {
          this.progressText?.destroy();
          this.progressText = null;
        },
      });
    }

    this.agents = [];
  }
}
