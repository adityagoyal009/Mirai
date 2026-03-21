"""
WebSocket endpoint for real-time swarm prediction visualization.
Uses simple_websocket via flask-sock. Thread-safe broadcast via queue.
"""

import json
import queue
import threading
import traceback
from flask import Blueprint
from flask_sock import Sock

from ..utils.logger import get_logger
from ..services.swarm_predictor import SwarmPredictor

logger = get_logger('mirofish.api.ws')

ws_bp = Blueprint('websocket', __name__)
sock = Sock()

# Each connected client gets a message queue
_client_queues: list = []
_clients_lock = threading.Lock()


def broadcast(msg: dict):
    """Thread-safe broadcast — pushes to all client queues."""
    data = json.dumps(msg)
    with _clients_lock:
        for q in _client_queues:
            try:
                q.put_nowait(data)
            except queue.Full:
                pass


def init_websocket(app):
    """Initialize WebSocket support on the Flask app."""
    sock.init_app(app)
    app.register_blueprint(ws_bp)


@sock.route('/ws/swarm')
def swarm_ws(ws):
    """WebSocket endpoint for swarm prediction streaming."""
    client_queue = queue.Queue(maxsize=1000)
    with _clients_lock:
        _client_queues.append(client_queue)
    logger.info("[WS] Client connected")

    # Sender thread: reads from queue, sends to WebSocket
    stop_event = threading.Event()

    def sender():
        while not stop_event.is_set():
            try:
                data = client_queue.get(timeout=0.5)
                try:
                    ws.send(data)
                except Exception:
                    break
            except queue.Empty:
                continue

    sender_thread = threading.Thread(target=sender, daemon=True)
    sender_thread.start()

    try:
        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                # Keepalive — client still connected but no message
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                client_queue.put(json.dumps({"type": "error", "error": "Invalid JSON"}))
                continue

            if msg.get("type") == "startSwarm":
                _handle_start_swarm(msg)
            elif msg.get("type") == "saveLayout":
                logger.info("[WS] Layout save received")
            else:
                client_queue.put(json.dumps({
                    "type": "error",
                    "error": f"Unknown message type: {msg.get('type')}"
                }))

    except Exception as e:
        if "timed out" not in str(e).lower():
            logger.warning(f"[WS] Client error: {e}")
    finally:
        stop_event.set()
        with _clients_lock:
            if client_queue in _client_queues:
                _client_queues.remove(client_queue)
        logger.info("[WS] Client disconnected")


def _handle_start_swarm(msg: dict):
    """Handle a startSwarm request — run prediction with streaming callbacks."""
    exec_summary = msg.get("execSummary", "")
    agent_count = msg.get("agentCount", 100)

    if not exec_summary:
        broadcast({"type": "error", "error": "Missing execSummary"})
        return

    valid_counts = [50, 100, 250, 500, 1000]
    if agent_count not in valid_counts:
        agent_count = min(valid_counts, key=lambda x: abs(x - agent_count))

    logger.info(f"[WS] Starting swarm: {agent_count} agents")
    broadcast({
        "type": "swarmStarted",
        "totalAgents": agent_count,
        "execSummary": exec_summary[:200],
    })

    agents_completed = [0]
    total_positive = [0]
    total_negative = [0]

    def on_agent_start(agent_id, persona_name, model_label):
        broadcast({
            "type": "agentSpawned",
            "id": agent_id,
            "persona": persona_name,
            "model": model_label,
        })
        broadcast({
            "type": "agentActive",
            "id": agent_id,
            "activity": "evaluating",
        })

    def on_agent_complete(agent):
        agents_completed[0] += 1
        if agent.vote == "positive":
            total_positive[0] += 1
        else:
            total_negative[0] += 1

        broadcast({
            "type": "agentVoted",
            "id": agent.agent_id,
            "vote": agent.vote,
            "overall": agent.overall,
            "scores": agent.scores,
            "confidence": agent.confidence,
            "reasoning": agent.reasoning[:150],
        })

        if agents_completed[0] % 5 == 0 or agents_completed[0] == agent_count:
            total = agents_completed[0]
            broadcast({
                "type": "swarmProgress",
                "agentsCompleted": total,
                "totalAgents": agent_count,
                "positivePct": round(total_positive[0] / max(total, 1) * 100, 1),
                "negativePct": round(total_negative[0] / max(total, 1) * 100, 1),
                "avgConfidence": 0,
            })

    def run_swarm():
        try:
            swarm = SwarmPredictor()
            research_context = f"Executive Summary Analysis:\n{exec_summary}"

            result = swarm.predict(
                exec_summary=exec_summary,
                research_context=research_context,
                agent_count=agent_count,
                on_agent_complete=on_agent_complete,
                on_agent_start=on_agent_start,
            )

            broadcast({
                "type": "swarmComplete",
                "result": result.to_dict(),
            })
            logger.info(f"[WS] Swarm complete: {result.positive_pct}% positive")

        except Exception as e:
            logger.error(f"[WS] Swarm failed: {e}\n{traceback.format_exc()}")
            broadcast({"type": "error", "error": str(e)})

    thread = threading.Thread(target=run_swarm, daemon=True)
    thread.start()
