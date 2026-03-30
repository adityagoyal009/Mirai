// ---------------------------------------------------------------------------
// PhaseIndicator.tsx — Animated phase progression trail for the Mirai HUD
// ---------------------------------------------------------------------------
// Displays a horizontal row of small circles (one per pipeline phase) with
// a pulsing animation on the current phase, dimmer fills for past phases,
// and dark outlines for future phases. Current phase name shown below.
// ---------------------------------------------------------------------------

import { useMemo } from 'react';

// ---- Phase data -----------------------------------------------------------

const PHASES = [
  'idle',
  'research',
  'council',
  'swarm',
  'plan',
  'oasis',
  'narrative',
  'complete',
] as const;

const PHASE_COLORS: Record<string, string> = {
  idle: '#555',
  research: '#4a9eff',
  council: '#cc66ff',
  swarm: '#ffaa4a',
  plan: '#4aff7a',
  oasis: '#e6e64a',
  narrative: '#e64ae6',
  complete: '#44cc66',
};

// ---- Props ----------------------------------------------------------------

export interface PhaseIndicatorProps {
  /** Current Mirai pipeline phase id. */
  phase: string;
}

// ---- Component ------------------------------------------------------------

export function PhaseIndicator({ phase }: PhaseIndicatorProps) {
  const currentIdx = PHASES.indexOf(phase as (typeof PHASES)[number]);
  const color = PHASE_COLORS[phase] || PHASE_COLORS.idle;

  // Inject the keyframe animation once (memoised so it only inserts once)
  useMemo(() => {
    const id = 'phase-indicator-pulse';
    if (typeof document !== 'undefined' && !document.getElementById(id)) {
      const style = document.createElement('style');
      style.id = id;
      style.textContent = `
        @keyframes phase-pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50%      { transform: scale(1.45); opacity: 0.65; }
        }
      `;
      document.head.appendChild(style);
    }
  }, []);

  return (
    <div style={styles.container}>
      {/* Phase circles */}
      <div style={styles.circleRow}>
        {PHASES.map((p, i) => {
          const phaseColor = PHASE_COLORS[p];
          const isCurrent = i === currentIdx;
          const isPast = currentIdx >= 0 && i < currentIdx;
          // Future: not past and not current (or phase is unknown)

          let bg: string;
          let border: string;
          let extraStyle: React.CSSProperties = {};

          if (isCurrent) {
            bg = phaseColor;
            border = phaseColor;
            extraStyle = {
              animation: 'phase-pulse 1.4s ease-in-out infinite',
              boxShadow: `0 0 6px ${phaseColor}`,
            };
          } else if (isPast) {
            bg = phaseColor;
            border = phaseColor;
            extraStyle = { opacity: 0.35 };
          } else {
            // Future — dark outline only
            bg = 'transparent';
            border = '#333';
          }

          return (
            <div
              key={p}
              title={p}
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: bg,
                border: `1px solid ${border}`,
                ...extraStyle,
              }}
            />
          );
        })}
      </div>

      {/* Current phase label */}
      <div style={{ ...styles.label, color }}>
        {phase.toUpperCase()}
      </div>
    </div>
  );
}

// ---- Styles ---------------------------------------------------------------

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    top: 12,
    left: 12,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: 5,
    background: 'rgba(10,10,15,0.82)',
    padding: '7px 14px 6px',
    borderRadius: 20,
    border: '1px solid #222',
    pointerEvents: 'auto',
    fontFamily: "'Courier New', monospace",
  },
  circleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  label: {
    fontSize: 10,
    letterSpacing: 2,
    fontWeight: 'bold',
    lineHeight: 1,
  },
};
