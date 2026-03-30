import Phaser from 'phaser';
import { getDialogById, type DialogStep } from './dialogDefs';

export interface DialogState {
  active: boolean;
  npcName: string;
  currentStep: DialogStep | null;
  stepIndex: number;
  dialogId: string;
  responses: Record<string, string>;
}

export class DialogManager {
  private scene: Phaser.Scene;
  public state: DialogState;
  private onStateChange?: (state: DialogState) => void;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.state = {
      active: false,
      npcName: '',
      currentStep: null,
      stepIndex: 0,
      dialogId: '',
      responses: {},
    };
  }

  /** Register a callback for state changes (used by React bridge). */
  onChange(fn: (state: DialogState) => void): void {
    this.onStateChange = fn;
  }

  /** Start a dialog by id. npcName is shown in the dialog box. */
  startDialog(dialogId: string, npcName: string): boolean {
    const def = getDialogById(dialogId);
    if (!def) return false;

    this.state = {
      active: true,
      npcName,
      currentStep: def.steps[0] || null,
      stepIndex: 0,
      dialogId,
      responses: {},
    };
    this.notify();
    return true;
  }

  /** Advance to next step. If current step expects input, pass the response. */
  advance(response?: string): void {
    if (!this.state.active) return;

    const def = getDialogById(this.state.dialogId);
    if (!def) return;

    // Store response if current step expects input
    if (this.state.currentStep?.expectsInput && response !== undefined && this.state.currentStep.stateKey) {
      this.state.responses[this.state.currentStep.stateKey] = response;
    }

    const nextIndex = this.state.stepIndex + 1;
    if (nextIndex >= def.steps.length) {
      // Dialog complete
      this.state.active = false;
      this.state.currentStep = null;
      this.notify();
      // Emit completion event
      this.scene.events.emit('dialog:complete', this.state.dialogId, this.state.responses);
      return;
    }

    this.state.stepIndex = nextIndex;
    this.state.currentStep = def.steps[nextIndex];
    this.notify();
  }

  /** Cancel/close dialog. */
  cancel(): void {
    this.state.active = false;
    this.state.currentStep = null;
    this.notify();
  }

  private notify(): void {
    if (this.onStateChange) {
      this.onStateChange({ ...this.state });
    }
  }
}
