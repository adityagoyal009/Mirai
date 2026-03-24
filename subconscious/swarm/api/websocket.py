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

            if msg.get("type") == "startAnalysis":
                _handle_full_analysis(msg)
            elif msg.get("type") == "chatWithAgent":
                _handle_agent_chat(msg)
            elif msg.get("type") == "startSwarm":
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


def _handle_full_analysis(msg: dict):
    """Handle startAnalysis — run full BI pipeline with streaming events."""
    exec_summary = msg.get("execSummary", "")
    depth = msg.get("depth", "deep")
    agent_count = msg.get("agentCount", 25)

    if not exec_summary:
        broadcast({"type": "error", "error": "Missing execSummary"})
        return

    valid_counts = [0, 10, 25, 50, 100, 250, 500, 1000]
    if agent_count not in valid_counts:
        agent_count = min(valid_counts, key=lambda x: abs(x - agent_count))

    logger.info(f"[WS] Starting full analysis: depth={depth}, agents={agent_count}")

    def run_analysis():
        try:
            from ..services.business_intel import BusinessIntelEngine
            from ..services.swarm_predictor import SwarmPredictor

            bi = BusinessIntelEngine()

            # ── Phase 1: Research (iterative agent + BI engine) ──
            broadcast({"type": "researchStarted"})
            extraction = bi.extract_and_validate(exec_summary)

            # Run iterative research agent first (3 rounds, Claude-quality)
            iterative_findings = None
            try:
                from ..services.research_agent import ResearchAgent
                research_agent = ResearchAgent()

                def on_research_progress(round_num, status):
                    broadcast({"type": "researchProgress", "round": round_num, "status": status})

                iterative_findings = research_agent.research(
                    company=extraction.company if hasattr(extraction, 'company') else '',
                    industry=extraction.industry if hasattr(extraction, 'industry') else '',
                    product=extraction.product if hasattr(extraction, 'product') else '',
                    target_market=extraction.target_market if hasattr(extraction, 'target_market') else '',
                    on_progress=on_research_progress,
                )
                logger.info(f"[WS] Iterative research: {iterative_findings.rounds_completed} rounds, "
                           f"{len(iterative_findings.facts)} facts, {len(iterative_findings.sources)} sources")
            except Exception as e:
                logger.warning(f"[WS] Iterative research failed (falling back to BI engine): {e}")

            # Run standard BI research (enriches with ChromaDB, Mem0, etc.)
            research = bi.research(exec_summary, depth=depth, extraction=extraction)

            # Merge iterative findings into research
            if iterative_findings and iterative_findings.summary:
                if hasattr(research, 'summary'):
                    research.summary = iterative_findings.summary + "\n\n" + (research.summary or "")
                if hasattr(research, 'competitors') and iterative_findings.competitors:
                    existing = set(str(c) for c in research.competitors)
                    for comp in iterative_findings.competitors:
                        if comp not in existing:
                            research.competitors.append(comp)
                if hasattr(research, 'context_facts') and iterative_findings.facts:
                    research.context_facts = iterative_findings.facts + (research.context_facts or [])

            broadcast({
                "type": "researchComplete",
                "findings": len(research.context_facts) if hasattr(research, 'context_facts') else 0,
                "competitors": len(research.competitors) if hasattr(research, 'competitors') else 0,
                "summary": (research.summary[:500] if hasattr(research, 'summary') else ""),
                "sources": len(iterative_findings.sources) if iterative_findings else 0,
                "rounds": iterative_findings.rounds_completed if iterative_findings else 0,
            })

            # ── Phase 2: Council ──
            from ..config import Config
            council_models = Config.get_council_models()
            model_labels = [m.get('label', m.get('model', '?')) for m in council_models] if council_models else ['Primary LLM']
            broadcast({
                "type": "councilStarted",
                "modelCount": len(model_labels),
                "models": model_labels,
            })

            use_council = depth == "deep" and len(council_models) > 1
            prediction = bi.predict(exec_summary, research, use_council=use_council)

            dims = []
            if hasattr(prediction, 'dimensions'):
                dims = [{"name": d.name, "score": d.score} for d in prediction.dimensions]
            elif isinstance(prediction, dict):
                dims = prediction.get('dimensions', [])

            contested = []
            if hasattr(prediction, 'contested_dimensions'):
                contested = prediction.contested_dimensions or []
            elif isinstance(prediction, dict):
                contested = prediction.get('contested_dimensions', [])

            p_score = prediction.overall_score if hasattr(prediction, 'overall_score') else prediction.get('overall_score', 0)
            p_verdict = prediction.verdict if hasattr(prediction, 'verdict') else prediction.get('verdict', '?')
            p_confidence = prediction.confidence if hasattr(prediction, 'confidence') else prediction.get('confidence', 0)

            broadcast({
                "type": "councilComplete",
                "overall": p_score,
                "verdict": p_verdict,
                "confidence": p_confidence,
                "dimensions": dims,
                "contestedDimensions": contested,
                "models": model_labels,
            })

            # ── Phase 2b: Swarm (with enriched context) ──
            if agent_count > 0:
                # Build enriched context from research + council
                research_summary = research.summary[:500] if hasattr(research, 'summary') else str(research)[:500]
                competitors_str = ', '.join(
                    (c if isinstance(c, str) else c.get('name', str(c)))
                    for c in (research.competitors[:5] if hasattr(research, 'competitors') else [])
                )
                dim_summary = ', '.join(
                    f"{d['name']}={d['score']}" for d in sorted(dims, key=lambda x: x['score'])[:3]
                ) if dims else ''

                enriched_context = (
                    f"RESEARCH FINDINGS:\n{research_summary}\n"
                    f"Competitors: {competitors_str}\n\n"
                    f"COUNCIL VERDICT: {p_score:.1f}/10 — {p_verdict}\n"
                    f"Confidence: {p_confidence:.0%}\n"
                    f"Weakest dimensions: {dim_summary}\n\n"
                    f"Given this research and council assessment, evaluate this startup from your unique perspective."
                )

                agents_completed = [0]
                total_positive = [0]
                total_negative = [0]

                broadcast({
                    "type": "swarmStarted",
                    "totalAgents": agent_count,
                    "execSummary": exec_summary[:200],
                })

                def on_agent_start(agent_id, persona_name, model_label, zone="wildcard"):
                    broadcast({
                        "type": "agentSpawned",
                        "id": agent_id,
                        "persona": persona_name,
                        "model": model_label,
                        "zone": zone,
                    })
                    broadcast({"type": "agentActive", "id": agent_id, "activity": "evaluating"})

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

                swarm = SwarmPredictor()

                def on_deliberation_start():
                    broadcast({"type": "deliberationStarted", "rounds": 2})

                swarm_result = swarm.predict(
                    exec_summary=exec_summary,
                    research_context=enriched_context,
                    agent_count=agent_count,
                    on_agent_complete=on_agent_complete,
                    on_agent_start=on_agent_start,
                    on_deliberation_start=on_deliberation_start,
                    industry=extraction.industry if hasattr(extraction, 'industry') else '',
                    product=extraction.product if hasattr(extraction, 'product') else '',
                )

                raw = swarm_result.to_dict()
                broadcast({
                    "type": "swarmComplete",
                    "result": {
                        "totalAgents": raw.get("total_agents", 0),
                        "verdict": raw.get("verdict", "Unknown"),
                        "avg_scores": raw.get("avg_scores", {}),
                        "median_overall": raw.get("median_overall", 0),
                        "std_overall": raw.get("std_overall", 0),
                        "score_distribution": raw.get("score_distribution", {}),
                        "positivePct": raw.get("positive_pct", 0),
                        "negativePct": raw.get("negative_pct", 0),
                        "avgConfidence": raw.get("avg_confidence", 0),
                        "keyThemesPositive": raw.get("key_themes_positive", []),
                        "keyThemesNegative": raw.get("key_themes_negative", []),
                        "contestedThemes": raw.get("contested_themes", []),
                        "modelsUsed": raw.get("models_used", []),
                        "executionTimeSeconds": raw.get("execution_time_seconds", 0),
                        "divergence": raw.get("divergence"),
                        "deliberation": raw.get("deliberation"),
                    },
                })

            # ── Phase 3: Plan ──
            broadcast({"type": "planStarted"})
            plan_dict = {}
            try:
                plan = bi.plan(exec_summary, research, prediction)
                plan_dict = plan.to_dict() if hasattr(plan, 'to_dict') else (plan if isinstance(plan, dict) else {})
                broadcast({
                    "type": "planComplete",
                    "risks": plan_dict.get("risks", [])[:5],
                    "moves": plan_dict.get("next_moves", plan_dict.get("moves", []))[:5],
                })
            except Exception as e:
                logger.warning(f"[WS] Plan phase failed: {e}")
                broadcast({"type": "planComplete", "risks": [], "moves": []})

            # ── Phase 4: OASIS Market Simulation (optional) ──
            oasis_result = {}
            simulate_market = msg.get("simulateMarket", False)
            if simulate_market:
                try:
                    broadcast({"type": "oasisStarted", "rounds": 6})
                    from ..services.oasis_simulator import OasisSimulator
                    oasis = OasisSimulator()

                    def on_round(result):
                        broadcast({
                            "type": "oasisRound",
                            "month": result["month"],
                            "event": result["event"],
                            "sentimentPct": result["sentiment_pct"],
                            "change": result["sentiment_change"],
                            "quote": result["key_quote"],
                        })

                    oasis_result = oasis.simulate(
                        exec_summary=exec_summary,
                        research_context=research_summary[:500] if 'research_summary' in dir() else '',
                        council_verdict=f"{p_score:.1f}/10 - {p_verdict}",
                        on_round_complete=on_round,
                    )
                    broadcast({
                        "type": "oasisComplete",
                        "trajectory": oasis_result.get("trajectory", "stable"),
                        "startSentiment": oasis_result.get("start_sentiment", 50),
                        "endSentiment": oasis_result.get("end_sentiment", 50),
                        "timeline": oasis_result.get("timeline", []),
                    })
                    logger.info(f"[WS] OASIS complete: {oasis_result.get('trajectory')}")
                except Exception as e:
                    logger.warning(f"[WS] OASIS simulation failed (non-fatal): {e}")

            # ── Build data dicts for report + analysisComplete ──
            research_dict = {}
            try:
                research_dict = {
                    "summary": research.summary if hasattr(research, 'summary') else '',
                    "competitors": [
                        (c if isinstance(c, str) else c.get('name', str(c)) if isinstance(c, dict) else str(c))
                        for c in (research.competitors if hasattr(research, 'competitors') else [])
                    ][:10],
                    "trends": research.trends[:5] if hasattr(research, 'trends') else [],
                    "context_facts": research.context_facts[:10] if hasattr(research, 'context_facts') else [],
                }
            except Exception:
                pass

            swarm_dict = {}
            final_verdict = p_verdict
            final_confidence = p_confidence
            if agent_count > 0:
                try:
                    raw_swarm = swarm_result.to_dict()
                    swarm_dict = {
                        "total_agents": raw_swarm.get("total_agents", 0),
                        "positive_pct": raw_swarm.get("positive_pct", 0),
                        "negative_pct": raw_swarm.get("negative_pct", 0),
                        "sample_agents": raw_swarm.get("sample_agents", []),
                        "key_themes_positive": raw_swarm.get("key_themes_positive", []),
                        "key_themes_negative": raw_swarm.get("key_themes_negative", []),
                        "divergence": raw_swarm.get("divergence"),
                        "deliberation": raw_swarm.get("deliberation"),
                        "verdict": raw_swarm.get("verdict"),
                        "avg_confidence": raw_swarm.get("avg_confidence"),
                    }
                    # Override verdict with MORE CONSERVATIVE of council vs swarm
                    swarm_verdict = raw_swarm.get("verdict", p_verdict)
                    swarm_confidence = raw_swarm.get("avg_confidence", p_confidence)
                    verdict_rank = {"Strong Miss": 0, "Likely Miss": 1, "Mixed Signal": 2, "Uncertain": 3, "Likely Hit": 4, "Strong Hit": 5}
                    if verdict_rank.get(swarm_verdict, 3) < verdict_rank.get(p_verdict, 3):
                        final_verdict = swarm_verdict
                    final_confidence = round((p_confidence + swarm_confidence) / 2, 2)
                    logger.info(f"[WS] Verdict blend: council={p_verdict}, swarm={swarm_verdict} -> final={final_verdict} (confidence {final_confidence})")
                except Exception as e:
                    logger.warning(f"[WS] Swarm dict extraction failed: {e}")

            # ── ReACT Report Agent: generate professional report sections ──
            report_sections = {}
            try:
                broadcast({"type": "narrativeStarted"})
                from ..services.report_agent import ReportAgent

                report_data = {
                    "prediction": {
                        "verdict": final_verdict,
                        "composite_score": p_score,
                        "confidence": final_confidence,
                        "dimensions": dims,
                        "contested_dimensions": contested,
                        "council_models": model_labels,
                        "council_verdict": p_verdict,
                        "swarm_verdict": swarm_dict.get("verdict", p_verdict),
                    },
                    "research": research_dict,
                    "swarm": swarm_dict,
                    "plan": plan_dict,
                    "extraction": {
                        "company": extraction.company if hasattr(extraction, 'company') else '',
                        "industry": extraction.industry if hasattr(extraction, 'industry') else '',
                        "product": extraction.product if hasattr(extraction, 'product') else '',
                        "target_market": extraction.target_market if hasattr(extraction, 'target_market') else '',
                        "business_model": extraction.business_model if hasattr(extraction, 'business_model') else '',
                        "stage": extraction.stage if hasattr(extraction, 'stage') else '',
                        "traction": extraction.traction if hasattr(extraction, 'traction') else '',
                        "ask": extraction.ask if hasattr(extraction, 'ask') else '',
                    },
                }

                agent = ReportAgent()
                report_sections = agent.generate_report(report_data)
                logger.info(f"[WS] ReACT report generated: {len(report_sections)} sections")
            except Exception as e:
                logger.warning(f"[WS] Report agent failed (non-fatal): {e}")

            # Convert sections to narrative string for backward compatibility
            narrative = "\n\n".join(
                f"{title}\n{content}" for title, content in report_sections.items()
            ) if report_sections else ""

            # ── Final: Full result for PDF export ──
            broadcast({
                "type": "analysisComplete",
                "fullResult": {
                    "prediction": {
                        "verdict": p_verdict,
                        "composite_score": p_score,
                        "confidence": p_confidence,
                        "dimensions": dims,
                        "contested_dimensions": contested,
                        "council_models": model_labels,
                    },
                    "research": research_dict,
                    "swarm": swarm_dict,
                    "plan": plan_dict,
                    "extraction": {
                        "company": extraction.company if hasattr(extraction, 'company') else '',
                        "industry": extraction.industry if hasattr(extraction, 'industry') else '',
                        "product": extraction.product if hasattr(extraction, 'product') else '',
                        "target_market": extraction.target_market if hasattr(extraction, 'target_market') else '',
                        "business_model": extraction.business_model if hasattr(extraction, 'business_model') else '',
                        "stage": extraction.stage if hasattr(extraction, 'stage') else '',
                        "traction": extraction.traction if hasattr(extraction, 'traction') else '',
                        "ask": extraction.ask if hasattr(extraction, 'ask') else '',
                    },
                    "oasis": oasis_result if oasis_result else {},
                    "data_quality": extraction.data_quality if hasattr(extraction, 'data_quality') else 0,
                    "data_sources": ["SearXNG", "Council", "Swarm", "LLM", "OASIS"] if oasis_result else ["SearXNG", "Council", "Swarm", "LLM"],
                    "narrative": narrative,
                    "report_sections": report_sections,
                },
            })

            logger.info(f"[WS] Full analysis complete: {p_verdict} ({p_score:.1f}/10)")

        except Exception as e:
            logger.error(f"[WS] Full analysis failed: {e}\n{traceback.format_exc()}")
            broadcast({"type": "error", "error": str(e)})

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()


def _handle_agent_chat(msg: dict):
    """Handle chatWithAgent — let user ask follow-up questions to a specific agent."""
    agent_id = msg.get("agentId")
    user_message = msg.get("message", "")
    persona = msg.get("persona", "")
    zone = msg.get("zone", "")
    previous_vote = msg.get("previousVote", "")
    previous_reasoning = msg.get("previousReasoning", "")
    analysis_context = msg.get("analysisContext", "")

    if not user_message:
        broadcast({"type": "agentChatResponse", "agentId": agent_id, "error": "Empty message"})
        return

    def run_chat():
        try:
            from ..utils.llm_client import LLMClient
            llm = LLMClient()

            prompt = (
                f"You are: {persona}\n"
                f"Zone: {zone}\n\n"
                f"You previously evaluated a startup and voted: {previous_vote}\n"
                f"Your reasoning was: {previous_reasoning}\n\n"
                f"Analysis context: {analysis_context[:500]}\n\n"
                f"The user is now asking you a follow-up question. Stay in character as this persona. "
                f"Be specific and reference your previous assessment.\n\n"
                f"User: {user_message}\n\n"
                f"Your response:"
            )

            response = llm.chat([{"role": "user", "content": prompt}], max_tokens=500)
            broadcast({
                "type": "agentChatResponse",
                "agentId": agent_id,
                "response": response.strip() if response else "I couldn't formulate a response.",
            })
        except Exception as e:
            logger.error(f"[WS] Agent chat failed: {e}")
            broadcast({"type": "agentChatResponse", "agentId": agent_id, "error": str(e)})

    threading.Thread(target=run_chat, daemon=True).start()


def _handle_start_swarm(msg: dict):
    """Handle a startSwarm request — run prediction with streaming callbacks."""
    exec_summary = msg.get("execSummary", "")
    agent_count = msg.get("agentCount", 100)

    if not exec_summary:
        broadcast({"type": "error", "error": "Missing execSummary"})
        return

    valid_counts = [10, 25, 50, 100, 250, 500, 1000]
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

    # Track zone info from persona data
    agent_zones = {}

    def on_agent_start(agent_id, persona_name, model_label, zone="wildcard"):
        agent_zones[agent_id] = zone
        broadcast({
            "type": "agentSpawned",
            "id": agent_id,
            "persona": persona_name,
            "model": model_label,
            "zone": zone,
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

            raw = result.to_dict()
            # Convert snake_case to camelCase for dashboard compatibility
            broadcast({
                "type": "swarmComplete",
                "result": {
                    "totalAgents": raw.get("total_agents", 0),
                    "verdict": raw.get("verdict", "Unknown"),
                    "avg_scores": raw.get("avg_scores", {}),
                    "median_overall": raw.get("median_overall", 0),
                    "std_overall": raw.get("std_overall", 0),
                    "score_distribution": raw.get("score_distribution", {}),
                    "positivePct": raw.get("positive_pct", 0),
                    "negativePct": raw.get("negative_pct", 0),
                    "avgConfidence": raw.get("avg_confidence", 0),
                    "keyThemesPositive": raw.get("key_themes_positive", []),
                    "keyThemesNegative": raw.get("key_themes_negative", []),
                    "contestedThemes": raw.get("contested_themes", []),
                    "modelsUsed": raw.get("models_used", []),
                    "executionTimeSeconds": raw.get("execution_time_seconds", 0),
                },
            })
            logger.info(f"[WS] Swarm complete: {result.positive_pct}% positive")

        except Exception as e:
            logger.error(f"[WS] Swarm failed: {e}\n{traceback.format_exc()}")
            broadcast({"type": "error", "error": str(e)})

    thread = threading.Thread(target=run_swarm, daemon=True)
    thread.start()
