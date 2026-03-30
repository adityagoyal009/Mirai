/**
 * Sensei (先生) — Game Bridge
 *
 * Connects the SenseiSocket state to the Phaser game world.
 * Places mentor NPCs in existing rooms when mentors are ready.
 *
 * Room assignments:
 *   Library     → Mentor 1
 *   Council     → Mentor 2
 *   Marketplace → Mentor 3 & 4
 *   Time Room   → Mentor 5
 *   Archive     → Mentor 6 (+ Session Summary)
 */

import { useEffect, useRef, useCallback } from 'react'
import { senseiSocket, type SenseiState, type MentorInfo } from './senseiSocket'
import { MENTOR_DEFS } from './mentorDefs'

// Room → mentor spawn position (tile coords within room)
const MENTOR_ROOM_ASSIGNMENTS = [
  { roomId: 'library',     tile: { x: 10, y: 5 }, skin: 'char_009' },
  { roomId: 'council',     tile: { x: 8,  y: 5 }, skin: 'char_015' },
  { roomId: 'marketplace', tile: { x: 8,  y: 5 }, skin: 'char_025' },
  { roomId: 'marketplace', tile: { x: 16, y: 5 }, skin: 'char_035' },
  { roomId: 'time_room',   tile: { x: 8,  y: 5 }, skin: 'char_045' },
  { roomId: 'archive',     tile: { x: 8,  y: 5 }, skin: 'char_001' },
]

// Character skins for mentors (cycle through)
const MENTOR_SKINS = ['char_009', 'char_015', 'char_025', 'char_035', 'char_045', 'char_001']

export interface SenseiBridgeResult {
  state: SenseiState
  activeMentor: MentorInfo | null
  startSession: (execSummary: string, mentorIds: string[]) => void
  sendChat: (message: string) => void
  endMentorChat: () => void
  nextMentor: () => void
}

export function useSenseiBridge(getWorldScene: () => any | null): SenseiBridgeResult {
  const spawnedNpcIds = useRef<Set<string>>(new Set())

  // Subscribe to state updates
  useEffect(() => {
    const unsub = senseiSocket.subscribe((state) => {
      // When mentors are ready, spawn NPCs in the game world
      if (state.phase === 'selecting' && state.mentors.length > 0) {
        spawnMentorNpcs(state.mentors)
      }
    })
    return unsub
  }, [])

  const spawnMentorNpcs = useCallback((mentors: MentorInfo[]) => {
    const scene = getWorldScene()
    if (!scene) return

    // Clear any previously spawned mentor NPCs
    for (const npcId of spawnedNpcIds.current) {
      try {
        scene.events.emit('npc:remove', npcId)
      } catch {}
    }
    spawnedNpcIds.current.clear()

    // Spawn each mentor as a static NPC in their assigned room
    mentors.forEach((mentor, i) => {
      if (i >= MENTOR_ROOM_ASSIGNMENTS.length) return
      const assignment = MENTOR_ROOM_ASSIGNMENTS[i]
      const def = MENTOR_DEFS.find(m => m.id === mentor.type)
      const npcId = `sensei_mentor_${mentor.id}`

      try {
        // Emit event for WorldScene to handle NPC creation
        scene.events.emit('sensei:spawnMentor', {
          id: npcId,
          mentorId: mentor.id,
          name: mentor.name,
          icon: def?.icon || '🎓',
          skin: MENTOR_SKINS[i % MENTOR_SKINS.length],
          roomId: assignment.roomId,
          tile: assignment.tile,
          caption: `${def?.icon || ''} ${mentor.name}`,
        })
        spawnedNpcIds.current.add(npcId)
      } catch (e) {
        console.warn(`[Sensei] Failed to spawn mentor NPC ${npcId}:`, e)
      }
    })
  }, [getWorldScene])

  const activeMentor = senseiSocket.state.activeMentorId
    ? senseiSocket.state.mentors.find(m => m.id === senseiSocket.state.activeMentorId) || null
    : null

  return {
    state: senseiSocket.state,
    activeMentor,
    startSession: (execSummary, mentorIds) => {
      senseiSocket.connect()
      setTimeout(() => senseiSocket.startSession(execSummary, mentorIds), 500)
    },
    sendChat: (message) => {
      if (senseiSocket.state.activeMentorId) {
        senseiSocket.sendChat(senseiSocket.state.activeMentorId, message)
      }
    },
    endMentorChat: () => {
      if (senseiSocket.state.activeMentorId) {
        senseiSocket.endMentorChat(senseiSocket.state.activeMentorId)
      }
    },
    nextMentor: () => {
      const currentIdx = senseiSocket.state.mentors.findIndex(
        m => m.id === senseiSocket.state.activeMentorId
      )
      const nextIdx = currentIdx + 1
      if (nextIdx < senseiSocket.state.mentors.length) {
        senseiSocket.startMentorChat(senseiSocket.state.mentors[nextIdx].id)
      } else {
        senseiSocket.endSession()
      }
    },
  }
}
