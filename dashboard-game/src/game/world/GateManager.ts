/**
 * GateManager.ts
 *
 * Places locked gates in corridors between rooms. Gates block the player
 * until the preceding room's phase activity finishes.
 */

import Phaser from 'phaser';
import { roomDefs, TILE, type RoomDef } from './roomDefs';

interface Gate {
  id: string;
  corridorId: string;
  unlocksAfterPhase: string;
  reason: string;
  bar: Phaser.GameObjects.Rectangle;
  glow: Phaser.GameObjects.Rectangle;
  lockIcon: Phaser.GameObjects.Text;
  tooltip: Phaser.GameObjects.Text;
  body: Phaser.GameObjects.Zone;
  locked: boolean;
  tooltipVisible: boolean;
  cx: number;
  cy: number;
}

/** Maps corridor IDs to the phase that unlocks them + a reason message. */
const GATE_RULES: Record<string, { phase: string; reason: string }> = {
  corridor_lobby_library: {
    phase: 'intake',
    reason: 'Talk to the Intake Desk first to start your analysis.',
  },
  corridor_library_council: {
    phase: 'research',
    reason: 'Waiting for the Research phase to complete...',
  },
  corridor_council_marketplace: {
    phase: 'council',
    reason: 'The Council of Elders is still deliberating.',
  },
  corridor_marketplace_timeroom: {
    phase: 'swarm',
    reason: 'The Swarm agents are still voting.',
  },
  corridor_timeroom_archive: {
    phase: 'oasis',
    reason: 'The OASIS simulation is still running.',
  },
};

// Phases in order — a gate unlocks when its required phase is in the "past"
const PHASE_ORDER = [
  'idle', 'intake', 'research', 'council', 'swarm',
  'plan', 'oasis', 'narrative', 'complete',
];

export class GateManager {
  private scene: Phaser.Scene;
  private gates: Gate[] = [];
  private wallGroup: Phaser.Physics.Arcade.StaticGroup;

  constructor(scene: Phaser.Scene, wallGroup: Phaser.Physics.Arcade.StaticGroup) {
    this.scene = scene;
    this.wallGroup = wallGroup;
    this.createGates();
  }

  private createGates(): void {
    for (const room of roomDefs) {
      const rule = GATE_RULES[room.id];
      if (!rule) continue;

      const cx = (room.worldOffset.x + room.width / 2) * TILE;
      const cy = (room.worldOffset.y + room.height / 2) * TILE;
      const gateH = room.height * TILE;

      // Vertical bar
      const bar = this.scene.add.rectangle(cx, cy, 6, gateH - 8, 0xff4444, 0.8);
      bar.setDepth(10);
      bar.setStrokeStyle(1, 0xff6666, 0.6);

      // Glow
      const glow = this.scene.add.rectangle(cx, cy, 16, gateH - 4, 0xff2222, 0.15);
      glow.setDepth(9);

      // Lock icon
      const lockIcon = this.scene.add.text(cx, cy - 2, '🔒', {
        fontSize: '14px',
        align: 'center',
      });
      lockIcon.setOrigin(0.5);
      lockIcon.setDepth(11);

      // Tooltip — reason why gate is locked (hidden until player is near)
      const tooltip = this.scene.add.text(cx, cy - gateH / 2 - 12, rule.reason, {
        fontFamily: 'monospace',
        fontSize: '9px',
        color: '#ffaaaa',
        backgroundColor: '#1a0a0aee',
        padding: { x: 8, y: 4 },
        align: 'center',
        wordWrap: { width: 200 },
      });
      tooltip.setOrigin(0.5, 1);
      tooltip.setDepth(50);
      tooltip.setAlpha(0);

      // Collision body
      const body = this.scene.add.zone(cx, cy, 12, gateH);
      this.wallGroup.add(body);
      (body.body as Phaser.Physics.Arcade.StaticBody).setSize(12, gateH);

      // Pulse animation
      this.scene.tweens.add({
        targets: glow,
        alpha: 0.05,
        duration: 1200,
        yoyo: true,
        repeat: -1,
        ease: 'Sine.easeInOut',
      });

      this.gates.push({
        id: room.id,
        corridorId: room.id,
        unlocksAfterPhase: rule.phase,
        reason: rule.reason,
        bar,
        glow,
        lockIcon,
        tooltip,
        body,
        locked: true,
        tooltipVisible: false,
        cx,
        cy,
      });
    }
  }

  /**
   * Call each frame — shows/hides tooltip when player is near a locked gate.
   */
  checkProximity(playerX: number, playerY: number): void {
    const RANGE = 80; // pixels

    for (const gate of this.gates) {
      if (!gate.locked) continue;

      const dist = Phaser.Math.Distance.Between(playerX, playerY, gate.cx, gate.cy);
      const near = dist < RANGE;

      if (near && !gate.tooltipVisible) {
        gate.tooltipVisible = true;
        this.scene.tweens.killTweensOf(gate.tooltip);
        this.scene.tweens.add({
          targets: gate.tooltip,
          alpha: 1,
          duration: 200,
        });
      }
      if (!near && gate.tooltipVisible) {
        gate.tooltipVisible = false;
        this.scene.tweens.killTweensOf(gate.tooltip);
        this.scene.tweens.add({
          targets: gate.tooltip,
          alpha: 0,
          duration: 200,
        });
      }
    }
  }

  /**
   * Call whenever the Mirai phase changes. Unlocks gates whose
   * required phase is now in the past.
   */
  updatePhase(currentPhase: string): void {
    const currentIdx = PHASE_ORDER.indexOf(currentPhase);

    for (const gate of this.gates) {
      if (!gate.locked) continue;

      const requiredIdx = PHASE_ORDER.indexOf(gate.unlocksAfterPhase);
      // Gate unlocks when current phase is PAST the required phase
      if (currentIdx > requiredIdx) {
        this.unlockGate(gate);
      }
    }
  }

  /**
   * Force-unlock a specific corridor gate by corridor ID.
   * Used for intake completion (dialog:complete event).
   */
  unlockCorridor(corridorId: string): void {
    const gate = this.gates.find((g) => g.corridorId === corridorId);
    if (gate && gate.locked) {
      this.unlockGate(gate);
    }
  }

  private unlockGate(gate: Gate): void {
    gate.locked = false;

    // Play unlock sound
    const sm = (this.scene as any).soundManager;
    if (sm) sm.playGateUnlock();

    // Show direction hint via tutorial arrow
    const ta = (this.scene as any).tutorialArrow;
    if (ta) ta.showDirectionHint(gate.cx, gate.cy);

    // Remove collision
    gate.body.destroy();

    // Animate the gate opening
    this.scene.tweens.add({
      targets: [gate.bar, gate.glow],
      alpha: 0,
      scaleY: 0,
      duration: 600,
      ease: 'Power2',
      onComplete: () => {
        gate.bar.destroy();
        gate.glow.destroy();
      },
    });

    // Hide tooltip
    gate.tooltip.destroy();

    // Replace lock with unlock icon briefly, then fade
    gate.lockIcon.setText('🔓');
    this.scene.tweens.add({
      targets: gate.lockIcon,
      alpha: 0,
      y: gate.lockIcon.y - 20,
      duration: 800,
      delay: 300,
      onComplete: () => gate.lockIcon.destroy(),
    });

    // Green flash at the gate position
    const flash = this.scene.add.rectangle(
      gate.bar.x, gate.bar.y,
      32, gate.bar.height,
      0x44ff66, 0.3,
    );
    flash.setDepth(8);
    this.scene.tweens.add({
      targets: flash,
      alpha: 0,
      scaleX: 3,
      duration: 500,
      onComplete: () => flash.destroy(),
    });
  }
}
