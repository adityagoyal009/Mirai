export interface DialogStep {
  speaker: 'npc' | 'system';
  text: string;
  expectsInput?: boolean;
  inputType?: 'text' | 'number' | 'select' | 'file';
  inputOptions?: string[];
  stateKey?: string; // maps to analysis params
}

export interface DialogDef {
  id: string;
  steps: DialogStep[];
}

export const DIALOGS: DialogDef[] = [
  {
    id: 'intake_welcome',
    steps: [
      { speaker: 'npc', text: 'Welcome to the Mirai Intelligence Network. I am the Intake Clerk.' },
      { speaker: 'npc', text: 'Upload your executive summary as a PDF (max 2 pages), or paste it as text below.' },
      { speaker: 'npc', text: '', expectsInput: true, inputType: 'file', stateKey: 'execSummary' },
      { speaker: 'npc', text: 'How many agents should evaluate this opportunity?' },
      { speaker: 'npc', text: '', expectsInput: true, inputType: 'select', inputOptions: ['10', '25', '50', '100', '250'], stateKey: 'agentCount' },
      { speaker: 'npc', text: 'And the research depth?' },
      { speaker: 'npc', text: '', expectsInput: true, inputType: 'select', inputOptions: ['quick', 'standard', 'deep'], stateKey: 'depth' },
      { speaker: 'npc', text: 'Excellent. The analysis will begin. Proceed to the Library to observe the research phase.' },
    ],
  },
  {
    id: 'archive_printer',
    steps: [
      { speaker: 'npc', text: 'The Grand Archive is open. I can print your report when the analysis is complete.' },
      { speaker: 'npc', text: 'Walk up to me again when the narrative phase finishes.' },
    ],
  },
];

export function getDialogById(id: string): DialogDef | undefined {
  return DIALOGS.find(d => d.id === id);
}
