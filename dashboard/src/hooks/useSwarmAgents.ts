/**
 * useSwarmAgents — bridges Mirai WebSocket swarm events to OfficeState characters.
 * Routes agents to 6 role-based war room zones with metadata for hover tooltips.
 */

import { useEffect, useRef, useState } from 'react';
import { mirai } from '../miraiApi.js';
import type { OfficeState } from '../office/engine/officeState.js';

const MAX_VISIBLE_AGENTS = 80;
const WS_URL = `ws://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:5000/ws/swarm`;

export const ZONE_NAMES: Record<string, string> = {
  investor: 'INVESTORS',
  customer: 'CUSTOMERS',
  operator: 'OPERATORS',
  analyst: 'ANALYSTS',
  contrarian: 'CONTRARIANS',
  wildcard: 'WILD CARD',
  council: 'COUNCIL',
};

const ZONE_PALETTES: Record<string, number> = {
  investor: 0, customer: 1, operator: 2,
  analyst: 3, contrarian: 4, wildcard: 5, council: 0,
};

const ZONE_KEYWORDS: Record<string, string[]> = {
  investor: ['vc', 'investor', 'angel', 'pe ', 'fund', 'capital', 'venture', 'hedge', 'banker', 'seed', 'series', 'family office'],
  customer: ['customer', 'buyer', 'consumer', 'enterprise', 'smb', 'target', 'user', 'procurement', 'it director', 'owner', 'merchant'],
  operator: ['founder', 'cto', 'cmo', 'cfo', 'coo', 'ceo', 'operator', 'serial', 'vp ', 'director', 'engineer', 'product manager', 'chief'],
  analyst: ['analyst', 'researcher', 'expert', 'economist', 'strategist', 'professor', 'academic', 'consultant', 'journalist', 'reporter'],
  contrarian: ['competitor', 'regulatory', 'regulator', 'patent', 'attorney', 'privacy', 'compliance', 'risk', 'insurance', 'cybersecurity', 'skeptic', 'contrarian'],
};

function classifyPersona(persona: string): string {
  const lower = persona.toLowerCase();
  for (const [zone, keywords] of Object.entries(ZONE_KEYWORDS)) {
    for (const kw of keywords) {
      if (lower.includes(kw)) return zone;
    }
  }
  return 'wildcard';
}

// ── Agent metadata for hover tooltips ──
export interface AgentMeta {
  persona: string;
  zone: string;
  model: string;
  activity: string;
  vote?: string;
  reasoning?: string;
  overall?: number;
}

export const agentMetadata: Map<number, AgentMeta> = new Map();

// ── Zone counts for scoreboard ──
export const zoneCounts: Record<string, number> = {
  investor: 0, customer: 0, operator: 0,
  analyst: 0, contrarian: 0, wildcard: 0,
};

export function resetZoneCounts() {
  for (const key of Object.keys(zoneCounts)) zoneCounts[key] = 0;
  agentMetadata.clear();
}

export function useSwarmAgents(getOfficeState: () => OfficeState): number[] {
  const connectedRef = useRef(false);
  const spawnedIdsRef = useRef<Set<number>>(new Set());
  const [spawnedIds, setSpawnedIds] = useState<number[]>([]);

  useEffect(() => {
    if (connectedRef.current) return;
    connectedRef.current = true;
    mirai.connect(WS_URL);

    const unsub = mirai.onMessage((msg) => {
      const os = getOfficeState();
      const msgType = (msg as any).type as string;

      // Handle research events (not in SwarmMessage type)
      if (msgType === 'researchStarted') {
        for (const id of spawnedIdsRef.current) { try { os.removeAgent(id); } catch {} }
        spawnedIdsRef.current.clear(); setSpawnedIds([]); resetZoneCounts(); os.resetZoneSeats();
        const rid = 8888;
        agentMetadata.set(rid, { persona: 'Research Agent', zone: 'wildcard', model: '', activity: 'Searching markets...' });
        try { os.addAgent(rid, 2, undefined, undefined, undefined, undefined, 'wildcard'); spawnedIdsRef.current.add(rid); setSpawnedIds([rid]); os.setAgentActive(rid, false); } catch {}
        return;
      }
      if (msgType === 'researchProgress') {
        const rmeta = agentMetadata.get(8888);
        if (rmeta) rmeta.activity = (msg as any).status || 'Researching...';
        return;
      }
      if (msgType === 'researchComplete') {
        try { os.removeAgent(8888); } catch {}
        spawnedIdsRef.current.delete(8888);
        return;
      }

      switch (msg.type) {
        case 'swarmStarted': {
          // Clear all previous agents
          for (const id of spawnedIdsRef.current) {
            try { os.removeAgent(id); } catch {}
          }
          spawnedIdsRef.current.clear();
          setSpawnedIds([]);
          resetZoneCounts();
          os.resetZoneSeats();
          break;
        }

        case 'agentSpawned': {
          if (spawnedIdsRef.current.size >= MAX_VISIBLE_AGENTS) break;
          const agentId = msg.id;
          const zone = (msg as any).zone || classifyPersona(msg.persona || '');
          const palette = ZONE_PALETTES[zone] ?? 5;
          zoneCounts[zone] = (zoneCounts[zone] || 0) + 1;

          // Store metadata for hover tooltip
          agentMetadata.set(agentId, {
            persona: msg.persona || `Agent #${agentId}`,
            zone,
            model: (msg as any).model || '',
            activity: 'Spawning...',
          });

          try {
            os.addAgent(agentId, palette, undefined, undefined, undefined, undefined, zone);
            spawnedIdsRef.current.add(agentId);
            setSpawnedIds(Array.from(spawnedIdsRef.current));
          } catch {}
          break;
        }

        case 'agentActive': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          const meta = agentMetadata.get(msg.id);
          if (meta) {
            meta.activity = msg.activity === 'researching' ? 'Researching...'
              : msg.activity === 'reading' ? 'Reading...'
              : 'Evaluating...';
          }
          try {
            const toolName = msg.activity === 'researching' ? 'Read'
              : msg.activity === 'reading' ? 'Grep' : 'Write';
            os.setAgentTool(msg.id, toolName);
            os.setAgentActive(msg.id, true);
          } catch {}
          break;
        }

        case 'agentVoted': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          const meta = agentMetadata.get(msg.id);
          if (meta) {
            meta.vote = msg.vote;
            meta.reasoning = msg.reasoning;
            meta.overall = (msg as any).overall;
            meta.activity = msg.vote === 'positive' ? 'Voted: HIT' : 'Voted: MISS';
          }
          try {
            os.setAgentTool(msg.id, null);
            if (msg.vote === 'positive') {
              os.showWaitingBubble(msg.id);
            } else {
              os.showPermissionBubble(msg.id);
            }
            // After 5 seconds, set agent inactive → triggers WALK/WANDER cycle
            const votedId = msg.id;
            setTimeout(() => {
              try { os.setAgentActive(votedId, false); } catch {}
            }, 5000);
          } catch {}
          break;
        }

        case 'agentDone': {
          if (!spawnedIdsRef.current.has(msg.id)) break;
          try { os.setAgentActive(msg.id, false); } catch {}
          break;
        }

        case 'swarmComplete':
          // All agents go idle → triggers wandering for 30 seconds
          setTimeout(() => {
            for (const id of spawnedIdsRef.current) {
              try { os.setAgentActive(id, false); } catch {}
            }
          }, 3000);
          // Stop wandering after 30 seconds — agents sit back down
          setTimeout(() => {
            for (const id of spawnedIdsRef.current) {
              try { os.setAgentActive(id, true); } catch {}
            }
          }, 33000);
          break;

        // Council: spawn 4 Elder agents
        case 'councilStarted': {
          const models = (msg as any).models || [];
          for (let i = 0; i < Math.min(models.length, 4); i++) {
            const elderId = 9000 + i;
            agentMetadata.set(elderId, {
              persona: `Elder ${i + 1}`,
              zone: 'council',
              model: models[i] || `Model ${i + 1}`,
              activity: 'Deliberating...',
            });
            zoneCounts['council'] = (zoneCounts['council'] || 0) + 1;
            try {
              os.addAgent(elderId, 0, undefined, undefined, undefined, undefined, 'council');
              spawnedIdsRef.current.add(elderId);
              setSpawnedIds(Array.from(spawnedIdsRef.current));
              os.setAgentTool(elderId, 'Write');
              os.setAgentActive(elderId, true);
            } catch {}
          }
          break;
        }

        case 'councilComplete': {
          // Elders finish — show vote bubbles
          for (let i = 0; i < 4; i++) {
            const elderId = 9000 + i;
            const meta = agentMetadata.get(elderId);
            if (meta) {
              meta.activity = `Verdict: ${(msg as any).verdict}`;
              meta.overall = (msg as any).overall;
            }
            try {
              os.setAgentTool(elderId, null);
              os.showWaitingBubble(elderId);
            } catch {}
          }
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

  return spawnedIds;
}
