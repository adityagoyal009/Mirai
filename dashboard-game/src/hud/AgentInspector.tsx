import type { AgentData } from '../miraiSocket';

export function AgentInspector({
  agent,
  onClose,
}: {
  agent: AgentData;
  onClose: () => void;
}) {
  const voteColor = agent.vote === 'positive' ? '#44cc66' : agent.vote === 'negative' ? '#cc4444' : '#888';

  return (
    <div style={styles.backdrop} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <span style={styles.persona}>{agent.persona}</span>
          <button onClick={onClose} style={styles.close}>ESC</button>
        </div>

        <div style={styles.row}>
          <Label text="ZONE" /><Value text={agent.zone} />
          <Label text="MODEL" /><Value text={agent.model} />
        </div>

        {agent.vote && (
          <div style={{ ...styles.voteBadge, borderColor: voteColor, color: voteColor }}>
            {agent.vote === 'positive' ? 'HIT' : 'MISS'}
            {agent.overall != null && ` — ${agent.overall}/10`}
            {agent.confidence != null && ` (${Math.round(agent.confidence * 100)}% conf)`}
          </div>
        )}

        {agent.scores && (
          <div style={styles.scores}>
            {Object.entries(agent.scores).map(([k, v]) => (
              <div key={k} style={styles.scoreRow}>
                <span style={styles.scoreLabel}>{k}</span>
                <div style={styles.scoreBar}>
                  <div style={{ ...styles.scoreFill, width: `${(v as number) * 10}%` }} />
                </div>
                <span style={styles.scoreValue}>{v as number}</span>
              </div>
            ))}
          </div>
        )}

        {agent.reasoning && (
          <div style={styles.reasoning}>{agent.reasoning}</div>
        )}
      </div>
    </div>
  );
}

function Label({ text }: { text: string }) {
  return <span style={{ color: '#555', fontSize: 9, letterSpacing: 1, marginRight: 4 }}>{text}</span>;
}
function Value({ text }: { text: string }) {
  return <span style={{ color: '#aaa', fontSize: 11, marginRight: 16 }}>{text}</span>;
}

const styles: Record<string, React.CSSProperties> = {
  backdrop: {
    position: 'absolute',
    top: 0, right: 0, bottom: 0,
    width: 320,
    background: 'rgba(10,10,20,0.95)',
    borderLeft: '1px solid #333',
    pointerEvents: 'auto',
    fontFamily: "'Courier New', monospace",
    padding: 16,
    overflowY: 'auto',
    zIndex: 20,
  },
  panel: {},
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  persona: {
    color: '#4a9eff',
    fontSize: 13,
    fontWeight: 'bold',
  },
  close: {
    fontFamily: "'Courier New', monospace",
    fontSize: 9,
    color: '#888',
    background: '#1a1a22',
    border: '1px solid #333',
    padding: '2px 8px',
    borderRadius: 3,
    cursor: 'pointer',
  },
  row: {
    display: 'flex',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  voteBadge: {
    border: '1px solid',
    borderRadius: 4,
    padding: '4px 10px',
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 12,
    textAlign: 'center',
  },
  scores: {
    marginBottom: 12,
  },
  scoreRow: {
    display: 'flex',
    alignItems: 'center',
    marginBottom: 4,
  },
  scoreLabel: {
    color: '#666',
    fontSize: 9,
    width: 60,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  scoreBar: {
    flex: 1,
    height: 6,
    backgroundColor: '#222',
    borderRadius: 3,
    marginRight: 8,
    overflow: 'hidden',
  },
  scoreFill: {
    height: '100%',
    backgroundColor: '#4a9eff',
    borderRadius: 3,
  },
  scoreValue: {
    color: '#aaa',
    fontSize: 10,
    width: 20,
    textAlign: 'right',
  },
  reasoning: {
    color: '#999',
    fontSize: 10,
    lineHeight: '1.5',
    borderTop: '1px solid #222',
    paddingTop: 10,
  },
};
