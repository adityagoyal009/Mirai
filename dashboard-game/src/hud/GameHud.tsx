export function GameHud({
  onStartDemo,
  onConnect,
}: {
  onStartDemo: () => void;
  onConnect: (url?: string) => void;
}) {
  return (
    <div style={styles.overlay}>
      {/* Controls — below minimap area */}
      <div style={styles.controls}>
        <button onClick={() => onConnect()} style={styles.btn}>
          CONNECT
        </button>
        <button onClick={onStartDemo} style={styles.btnPrimary}>
          DEMO
        </button>
      </div>

      {/* WASD hint — bottom left */}
      <div style={styles.hint}>WASD to move | E to interact</div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    pointerEvents: "none",
    zIndex: 10,
    fontFamily: "'Courier New', monospace",
  },
  controls: {
    position: "absolute",
    top: 160,
    right: 12,
    display: "flex",
    gap: 8,
    pointerEvents: "auto",
  },
  btn: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: "#888",
    background: "#1a1a22",
    border: "1px solid #333",
    padding: "4px 12px",
    borderRadius: 3,
    cursor: "pointer",
    letterSpacing: 1,
  },
  btnPrimary: {
    fontFamily: "'Courier New', monospace",
    fontSize: 10,
    color: "#4a9eff",
    background: "#1a2744",
    border: "1px solid #4a9eff44",
    padding: "4px 12px",
    borderRadius: 3,
    cursor: "pointer",
    letterSpacing: 1,
  },
  hint: {
    position: "absolute",
    bottom: 12,
    left: 12,
    fontSize: 10,
    color: "#444",
    letterSpacing: 1,
  },
};
