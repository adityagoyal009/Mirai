import type { MiraiState } from '../miraiSocket';

export function VoteTally({ state }: { state: MiraiState }) {
  // Only show during swarm phase or when there are votes
  const totalVoted = [...state.agents.values()].filter(a => a.vote).length;
  if (state.phase !== 'swarm' && totalVoted === 0) return null;

  const positive = [...state.agents.values()].filter(a => a.vote === 'positive').length;
  const negative = totalVoted - positive;
  const pPct = totalVoted > 0 ? (positive / totalVoted) * 100 : 50;

  return (
    <div style={styles.container}>
      <div style={styles.label}>
        <span style={{ color: '#44cc66' }}>HIT {state.positivePct || Math.round(pPct)}%</span>
        <span style={styles.count}>{totalVoted}/{state.totalAgents || '?'}</span>
        <span style={{ color: '#cc4444' }}>{state.negativePct || Math.round(100 - pPct)}% MISS</span>
      </div>
      <div style={styles.bar}>
        <div style={{
          width: `${pPct}%`,
          height: '100%',
          backgroundColor: '#44cc66',
          borderRadius: 2,
          transition: 'width 0.3s ease',
        }} />
      </div>
      {state.swarmResult && (
        <div style={styles.verdict}>
          {state.swarmResult.verdict}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: 'absolute',
    bottom: 12,
    right: 12,
    background: 'rgba(10,10,15,0.85)',
    border: '1px solid #222',
    borderRadius: 6,
    padding: '8px 12px',
    fontFamily: "'Courier New', monospace",
    pointerEvents: 'auto',
    minWidth: 160,
    zIndex: 10,
  },
  label: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 9,
    letterSpacing: 1,
    marginBottom: 4,
  },
  count: {
    color: '#666',
    fontSize: 9,
  },
  bar: {
    width: '100%',
    height: 6,
    backgroundColor: '#cc4444',
    borderRadius: 2,
    overflow: 'hidden',
  },
  verdict: {
    marginTop: 6,
    fontSize: 11,
    fontWeight: 'bold',
    color: '#4a9eff',
    textAlign: 'center',
    letterSpacing: 2,
  },
};
