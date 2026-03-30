import Phaser from "phaser";
import type { AgentData, Zone } from "./miraiSocket";

// -- Layout constants --
const TILE = 32;
const COLS = 40;
const ROWS = 24;
const W = COLS * TILE; // 1280
const H = ROWS * TILE; // 768

// 8 rooms in a 4x2 grid
const ROOM_COLS = 4;
const ROOM_ROWS = 2;
const ROOM_W = COLS / ROOM_COLS; // 10 tiles
const ROOM_H = ROWS / ROOM_ROWS; // 12 tiles

interface RoomDef {
  zone: Zone;
  label: string;
  col: number;
  row: number;
  color: number;
  labelColor: string;
}

const ROOMS: RoomDef[] = [
  { zone: "investor", label: "INVESTORS", col: 0, row: 0, color: 0x1a2744, labelColor: "#4a9eff" },
  { zone: "customer", label: "CUSTOMERS", col: 1, row: 0, color: 0x1a3a2a, labelColor: "#4aff7a" },
  { zone: "operator", label: "OPERATORS", col: 2, row: 0, color: 0x3a2a1a, labelColor: "#ffaa4a" },
  { zone: "council", label: "COUNCIL", col: 3, row: 0, color: 0x3a1a3a, labelColor: "#cc66ff" },
  { zone: "analyst", label: "ANALYSTS", col: 0, row: 1, color: 0x2a2a1a, labelColor: "#e6e64a" },
  { zone: "contrarian", label: "CONTRARIANS", col: 1, row: 1, color: 0x3a1a1a, labelColor: "#ff4a4a" },
  { zone: "wildcard", label: "WILDCARDS", col: 2, row: 1, color: 0x1a3a3a, labelColor: "#4ae6e6" },
  { zone: "archive", label: "ARCHIVE", col: 3, row: 1, color: 0x2a1a2a, labelColor: "#e64ae6" },
];

const ZONE_TO_ROOM = new Map(ROOMS.map((r) => [r.zone, r]));

interface AgentSprite {
  circle: Phaser.GameObjects.Arc;
  label: Phaser.GameObjects.Text;
  bubble: Phaser.GameObjects.Text | null;
  bubbleTimer: ReturnType<typeof setTimeout> | null;
  data: AgentData;
}

export class WarRoomScene extends Phaser.Scene {
  private agentSprites = new Map<number, AgentSprite>();
  private roomLabels: Phaser.GameObjects.Text[] = [];
  private particleZones = new Map<Zone, { x: number; y: number; w: number; h: number }>();

  constructor() {
    super({ key: "WarRoom" });
  }

  create() {
    this.cameras.main.setBackgroundColor("#0a0a0f");
    this.drawRooms();
  }

  private drawRooms() {
    const gfx = this.add.graphics();

    for (const room of ROOMS) {
      const rx = room.col * ROOM_W * TILE;
      const ry = room.row * ROOM_H * TILE;
      const rw = ROOM_W * TILE;
      const rh = ROOM_H * TILE;

      // Floor
      gfx.fillStyle(room.color, 1);
      gfx.fillRect(rx + 2, ry + 2, rw - 4, rh - 4);

      // Border
      gfx.lineStyle(2, 0x333344, 0.8);
      gfx.strokeRect(rx + 1, ry + 1, rw - 2, rh - 2);

      // Inner glow lines
      gfx.lineStyle(1, 0x222233, 0.4);
      for (let i = TILE; i < rw; i += TILE) {
        gfx.lineBetween(rx + i, ry + 2, rx + i, ry + rh - 2);
      }
      for (let i = TILE; i < rh; i += TILE) {
        gfx.lineBetween(rx + 2, ry + i, rx + rw - 2, ry + i);
      }

      // Room label
      const lbl = this.add.text(rx + rw / 2, ry + 16, room.label, {
        fontFamily: "'Courier New', monospace",
        fontSize: "11px",
        color: room.labelColor,
        align: "center",
      });
      lbl.setOrigin(0.5, 0);
      lbl.setAlpha(0.7);
      this.roomLabels.push(lbl);

      // Store zone bounds for spawning
      const padding = TILE;
      this.particleZones.set(room.zone, {
        x: rx + padding,
        y: ry + 32 + padding,
        w: rw - padding * 2,
        h: rh - 32 - padding * 2,
      });
    }

    // Outer border
    gfx.lineStyle(2, 0x444466, 1);
    gfx.strokeRect(0, 0, W, H);
  }

  spawnAgent(agent: AgentData) {
    if (this.agentSprites.has(agent.id)) return;

    const bounds = this.particleZones.get(agent.zone) ||
      this.particleZones.get("analyst")!;

    const x = bounds.x + Math.random() * bounds.w;
    const y = bounds.y + Math.random() * bounds.h;

    const circle = this.add.circle(x, y, 6, 0x6688cc, 0.9);
    circle.setStrokeStyle(1, 0x88aaee, 0.6);

    // Spawn animation
    circle.setScale(0);
    this.tweens.add({
      targets: circle,
      scale: 1,
      duration: 300,
      ease: "Back.easeOut",
    });

    // Idle bob
    this.tweens.add({
      targets: circle,
      y: y + 3,
      duration: 1500 + Math.random() * 1000,
      yoyo: true,
      repeat: -1,
      ease: "Sine.easeInOut",
    });

    const label = this.add.text(x, y - 12, agent.persona.split(" ")[0], {
      fontFamily: "'Courier New', monospace",
      fontSize: "8px",
      color: "#889",
      align: "center",
    });
    label.setOrigin(0.5, 1);
    label.setAlpha(0);

    // Fade in label
    this.tweens.add({
      targets: label,
      alpha: 0.6,
      duration: 500,
      delay: 300,
    });

    this.agentSprites.set(agent.id, {
      circle,
      label,
      bubble: null,
      bubbleTimer: null,
      data: agent,
    });
  }

  setAgentActive(id: number) {
    const sprite = this.agentSprites.get(id);
    if (!sprite) return;

    // Pulse effect for active agents
    this.tweens.add({
      targets: sprite.circle,
      scaleX: 1.3,
      scaleY: 1.3,
      duration: 300,
      yoyo: true,
      repeat: 2,
      ease: "Sine.easeInOut",
    });
    sprite.circle.setFillStyle(0xaabb44, 0.9);
  }

  setAgentVoted(id: number, vote: "positive" | "negative", reasoning: string) {
    const sprite = this.agentSprites.get(id);
    if (!sprite) return;

    const color = vote === "positive" ? 0x44cc66 : 0xcc4444;
    const strokeColor = vote === "positive" ? 0x66ff88 : 0xff6666;
    sprite.circle.setFillStyle(color, 0.9);
    sprite.circle.setStrokeStyle(2, strokeColor, 0.8);

    // Vote pop
    this.tweens.add({
      targets: sprite.circle,
      scaleX: 1.5,
      scaleY: 1.5,
      duration: 150,
      yoyo: true,
      ease: "Quad.easeOut",
    });

    // Show speech bubble briefly
    this.showBubble(sprite, reasoning.substring(0, 60) + "...", vote);
  }

  private showBubble(sprite: AgentSprite, text: string, vote: string) {
    if (sprite.bubble) {
      sprite.bubble.destroy();
      if (sprite.bubbleTimer) clearTimeout(sprite.bubbleTimer);
    }

    const bColor = vote === "positive" ? "#1a3a1a" : "#3a1a1a";
    const tColor = vote === "positive" ? "#88ff88" : "#ff8888";

    const bubble = this.add.text(
      sprite.circle.x,
      sprite.circle.y - 22,
      text,
      {
        fontFamily: "'Courier New', monospace",
        fontSize: "7px",
        color: tColor,
        backgroundColor: bColor,
        padding: { x: 4, y: 2 },
        wordWrap: { width: 140 },
        align: "center",
      }
    );
    bubble.setOrigin(0.5, 1);
    bubble.setAlpha(0);
    bubble.setDepth(10);

    this.tweens.add({
      targets: bubble,
      alpha: 1,
      y: sprite.circle.y - 28,
      duration: 200,
    });

    sprite.bubble = bubble;
    sprite.bubbleTimer = setTimeout(() => {
      if (bubble.scene) {
        this.tweens.add({
          targets: bubble,
          alpha: 0,
          duration: 800,
          onComplete: () => bubble.destroy(),
        });
      }
      sprite.bubble = null;
    }, 3500);
  }

  clearAgents() {
    this.agentSprites.forEach((sprite) => {
      sprite.circle.destroy();
      sprite.label.destroy();
      if (sprite.bubble) sprite.bubble.destroy();
      if (sprite.bubbleTimer) clearTimeout(sprite.bubbleTimer);
    });
    this.agentSprites.clear();
  }

  // Phase visual effects
  flashRoom(zone: Zone) {
    const room = ZONE_TO_ROOM.get(zone);
    if (!room) return;
    const rx = room.col * ROOM_W * TILE;
    const ry = room.row * ROOM_H * TILE;
    const rw = ROOM_W * TILE;
    const rh = ROOM_H * TILE;

    const flash = this.add.rectangle(
      rx + rw / 2,
      ry + rh / 2,
      rw - 4,
      rh - 4,
      0xffffff,
      0.08
    );
    this.tweens.add({
      targets: flash,
      alpha: 0,
      duration: 1000,
      onComplete: () => flash.destroy(),
    });
  }
}

export const GAME_CONFIG: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: W,
  height: H,
  backgroundColor: "#0a0a0f",
  scene: WarRoomScene,
  parent: "phaser-container",
  pixelArt: true,
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
};
