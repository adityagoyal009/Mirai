import { useEffect, useState, useRef } from 'react';

import type { SubagentCharacter } from '../hooks/useExtensionMessages.js';
import { agentMetadata, ZONE_NAMES } from '../hooks/useSwarmAgents.js';
import { mirai } from '../miraiApi.js';
import type { OfficeState } from '../office/engine/officeState.js';
import { CharacterState, TILE_SIZE } from '../office/types.js';

interface AgentLabelsProps {
  officeState: OfficeState;
  agents: number[];
  agentStatuses: Record<number, string>;
  containerRef: React.RefObject<HTMLDivElement | null>;
  zoom: number;
  panRef: React.RefObject<{ x: number; y: number }>;
  subagentCharacters: SubagentCharacter[];
}

export function AgentLabels({
  officeState,
  agents,
  agentStatuses,
  containerRef,
  zoom,
  panRef,
  subagentCharacters,
}: AgentLabelsProps) {
  const [, setTick] = useState(0);
  const [hoveredId, setHoveredId] = useState<number | null>(null);
  const [chatAgentId, setChatAgentId] = useState<number | null>(null);
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{role: string; text: string}>>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const chatInputRef = useRef<HTMLInputElement>(null);

  // Listen for chat responses
  useEffect(() => {
    const unsub = mirai.onMessage((msg) => {
      if (msg.type === 'agentChatResponse') {
        const m = msg as any;
        setChatLoading(false);
        if (m.response) {
          setChatMessages(prev => [...prev, { role: 'agent', text: m.response }]);
        }
      }
    });
    return unsub;
  }, []);

  useEffect(() => {
    let rafId = 0;
    const tick = () => {
      setTick((n) => n + 1);
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafId);
  }, []);

  const el = containerRef.current;
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const canvasW = Math.round(rect.width * dpr);
  const canvasH = Math.round(rect.height * dpr);
  const layout = officeState.getLayout();
  const mapW = layout.cols * TILE_SIZE * zoom;
  const mapH = layout.rows * TILE_SIZE * zoom;
  const deviceOffsetX = Math.floor((canvasW - mapW) / 2) + Math.round(panRef.current.x);
  const deviceOffsetY = Math.floor((canvasH - mapH) / 2) + Math.round(panRef.current.y);

  const subLabelMap = new Map<number, string>();
  for (const sub of subagentCharacters) {
    subLabelMap.set(sub.id, sub.label);
  }

  const allIds = [...agents, ...subagentCharacters.map((s) => s.id)];

  return (
    <>
      {allIds.map((id) => {
        const ch = officeState.characters.get(id);
        if (!ch) return null;

        const sittingOffset = ch.state === CharacterState.TYPE ? 6 : 0;
        const screenX = (deviceOffsetX + ch.x * zoom) / dpr;
        const screenY = (deviceOffsetY + (ch.y + sittingOffset - 24) * zoom) / dpr;

        const status = agentStatuses[id];
        const isWaiting = status === 'waiting';
        const isActive = ch.isActive;
        void ch.isSubagent;
        const meta = agentMetadata.get(id);

        let dotColor = 'transparent';
        if (isWaiting) {
          dotColor = '#cca700';
        } else if (isActive) {
          dotColor = '#3794ff';
        }

        const isHovered = hoveredId === id;

        return (
          <div
            key={id}
            style={{
              position: 'absolute',
              left: screenX,
              top: screenY - 16,
              transform: 'translateX(-50%)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              pointerEvents: 'auto',
              zIndex: isHovered ? 100 : 40,
              cursor: 'pointer',
            }}
            onMouseEnter={() => setHoveredId(id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            {/* Status dot */}
            {dotColor !== 'transparent' && (
              <span
                className={isActive && !isWaiting ? 'pixel-agents-pulse' : undefined}
                style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: dotColor, marginBottom: 2,
                }}
              />
            )}

            {/* Activity tag — show for active agents, persona on hover */}
            {meta && meta.vote && !isHovered && (
              <span style={{
                fontSize: '10px',
                color: meta.vote === 'positive' ? '#00ff88' : '#ff4444',
                background: 'rgba(10,10,30,0.8)',
                padding: '1px 4px', borderRadius: 2,
                whiteSpace: 'nowrap',
              }}>
                {meta.vote === 'positive' ? 'HIT' : 'MISS'}
              </span>
            )}
            {isHovered && meta && (
              <span style={{
                fontSize: '12px',
                color: '#e0e0e0',
                background: 'rgba(30,30,46,0.9)',
                padding: '2px 6px', borderRadius: 3,
                whiteSpace: 'nowrap',
              }}>
                {meta.persona.slice(0, 30)}
              </span>
            )}

            {/* Hover tooltip */}
            {isHovered && meta && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'rgba(8, 8, 24, 0.97)',
                  border: '1px solid #333',
                  borderRadius: 8,
                  padding: '10px 12px',
                  width: 240,
                  zIndex: 200,
                  boxShadow: '0 4px 20px rgba(0,0,0,0.8)',
                  marginBottom: 8,
                }}
                onMouseEnter={() => setHoveredId(id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                {/* Persona name */}
                <div style={{ color: '#00ff88', fontSize: 12, fontWeight: 'bold', marginBottom: 4 }}>
                  {meta.persona.slice(0, 60)}
                </div>

                {/* Zone */}
                <div style={{ color: '#888', fontSize: 10, marginBottom: 6 }}>
                  {ZONE_NAMES[meta.zone] || meta.zone}
                </div>

                {/* Activity */}
                <div style={{
                  color: '#4488ff', fontSize: 11, marginBottom: 4,
                  padding: '2px 6px', background: 'rgba(68,136,255,0.1)',
                  borderRadius: 3, display: 'inline-block',
                }}>
                  {meta.activity}
                </div>

                {/* Vote result */}
                {meta.vote && (
                  <div style={{
                    color: meta.vote === 'positive' ? '#00ff88' : '#ff4444',
                    fontSize: 12, fontWeight: 'bold', marginTop: 6,
                  }}>
                    {meta.vote === 'positive' ? '👍 HIT' : '👎 MISS'}
                    {meta.overall != null && (
                      <span style={{ color: '#aaa', fontWeight: 'normal', marginLeft: 6 }}>
                        {meta.overall.toFixed(1)}/10
                      </span>
                    )}
                  </div>
                )}

                {/* Reasoning */}
                {meta.reasoning && (
                  <div style={{
                    color: '#aaa', fontSize: 10, marginTop: 6,
                    lineHeight: 1.4, borderTop: '1px solid #222', paddingTop: 6,
                  }}>
                    "{meta.reasoning.slice(0, 150)}{meta.reasoning.length > 150 ? '...' : ''}"
                  </div>
                )}

                {/* Chat button */}
                {meta.vote && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setChatAgentId(id); setChatMessages([]); setChatInput(''); }}
                    style={{
                      marginTop: 6, width: '100%', padding: '4px 8px', fontSize: 10,
                      background: '#1565c0', color: '#fff', border: 'none', borderRadius: 3,
                      cursor: 'pointer',
                    }}
                  >
                    Ask this agent
                  </button>
                )}
              </div>
            )}

            {/* Chat modal */}
            {chatAgentId === id && meta && (
              <div
                style={{
                  position: 'absolute', bottom: '100%', left: '50%', transform: 'translateX(-50%)',
                  background: 'rgba(8,8,24,0.98)', border: '1px solid #333', borderRadius: 8,
                  padding: 12, width: 280, zIndex: 300, boxShadow: '0 4px 20px rgba(0,0,0,0.9)',
                  marginBottom: 8,
                }}
                onClick={(e) => e.stopPropagation()}
                onMouseDown={(e) => e.stopPropagation()}
                onPointerDown={(e) => e.stopPropagation()}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{ color: '#00ff88', fontSize: 11, fontWeight: 'bold' }}>{meta.persona.slice(0, 30)}</span>
                  <span onClick={() => setChatAgentId(null)} style={{ color: '#888', cursor: 'pointer', fontSize: 14 }}>×</span>
                </div>

                {/* Chat messages */}
                <div style={{ maxHeight: 150, overflowY: 'auto', marginBottom: 8 }}>
                  {chatMessages.map((m, i) => (
                    <div key={i} style={{
                      color: m.role === 'user' ? '#4488ff' : '#e0e0e0',
                      fontSize: 10, marginBottom: 4, lineHeight: 1.4,
                      padding: '3px 6px', background: m.role === 'user' ? 'rgba(68,136,255,0.1)' : 'rgba(255,255,255,0.05)',
                      borderRadius: 3,
                    }}>
                      <strong>{m.role === 'user' ? 'You' : 'Agent'}:</strong> {m.text}
                    </div>
                  ))}
                  {chatLoading && <div style={{ color: '#888', fontSize: 10 }}>Thinking...</div>}
                </div>

                {/* Input */}
                <div style={{ display: 'flex', gap: 4 }}>
                  <input
                    ref={chatInputRef}
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && chatInput.trim()) {
                        setChatMessages(prev => [...prev, { role: 'user', text: chatInput }]);
                        setChatLoading(true);
                        mirai.chatWithAgent(id, chatInput, meta.persona, meta.zone,
                          meta.vote || '', meta.reasoning || '', '');
                        setChatInput('');
                      }
                    }}
                    placeholder="Ask a question..."
                    style={{
                      flex: 1, background: '#0d0d1a', border: '1px solid #333', borderRadius: 3,
                      padding: '4px 6px', fontSize: 10, color: '#e0e0e0', outline: 'none',
                    }}
                  />
                  <button
                    onClick={() => {
                      if (chatInput.trim()) {
                        setChatMessages(prev => [...prev, { role: 'user', text: chatInput }]);
                        setChatLoading(true);
                        mirai.chatWithAgent(id, chatInput, meta.persona, meta.zone,
                          meta.vote || '', meta.reasoning || '', '');
                        setChatInput('');
                      }
                    }}
                    style={{
                      background: '#1565c0', color: '#fff', border: 'none', borderRadius: 3,
                      padding: '4px 8px', fontSize: 10, cursor: 'pointer',
                    }}
                  >
                    Send
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}
