import { useEffect, useRef, useState, useCallback } from 'react';
import Phaser from 'phaser';
import { gameConfig } from '../game/config';
import { WorldScene } from '../game/WorldScene';
import { mirai, type MiraiState, type AgentData } from '../miraiSocket';
import type { DialogState } from '../game/dialog/DialogManager';

export function useGameBridge() {
  const gameRef = useRef<Phaser.Game | null>(null);
  const sceneRef = useRef<WorldScene | null>(null);
  const [state, setState] = useState<MiraiState>(mirai.state);
  const [nearestNpc, setNearestNpc] = useState<{ id: string; caption: string } | null>(null);
  const [dialogState, setDialogState] = useState<DialogState | null>(null);
  const [playerPos, setPlayerPos] = useState<{ x: number; y: number } | null>(null);

  // Track which agents/votes we've already pushed to the scene
  const spawnedRef = useRef(new Set<number>());
  const activeRef = useRef(new Set<number>());
  const votedRef = useRef(new Set<number>());

  // -- Phaser lifecycle --
  useEffect(() => {
    const game = new Phaser.Game(gameConfig);
    gameRef.current = game;

    game.events.on('ready', () => {
      const poll = () => {
        const scene = game.scene.getScene('WorldScene') as WorldScene;
        if (scene && scene.scene.isActive()) {
          sceneRef.current = scene;

          // Wire scene callbacks to React state
          scene.onNearestNpc(setNearestNpc);
          scene.onDialog(setDialogState);

          // Poll player position for minimap (every 100ms)
          const posPoll = setInterval(() => {
            if (sceneRef.current) {
              setPlayerPos(sceneRef.current.getPlayerPosition());
            }
          }, 100);
          // Store cleanup ref
          (game as any).__posPoll = posPoll;

          // Listen for analysis start from dialog completion
          scene.events.on('analysis:start', (_dialogId: string, responses: Record<string, string>) => {
            if (responses.execSummary) {
              mirai.startAnalysis(
                responses.execSummary,
                parseInt(responses.agentCount || '25', 10),
                responses.depth || 'standard',
              );
            }
          });

          // Listen for agent inspect
          scene.events.on('agent:inspect', (agent: AgentData) => {
            setInspectedAgent(agent);
          });

          // Listen for report collection
          scene.events.on('report:collect', (narrative: string) => {
            const council = mirai.state.council;
            setReportData({
              narrative,
              verdict: mirai.state.swarmResult?.verdict || council?.verdict,
              score: council?.overall,
              confidence: council?.confidence,
            });
          });
        } else {
          setTimeout(poll, 100);
        }
      };
      poll();
    });

    return () => {
      clearInterval((game as any).__posPoll);
      game.destroy(true);
      gameRef.current = null;
      sceneRef.current = null;
    };
  }, []);

  // -- Mirai state subscription --
  useEffect(() => {
    const unsub = mirai.subscribe((newState) => {
      setState({ ...newState, agents: new Map(newState.agents) });
    });
    return () => { unsub(); };
  }, []);

  // -- Bridge mirai state changes into the Phaser scene --
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    // Update phase manager and gate system with current state
    scene.phaseManager.update(state);
    scene.gateManager.updatePhase(state.phase);

    // On phase reset, clear agents
    if (state.phase === 'idle' || state.phase === 'swarm') {
      if (state.phase === 'idle') {
        scene.clearAgents();
        spawnedRef.current.clear();
        activeRef.current.clear();
        votedRef.current.clear();
      }
    }

    // Spawn new agents
    state.agents.forEach((agent) => {
      if (!spawnedRef.current.has(agent.id)) {
        scene.spawnAgentNpc(agent);
        spawnedRef.current.add(agent.id);
      }
      if (agent.activity === 'evaluating' && !activeRef.current.has(agent.id)) {
        scene.activateAgentNpc(agent.id);
        activeRef.current.add(agent.id);
      }
      if (agent.vote && !votedRef.current.has(agent.id)) {
        scene.agentVoted(agent.id, agent.vote, agent.reasoning || '');
        votedRef.current.add(agent.id);
      }
    });
  }, [state]);

  // -- Agent inspection state --
  const [inspectedAgent, setInspectedAgent] = useState<AgentData | null>(null);

  // -- Report viewer state --
  const [reportData, setReportData] = useState<{ narrative: string; verdict?: string; score?: number; confidence?: number } | null>(null);

  // -- Actions --
  const startDemo = useCallback(() => {
    mirai.simulateDemo();
  }, []);

  const connectWs = useCallback((url?: string) => {
    mirai.connect(url);
  }, []);

  const advanceDialog = useCallback((response?: string) => {
    sceneRef.current?.dialogManager.advance(response);
  }, []);

  const cancelDialog = useCallback(() => {
    sceneRef.current?.dialogManager.cancel();
  }, []);

  const closeInspector = useCallback(() => {
    setInspectedAgent(null);
  }, []);

  const closeReport = useCallback(() => {
    setReportData(null);
    if (sceneRef.current) sceneRef.current.player.frozen = false;
  }, []);

  return {
    state,
    startDemo,
    connectWs,
    nearestNpc,
    dialogState,
    advanceDialog,
    cancelDialog,
    inspectedAgent,
    closeInspector,
    reportData,
    closeReport,
    playerPos,
  };
}
