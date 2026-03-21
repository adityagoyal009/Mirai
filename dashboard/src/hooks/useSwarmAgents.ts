/**
 * useSwarmAgents — bridges Mirai WebSocket swarm events to OfficeState characters.
 * Routes agents to role-based zones based on persona name.
 */

import { useEffect, useRef } from 'react';
import { mirai } from '../miraiApi.js';
import type { OfficeState } from '../office/engine/officeState.js';

const MAX_VISIBLE_AGENTS = 50;
const WS_URL = `ws://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:5000/ws/swarm`;

// Role-based zone palettes (maps to character palette 0-5)
const ZONE_PALETTES: Record<string, number> = {
  investor: 0,
  customer: 1,
  operator: 2,
  analyst: 3,
  contrarian: 4,
};

// Keywords to classify personas into zones
const ZONE_KEYWORDS: Record<string, string[]> = {
  investor: ['vc', 'investor', 'angel', 'pe ', 'fund', 'capital', 'venture', 'hedge', 'banker', 'underwriter', 'allocator', 'portfolio'],
  customer: ['customer', 'buyer', 'consumer', 'enterprise', 'smb', 'target', 'user', 'procurement', 'it director', 'owner'],
  operator: ['founder', 'cto', 'cmo', 'cfo', 'coo', 'ceo', 'operator', 'serial', 'vp ', 'director', 'engineer', 'product manager'],
  analyst: ['analyst', 'researcher', 'expert', 'economist', 'strategist', 'professor', 'academic', 'consultant', 'bcg', 'mckinsey', 'gartner'],
  contrarian: ['devil', 'advocate', 'contrarian', 'optimist', 'pessimist', 'journalist', 'reporter', 'cynic', 'realist', 'skeptic'],
};

function classifyPersona(persona: string): string {
  const lower = persona.toLowerCase();
  for (const [zone, keywords] of Object.entries(ZONE_KEYWORDS)) {
    for (const kw of keywords) {
      if (lower.includes(kw)) return zone;
    }
  }
  // Default: distribute evenly
  return Object.keys(ZONE_KEYWORDS)[Math.floor(Math.random() * 5)];
}

export function useSwarmAgents(getOfficeState: () => OfficeState) {
  const connectedRef = useRef(false);
  const spawnedIdsRef = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (connectedRef.current) return;
    connectedRef.current = true;

    mirai.connect(WS_URL);

    const unsub = mirai.onMessage((msg) => {
      const os = getOfficeState();

      switch (msg.type) {
        case 'swarmStarted': {
          for (const id of spawnedIdsRef.current) {
            try { os.removeAgent(id); } catch {}
          }
          spawnedIdsRef.current.clear();
          break;
        }

        case 'agentSpawned': {
          if (spawnedIdsRef.current.size >= MAX_VISIBLE_AGENTS) break;
          const agentId = msg.id;
          const zone = classifyPersona(msg.persona || '');
          const palette = ZONE_PALETTES[zone] ?? 0;
          try {
            os.addAgent(agentId, palette);
            spawnedIdsRef.current.add(agentId);
          } catch (e) {
            // Seat might not be available
          }
          break;
        }

        case 'agentActive': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          try {
            const toolName = msg.activity === 'researching' ? 'Read'
              : msg.activity === 'reading' ? 'Grep'
              : 'Write';
            os.setAgentTool(msg.id, toolName);
            os.setAgentActive(msg.id, true);
          } catch {}
          break;
        }

        case 'agentVoted': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          try {
            os.setAgentTool(msg.id, null);
            if (msg.vote === 'positive') {
              os.showWaitingBubble(msg.id);
            } else {
              os.showPermissionBubble(msg.id);
            }
          } catch {}
          break;
        }

        case 'agentDone': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          try {
            os.setAgentActive(msg.id, false);
          } catch {}
          break;
        }

        case 'swarmComplete': {
          break;
        }
      }
    });

    return () => {
      unsub();
      mirai.disconnect();
      connectedRef.current = false;
    };
  }, [getOfficeState]);
}
