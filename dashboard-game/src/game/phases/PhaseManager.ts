import type { WorldScene } from '../WorldScene';
import type { MiraiState, Phase } from '../../miraiSocket';
import { ResearchBehavior } from './ResearchBehavior';
import { CouncilBehavior } from './CouncilBehavior';
import { OasisBehavior } from './OasisBehavior';
import { ReportBehavior } from './ReportBehavior';
import { SwarmBehavior } from './SwarmBehavior';

interface Behavior {
  enter(state: MiraiState): void;
  onStateUpdate(state: MiraiState): void;
  tick(time: number, delta: number): void;
  exit(): void;
  freeze?(): void;
}

export class PhaseManager {
  private scene: WorldScene;
  private currentPhase: Phase = 'idle';
  private research: ResearchBehavior;
  private council: CouncilBehavior;
  private swarm: SwarmBehavior;
  private oasis: OasisBehavior;
  private report: ReportBehavior;
  private frozen = false;

  constructor(scene: WorldScene) {
    this.scene = scene;
    this.research = new ResearchBehavior(scene);
    this.council = new CouncilBehavior(scene);
    this.swarm = new SwarmBehavior(scene);
    this.oasis = new OasisBehavior(scene);
    this.report = new ReportBehavior(scene);
  }

  /** Called whenever MiraiState changes. Detects phase transitions and routes. */
  update(state: MiraiState): void {
    if (this.frozen) return;

    if (state.phase !== this.currentPhase) {
      // On transition to 'complete', freeze everything instead of exiting
      if (state.phase === 'complete') {
        this.freezeAll();
        this.currentPhase = state.phase;
        this.report.enter(state);
        // Play phase transition sound
        if ((this.scene as any).soundManager) {
          (this.scene as any).soundManager.playPhaseTransition();
        }
        return;
      }

      this.onPhaseExit(this.currentPhase);
      this.currentPhase = state.phase;
      this.onPhaseEnter(state.phase, state);

      // Play phase transition sound
      if ((this.scene as any).soundManager) {
        (this.scene as any).soundManager.playPhaseTransition();
      }
    }

    // Continuous updates for active phase
    this.getBehavior(state.phase)?.onStateUpdate(state);
  }

  private onPhaseEnter(phase: Phase, state: MiraiState): void {
    this.getBehavior(phase)?.enter(state);
  }

  private onPhaseExit(phase: Phase): void {
    this.getBehavior(phase)?.exit();
  }

  private getBehavior(phase: Phase): Behavior | null {
    switch (phase) {
      case 'research': return this.research;
      case 'council': return this.council;
      case 'swarm': return this.swarm;
      case 'oasis': return this.oasis;
      case 'complete': return this.report;
      default: return null;
    }
  }

  private freezeAll(): void {
    this.research.freeze?.();
    this.council.freeze?.();
    this.swarm.freeze?.();
    this.oasis.freeze?.();
    this.frozen = true;
  }

  /** Called each Phaser frame from WorldScene.update() */
  tick(time: number, delta: number): void {
    if (this.frozen) return;
    this.getBehavior(this.currentPhase)?.tick(time, delta);
  }

  /** Reset for a new analysis run. */
  reset(): void {
    this.frozen = false;
    this.currentPhase = 'idle';
  }
}
