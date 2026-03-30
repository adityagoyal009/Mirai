import { useState } from "react";
import { useGameBridge } from "./bridge/useGameBridge";
import { GameHud } from "./hud/GameHud";
import { PhaseIndicator } from "./hud/PhaseIndicator";
import { Minimap } from "./hud/Minimap";
import { InteractPrompt, DialogBox } from "./hud/InteractPrompt";
import { SenseiApp } from "./sensei/SenseiApp";

export default function App() {
  const [senseiExecSummary, setSenseiExecSummary] = useState('');
  const [senseiActive, setSenseiActive] = useState(false);

  const {
    state,
    connectWs,
    nearestNpc,
    dialogState,
    advanceDialog,
    cancelDialog,
    playerPos,
  } = useGameBridge();

  // Intercept dialog completion — route exec summary to Sensei
  const handleDialogAdvance = (response?: string) => {
    advanceDialog(response);
    if (dialogState?.dialogId === 'intake_welcome') {
      const step = dialogState.currentStep;
      if (step?.stateKey === 'execSummary' && response) {
        setSenseiExecSummary(response);
        setSenseiActive(true);
      }
    }
  };

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <div id="phaser-container" style={{ width: "100%", height: "100%" }} />

      {/* Sensei branding */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 800,
        background: 'rgba(0,0,0,0.6)', borderRadius: 8, padding: '6px 14px',
        fontSize: 11, fontWeight: 600, letterSpacing: 2, color: '#888',
      }}>
        先生 SENSEI
      </div>

      <PhaseIndicator phase={senseiActive ? 'sensei' : state.phase} />

      <Minimap
        playerPos={playerPos}
        phase={state.phase}
        agentCount={state.agents.size}
      />

      <GameHud onStartDemo={() => {}} onConnect={connectWs} />

      <InteractPrompt
        npcName={nearestNpc?.caption || ""}
        visible={!!nearestNpc && !dialogState?.active}
      />

      {dialogState && (
        <DialogBox
          dialogState={dialogState}
          onAdvance={handleDialogAdvance}
          onCancel={cancelDialog}
        />
      )}

      {/* Sensei overlay */}
      {senseiActive && senseiExecSummary && (
        <SenseiApp execSummary={senseiExecSummary} />
      )}

      {/* Hint when not active */}
      {!senseiActive && (
        <div style={{
          position: 'absolute', bottom: 80, left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(0,0,0,0.7)', padding: '10px 20px', borderRadius: 8,
          color: '#aaa', fontSize: 12, textAlign: 'center', zIndex: 500,
        }}>
          Walk to the intake desk and upload your executive summary to start a mentor session
        </div>
      )}
    </div>
  );
}
