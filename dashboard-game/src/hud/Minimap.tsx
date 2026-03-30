// ---------------------------------------------------------------------------
// Minimap.tsx — 200x140 canvas minimap overlay for the Mirai War Room
// ---------------------------------------------------------------------------
// Renders all rooms from roomDefs as colored rectangles, highlights the
// active-phase room, draws the player as a white dot, and shows agent
// cluster dots in the marketplace during the swarm phase.
// Redraws on a 100 ms interval (not per-frame) for performance.
// ---------------------------------------------------------------------------

import { useRef, useEffect } from 'react';
import {
  roomDefs,
  TILE,
  WORLD_WIDTH,
  WORLD_HEIGHT,
} from '../game/world/roomDefs';

// ---- Props ----------------------------------------------------------------

export interface MinimapProps {
  /** Player pixel position (tile * 32). null when unknown. */
  playerPos: { x: number; y: number } | null;
  /** Current Mirai pipeline phase id. */
  phase: string;
  /** Number of active agents (used for swarm cluster dots). */
  agentCount: number;
}

// ---- Constants ------------------------------------------------------------

const MAP_W = 200;
const MAP_H = 140;
const BG = '#0a0a12';
const BORDER = '#333';
const ACTIVE_BORDER = '#ffcc44';
const PLAYER_COLOR = '#ffffff';
const PLAYER_RADIUS = 4;
const LABEL_FONT = '6px "Courier New", monospace';
const AGENT_DOT_COLOR = '#ffaa4a';
const AGENT_DOT_RADIUS = 2;

// ---- Helpers --------------------------------------------------------------

/** Convert a 0xRRGGBB number to a CSS hex string. */
const hexToCss = (n: number): string =>
  '#' + n.toString(16).padStart(6, '0');

// ---- Component ------------------------------------------------------------

export function Minimap({ playerPos, phase, agentCount }: MinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Scale factor: world tiles -> minimap pixels
    const scaleX = MAP_W / WORLD_WIDTH;
    const scaleY = MAP_H / WORLD_HEIGHT;

    const draw = () => {
      // 1. Clear with dark background
      ctx.fillStyle = BG;
      ctx.fillRect(0, 0, MAP_W, MAP_H);

      // 2. Draw each room
      for (const room of roomDefs) {
        const rx = room.worldOffset.x * scaleX;
        const ry = room.worldOffset.y * scaleY;
        const rw = room.width * scaleX;
        const rh = room.height * scaleY;

        // Filled rect with room floor color
        ctx.fillStyle = hexToCss(room.floorColor);
        ctx.fillRect(rx, ry, rw, rh);

        // 3. Active phase highlight
        if (room.phase && room.phase === phase) {
          ctx.strokeStyle = ACTIVE_BORDER;
          ctx.lineWidth = 1.5;
          ctx.strokeRect(rx + 0.5, ry + 0.5, rw - 1, rh - 1);
        }

        // 4. Room labels (skip corridors — rooms with empty label)
        if (room.label) {
          ctx.fillStyle = 'rgba(255,255,255,0.7)';
          ctx.font = LABEL_FONT;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(room.label, rx + rw / 2, ry + rh / 2, rw - 2);
        }
      }

      // 5. Agent cluster dots in marketplace during swarm phase
      if (phase === 'swarm' && agentCount > 0) {
        const market = roomDefs.find((r) => r.id === 'marketplace');
        if (market) {
          const mx = market.worldOffset.x * scaleX;
          const my = market.worldOffset.y * scaleY;
          const mw = market.width * scaleX;
          const mh = market.height * scaleY;

          // Use a seeded-ish pattern so dots don't jump each redraw
          ctx.fillStyle = AGENT_DOT_COLOR;
          const dotCount = Math.min(agentCount, 40); // cap visual dots
          for (let i = 0; i < dotCount; i++) {
            // Deterministic scatter using index
            const angle = (i * 2.399) % (Math.PI * 2); // golden angle
            const dist = ((i * 7 + 3) % 17) / 17;
            const dx = mx + mw * 0.5 + Math.cos(angle) * dist * mw * 0.35;
            const dy = my + mh * 0.5 + Math.sin(angle) * dist * mh * 0.35;
            ctx.beginPath();
            ctx.arc(dx, dy, AGENT_DOT_RADIUS, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // 6. Player dot
      if (playerPos) {
        const px = (playerPos.x / TILE) * scaleX;
        const py = (playerPos.y / TILE) * scaleY;
        ctx.fillStyle = PLAYER_COLOR;
        ctx.beginPath();
        ctx.arc(px, py, PLAYER_RADIUS, 0, Math.PI * 2);
        ctx.fill();
      }

      // 7. Border around entire minimap
      ctx.strokeStyle = BORDER;
      ctx.lineWidth = 1;
      ctx.strokeRect(0.5, 0.5, MAP_W - 1, MAP_H - 1);
    };

    // Initial draw + 100 ms interval
    draw();
    const intervalId = setInterval(draw, 100);
    return () => clearInterval(intervalId);
  }, [playerPos, phase, agentCount]);

  return (
    <canvas
      ref={canvasRef}
      width={MAP_W}
      height={MAP_H}
      style={styles.canvas}
    />
  );
}

// ---- Styles ---------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  canvas: {
    position: 'absolute',
    top: 12,
    right: 12,
    borderRadius: 6,
    opacity: 0.92,
    pointerEvents: 'auto',
  },
};
