/** Map status prefixes back to tool names for animation selection */
export const STATUS_TO_TOOL: Record<string, string> = {
  Reading: 'Read',
  Searching: 'Grep',
  Globbing: 'Glob',
  Fetching: 'WebFetch',
  'Searching web': 'WebSearch',
  Writing: 'Write',
  Editing: 'Edit',
  Running: 'Bash',
  Task: 'Task',
};

export function extractToolName(status: string): string | null {
  for (const [prefix, tool] of Object.entries(STATUS_TO_TOOL)) {
    if (status.startsWith(prefix)) return tool;
  }
  const first = status.split(/[\s:]/)[0];
  return first || null;
}

import { ZOOM_MIN } from '../constants.js';

/** Compute a default integer zoom level (device pixels per sprite pixel) */
export function defaultZoom(): number {
  // Auto-fit: fill available canvas space (scoreboard takes ~40%)
  const canvasW = window.innerWidth * 0.58;
  const canvasH = window.innerHeight * 0.95;
  const dpr = window.devicePixelRatio || 1;
  const mapW = 52 * 16;
  const mapH = 35 * 16;
  const fitZoom = Math.min(canvasW / mapW, canvasH / mapH) * dpr;
  // Use 0.5 step rounding for better fit
  return Math.max(ZOOM_MIN, Math.round(fitZoom * 2) / 2);
}
