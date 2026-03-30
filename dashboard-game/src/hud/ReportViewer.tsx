import { useEffect } from 'react';

interface Props {
  narrative: string;
  verdict?: string;
  score?: number;
  confidence?: number;
  onClose: () => void;
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100vw',
    height: '100vh',
    background: 'rgba(5,5,10,0.95)',
    zIndex: 100,
    pointerEvents: 'auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  container: {
    maxWidth: 700,
    width: '90%',
    maxHeight: '85vh',
    background: '#0a0a18',
    border: '1px solid #333',
    borderRadius: 8,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'flex',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  title: {
    fontFamily: "'Courier New', monospace",
    fontSize: 14,
    color: '#4a9eff',
    letterSpacing: 2,
  },
  closeBtn: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#888',
    background: 'transparent',
    border: '1px solid #444',
    padding: '4px 10px',
    borderRadius: 3,
    cursor: 'pointer',
    letterSpacing: 1,
  },
  divider: {
    height: 1,
    background: '#222',
    width: '100%',
  },
  verdictBar: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: '12px 16px',
  },
  score: {
    fontFamily: "'Courier New', monospace",
    fontSize: 14,
    color: '#fff',
    fontWeight: 'bold',
  },
  confidence: {
    fontFamily: "'Courier New', monospace",
    fontSize: 11,
    color: '#888',
  },
  narrativeScroll: {
    overflowY: 'auto',
    flex: 1,
    padding: 16,
    fontFamily: "'Courier New', monospace",
    fontSize: 12,
    color: '#ccc',
    lineHeight: 1.7,
  },
  paragraph: {
    marginBottom: 12,
    marginTop: 0,
  },
  actions: {
    display: 'flex',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'flex-end',
    padding: '12px 16px',
  },
  downloadBtn: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#4a9eff',
    background: '#1a2744',
    border: '1px solid #4a9eff44',
    padding: '6px 16px',
    borderRadius: 3,
    cursor: 'pointer',
    letterSpacing: 1,
  },
  closeAction: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: '#4a9eff',
    background: '#1a2744',
    border: '1px solid #4a9eff44',
    padding: '6px 16px',
    borderRadius: 3,
    cursor: 'pointer',
    letterSpacing: 1,
  },
};

export function ReportViewer({ narrative, verdict, score, confidence, onClose }: Props) {
  // ESC to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  return (
    <div style={styles.overlay}>
      <div style={styles.container}>
        {/* Header */}
        <div style={styles.header}>
          <span style={styles.title}>MIRAI INTELLIGENCE REPORT</span>
          <button onClick={onClose} style={styles.closeBtn}>ESC</button>
        </div>

        <div style={styles.divider} />

        {/* Verdict bar (if available) */}
        {verdict && (
          <div style={styles.verdictBar}>
            <span style={{
              color: verdict.includes('Hit') ? '#44cc66' : '#cc4444',
              fontWeight: 'bold',
              fontSize: 14,
              fontFamily: "'Courier New', monospace",
            }}>
              {verdict}
            </span>
            {score != null && <span style={styles.score}>{score}/10</span>}
            {confidence != null && (
              <span style={styles.confidence}>{Math.round(confidence * 100)}% confidence</span>
            )}
          </div>
        )}

        <div style={styles.divider} />

        {/* Scrollable narrative */}
        <div style={styles.narrativeScroll}>
          {narrative.split('\n').map((para, i) => (
            <p key={i} style={styles.paragraph}>{para}</p>
          ))}
        </div>

        <div style={styles.divider} />

        {/* Actions */}
        <div style={styles.actions}>
          <button
            onClick={() => {
              const apiBase = window.location.port === '5000' || window.location.pathname.startsWith('/game')
                ? '' : 'http://localhost:5000';
              window.open(`${apiBase}/api/bi/report/pdf`, '_blank');
            }}
            style={styles.downloadBtn}
          >
            Download PDF
          </button>
          <button onClick={onClose} style={styles.closeAction}>Close</button>
        </div>
      </div>
    </div>
  );
}
